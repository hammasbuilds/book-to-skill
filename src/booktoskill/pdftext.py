"""Read a PDF into positioned, font-tagged lines.

pypdf decodes the content streams; everything after that is done here. Each
text-show operation becomes a :class:`Run` with its baseline position, its
rendered size, whether its font is bold or monospaced, and an estimated width
(from the font's own ``/Widths`` table), so that the layout-repair stage can
decide where spaces, code indentation, headings and running headers are.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pypdf import PdfReader

_BOLD_MARKERS = ("bold", "bx", "black", "heavy", "semibold", "demi")
_MONO_MARKERS = ("tt", "mono", "courier", "code", "consol")
# Closing punctuation never takes a leading space in prose, whatever the gap.
_NO_SPACE_BEFORE = (".", ",", ";", ":", "!", "?", ")", "]", "}", chr(0x2019))


@dataclass(frozen=True)
class FontInfo:
    name: str
    bold: bool
    mono: bool
    first_char: int
    widths: tuple[float, ...]
    avg_width: float

    def text_width(self, text: str, size: float) -> float:
        """Width of ``text`` at ``size`` points, from the font's width table.

        A space inside a proportional run is not a glyph: it is justification
        glue that TeX-style typesetters shrink or stretch per line, and pypdf
        reconstructs it as a character. It is costed at 0.2 em - between the
        usual minimum shrink (~0.17 em) and the natural width (0.25-0.33 em) -
        because over-estimating it hides real word gaps at font changes.
        """
        total = 0.0
        for ch in text:
            if ch == " " and not self.mono:
                total += 200.0
                continue
            code = ord(ch) - self.first_char
            w = self.widths[code] if 0 <= code < len(self.widths) else 0.0
            total += w if w > 0 else self.avg_width
        return total * size / 1000.0


@dataclass(frozen=True)
class Run:
    x: float
    y: float
    size: float
    font: FontInfo
    text: str
    in_figure: bool = False

    @property
    def x_end(self) -> float:
        return self.x + self.font.text_width(self.text, self.size)


@dataclass
class Line:
    page: int
    y: float
    runs: list[Run] = field(default_factory=list)

    @property
    def x0(self) -> float:
        return self.runs[0].x

    @property
    def size(self) -> float:
        """The size of the line's longest run (superscripts do not count)."""
        return max(self.runs, key=lambda r: len(r.text)).size

    def _char_fraction(self, attr: str) -> float:
        total = sum(len(r.text.strip()) for r in self.runs)
        if total == 0:
            return 0.0
        hit = sum(len(r.text.strip()) for r in self.runs if getattr(r.font, attr))
        return hit / total

    @property
    def mono_fraction(self) -> float:
        return self._char_fraction("mono")

    @property
    def bold_fraction(self) -> float:
        return self._char_fraction("bold")

    def text(self, *, space_gap: float = 0.06, code: bool = False) -> str:
        """Join runs, inserting spaces where the horizontal gap says there is one.

        ``space_gap`` is the gap, in ems, above which two runs are separated by a
        space. On both books measured, gaps between runs split into a cluster at
        0-0.04 em (no space) and one from 0.08 em up (a word space squeezed by
        justification), hence the 0.06 default. In ``code`` mode a gap becomes
        as many spaces as fit, so aligned columns and indentation survive.
        """
        out: list[str] = []
        prev: Run | None = None
        for run in self.runs:
            if prev is not None:
                gap = run.x - prev.x_end
                if code and run.font.mono:
                    cw = run.font.text_width("m", run.size) or run.size * 0.5
                    n = max(0, round(gap / cw))
                    out.append(" " * n)
                elif (
                    gap > space_gap * run.size
                    and not out[-1].endswith((" ", "(", "[", "{"))
                    and not run.text.startswith(_NO_SPACE_BEFORE)
                ):
                    out.append(" ")
            out.append(run.text)
            prev = run
        return "".join(out)


@dataclass
class Page:
    index: int
    width: float
    height: float
    lines: list[Line]


