"""Read a PDF into positioned, font-tagged lines.

pypdf decodes the content streams; everything after that is done here. Each
text-show operation becomes a :class:`Run` with its baseline position, its
rendered size, whether its font is monospaced, and an estimated width (from
the font's own ``/Widths`` table, read through its ToUnicode map), so that
the layout-repair stage can decide where spaces, code indentation, headings
and running headers are.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from pypdf import PdfReader

_MONO_MARKERS = ("tt", "mono", "courier", "code", "consol")
# Closing punctuation never takes a leading space in prose, whatever the gap.
_NO_SPACE_BEFORE = (".", ",", ";", ":", "!", "?", ")", "]", "}", chr(0x2019))


@dataclass(frozen=True)
class FontInfo:
    name: str
    mono: bool
    char_widths: dict[str, float]  # decoded character -> advance, in 1/1000 em
    avg_width: float
    family: str = ""  # base name without subset tag or style, e.g. "mplus1mn"

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
            else:
                total += self.char_widths.get(ch, self.avg_width)
        return total * size / 1000.0


@dataclass(frozen=True)
class Run:
    x: float
    y: float
    size: float
    font: FontInfo
    text: str
    in_figure: bool = False
    lead_space: bool = False  # the decoded text began with a space

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

    @property
    def mono_fraction(self) -> float:
        """Share of the line's characters set in a monospaced font."""
        total = sum(len(r.text) for r in self.runs)
        mono = sum(len(r.text) for r in self.runs if r.font.mono)
        return mono / total if total else 0.0

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
                    (gap > space_gap * run.size or run.lead_space)
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


_HEX_RE = re.compile(rb"<([0-9A-Fa-f]+)>")


def _utf16(hexstr: bytes) -> str:
    raw = bytes.fromhex(hexstr.decode("ascii"))
    return raw.decode("utf-16-be", errors="ignore")


def parse_tounicode(data: bytes) -> dict[int, str]:
    """Character code -> text, from a ToUnicode CMap (bfchar and bfrange)."""
    out: dict[int, str] = {}
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", data, re.S):
        hexes = _HEX_RE.findall(block)
        for src, dst in zip(hexes[::2], hexes[1::2], strict=False):
            out[int(src, 16)] = _utf16(dst)
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for line in block.strip().splitlines():
            hexes = _HEX_RE.findall(line)
            if len(hexes) < 3:
                continue
            lo, hi = int(hexes[0], 16), int(hexes[1], 16)
            if b"[" in line:  # <lo> <hi> [<d1> <d2> ...]
                for i, dst in enumerate(hexes[2:]):
                    out[lo + i] = _utf16(dst)
            else:  # <lo> <hi> <start>: consecutive code points
                start = _utf16(hexes[2])
                if start:
                    for i in range(hi - lo + 1):
                        out[lo + i] = start[:-1] + chr(ord(start[-1]) + i)
    return out


def _font_key(font: Any) -> Any:
    """A stable cache key: the font's object number, or its identity."""
    ref = getattr(font, "indirect_reference", None)
    return (ref.idnum, ref.generation) if ref is not None else id(font)


def _font_info(font: Any, cache: dict[Any, FontInfo]) -> FontInfo:
    if font is None:
        return FontInfo("", False, {}, 500.0)
    key = _font_key(font)
    if key in cache:
        return cache[key]
    name = str(font.get("/BaseFont", ""))
    style = name.split("+")[-1].lower()
    widths_obj = font.get("/Widths")
    widths = [float(w) for w in widths_obj.get_object()] if widths_obj is not None else []
    first = int(font.get("/FirstChar", 0))
    # Which character each code draws: the ToUnicode map when there is one
    # (subsetting producers such as Prawn renumber glyphs), else the code itself.
    to_unicode = font.get("/ToUnicode")
    if to_unicode is not None:
        codes = parse_tounicode(to_unicode.get_object().get_data())
    else:
        codes = {first + i: chr(first + i) for i in range(len(widths))}
    char_widths = {
        text: widths[code - first]
        for code, text in codes.items()
        if len(text) == 1 and 0 <= code - first < len(widths) and widths[code - first] > 0
    }
    nonzero = [w for w in widths if w > 0]
    info = FontInfo(
        name=name,
        mono=any(m in style for m in _MONO_MARKERS),  # provisional; see _settle_mono
        char_widths=char_widths,
        avg_width=sum(nonzero) / len(nonzero) if nonzero else 500.0,
        family=style.split("-")[0],
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

    def __init__(self, cache: dict[Any, FontInfo]) -> None:
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
        # A leading space is kept as a flag, not as text: some producers
        # (Prawn) draw real space glyphs at the start of a run, so the run's
        # position sits on the space and the geometric gap reads as zero.
        info = _font_info(font, self.cache)
        lead = text[:1] in (" ", chr(0xA0))
        self.runs.append(Run(x, y, float(size) * scale, info, stripped, self.depth > 0, lead))


def read_pdf(path: str | Path, *, line_tolerance: float = 2.5) -> list[Page]:
    """Return every page of ``path`` as positioned lines, top to bottom."""
    # pypdf warns once per embedded CFF font that fontTools is not installed;
    # the width tables used here do not need it, so the noise is suppressed.
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(str(path))
    cache: dict[Any, FontInfo] = {}
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
    return _settle_mono(pages)


def _settle_mono(pages: list[Page]) -> list[Page]:
    """Decide which fonts are monospaced from the letters they actually draw.

    A font whose drawn letters all share one advance is monospaced, whatever
    it is called: TeX's typewriter fonts declare no FixedPitch flag. Only
    drawn letters count, because a subset's width table also lists unused
    codes at the .notdef width. A font that draws fewer than five distinct
    letters takes its family's verdict (a per-page subset of a code font may
    hold only a handful), and failing that its name.
    """
    drawn: dict[int, tuple[FontInfo, set[str]]] = {}
    for page in pages:
        for line in page.lines:
            for r in line.runs:
                drawn.setdefault(id(r.font), (r.font, set()))[1].update(r.text)
    verdict: dict[int, bool | None] = {}
    for key, (font, chars) in drawn.items():
        letters = [font.char_widths.get(c, 0.0) for c in chars if c.isascii() and c.isalpha()]
        letters = [w for w in letters if w]
        if len({c for c in chars if c.isascii() and c.isalpha()}) >= 5 and letters:
            verdict[key] = max(letters) - min(letters) < 0.01 * max(letters)
        else:
            verdict[key] = None
    mono_families = {font.family for key, (font, _) in drawn.items() if verdict[key]}
    settled: dict[int, FontInfo] = {}
    for key, (font, _) in drawn.items():
        v = verdict[key]
        mono = v if v is not None else (font.family in mono_families or font.mono)
        settled[key] = font if mono == font.mono else replace(font, mono=mono)
    for page in pages:
        for line in page.lines:
            line.runs = [
                r if settled[id(r.font)] is r.font else replace(r, font=settled[id(r.font)])
                for r in line.runs
            ]
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