def _font_info(font: Any, cache: dict[int, FontInfo]) -> FontInfo:
    if font is None:
        return FontInfo("", False, False, 0, (), 500.0)
    key = id(font)
    if key in cache:
        return cache[key]
    name = str(font.get("/BaseFont", ""))
    style = name.split("+")[-1].lower()
    widths_obj = font.get("/Widths")
    widths: tuple[float, ...] = ()
    if widths_obj is not None:
        widths = tuple(float(w) for w in widths_obj.get_object())
    nonzero = [w for w in widths if w > 0]
    avg = sum(nonzero) / len(nonzero) if nonzero else 500.0
    # A font whose every glyph has the same advance is monospaced, whatever it
    # is called; TeX's typewriter fonts declare no FixedPitch flag.
    uniform = len(nonzero) > 10 and max(nonzero) - min(nonzero) < 0.01 * avg
    info = FontInfo(
        name=name,
        bold=any(m in style for m in _BOLD_MARKERS),
        mono=uniform or any(m in style for m in _MONO_MARKERS),
        first_char=int(font.get("/FirstChar", 0)),
        widths=widths,
        avg_width=avg,
    )
    cache[key] = info
    return info


def _group_lines(page_index: int, runs: list[Run], tol: float) -> list[Line]:
    lines: list[Line] = []
    for run in sorted(runs, key=lambda r: (-r.y, r.x)):
        if lines and abs(lines[-1].y - run.y) <= tol:
            lines[-1].runs.append(run)
        else:
            lines.append(Line(page=page_index, y=run.y, runs=[run]))
    for line in lines:
        line.runs.sort(key=lambda r: r.x)
    return lines


class _Collector:
    """pypdf visitor callbacks that append positioned runs.

    Text drawn inside a form XObject (the ``Do`` operator) is flagged: in
    TeX-produced books that is where included figures put their labels and
    axis ticks.
    """

    def __init__(self, cache: dict[int, FontInfo]) -> None:
        self.cache = cache
        self.runs: list[Run] = []
        self.depth = 0

    def before(self, op: bytes, *_: Any) -> None:
        if op == b"Do":
            self.depth += 1

    def after(self, op: bytes, *_: Any) -> None:
        if op == b"Do":
            self.depth -= 1

    def text(self, text: str, cm: list[float], tm: list[float], font: Any, size: float) -> None:
        stripped = text.strip()
        if not stripped:
            return
        a, b, c, d, e, f = (float(v) for v in cm)
        x = float(tm[4]) * a + float(tm[5]) * c + e
        y = float(tm[4]) * b + float(tm[5]) * d + f
        scale = abs(float(tm[3]) * d) or abs(float(tm[0]) * a) or 1.0
        # pypdf sometimes prefixes a run with the space it inferred; the
        # position already encodes that gap, so it is dropped here and
        # re-derived from geometry in Line.text().
        info = _font_info(font, self.cache)
        self.runs.append(Run(x, y, float(size) * scale, info, stripped, self.depth > 0))


def read_pdf(path: str | Path, *, line_tolerance: float = 2.5) -> list[Page]:
    """Return every page of ``path`` as positioned lines, top to bottom."""
    # pypdf warns once per embedded CFF font that fontTools is not installed;
    # the width tables used here do not need it, so the noise is suppressed.
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(str(path))
    cache: dict[int, FontInfo] = {}
    pages: list[Page] = []
    for index, page in enumerate(reader.pages):
        collector = _Collector(cache)
        page.extract_text(
            visitor_operand_before=collector.before,
            visitor_operand_after=collector.after,
            visitor_text=collector.text,
        )
        box = page.mediabox
        lines = _group_lines(index, collector.runs, line_tolerance)
        pages.append(Page(index, float(box.width), float(box.height), lines))
    return pages


def read_outline(path: str | Path) -> list[tuple[int, str, int]]:
    """The PDF's bookmark tree as ``(depth, title, page_index)`` rows.

    Used only as a comparison method for structure detection: many PDFs have
    no outline, so the pipeline never depends on it.
    """
    reader = PdfReader(str(path))
    rows: list[tuple[int, str, int]] = []

    def walk(items: list[Any], depth: int) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                page = reader.get_destination_page_number(item)
                rows.append((depth, str(item.title), page))

    walk(reader.outline, 0)
    return rows
