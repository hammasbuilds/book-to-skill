"""Layout repair: positioned PDF lines -> clean blocks (headings, paragraphs, code).

Every repair is switchable through :class:`RepairOptions` so each one's effect
on extraction quality can be measured on its own (see ``experiments.py``).

The repairs, in the order they run:

* **figure text** - labels and axis ticks drawn inside included figures (form
  XObjects) are dropped, unless most of the book's text is inside forms (some
  producers wrap whole pages in one);
* **running headers / footers and page numbers** - lines in the page's header
  or footer band are dropped when they carry the page number (found by the
  page offset that most pages agree on) or repeat verbatim, digits aside, on
  many pages;
* **word spacing** - spaces are re-derived from glyph geometry rather than
  trusted from the decoder (``pdftext.Line.text``);
* **code blocks** - lines set almost entirely in a monospaced font become
  fenced code with their indentation rebuilt from x offsets;
* **paragraph reflow** - lines are joined into paragraphs using vertical gaps,
  first-line indents, bullets and short last lines;
* **de-hyphenation** - a word split across a line break is rejoined, keeping
  the hyphen only when the hyphenated form is attested elsewhere in the book;
* **ligatures** - presentation-form ligature glyphs (U+FB00-FB06) are expanded.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from booktoskill.pdftext import Line, Page

LIGATURES = {
    chr(0xFB00): "ff",
    chr(0xFB01): "fi",
    chr(0xFB02): "fl",
    chr(0xFB03): "ffi",
    chr(0xFB04): "ffl",
    chr(0xFB05): "st",
    chr(0xFB06): "st",
}
_LIGATURE_RE = re.compile("[" + "".join(LIGATURES) + "]")
_BULLETS = "".join(chr(c) for c in (0x2022, 0x25CF, 0x25E6, 0x2013, 0x2014))
_BULLET_RE = re.compile("^[" + _BULLETS + "]" + r"\s")
_ROMAN_RE = re.compile(r"^[ivxlcdm]+$")
_SENTENCE_END = (".", ":", "?", "!", '"', ")", chr(0x201D))
_WORD_RE = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")


@dataclass(frozen=True)
class RepairOptions:
    figures: bool = True
    headers: bool = True
    spacing: bool = True
    code: bool = True
    reflow: bool = True
    dehyphenate: bool = True
    ligatures: bool = True


@dataclass
class Block:
    kind: str  # "heading" | "paragraph" | "code"
    text: str
    page: int
    size: float = 0.0


@dataclass
class RepairReport:
    figure_runs_removed: int = 0
    header_lines_removed: int = 0
    page_number_offset: int | None = None
    code_blocks: int = 0
    hyphen_joins: int = 0
    hyphens_kept: int = 0
    ligatures_expanded: int = 0
    kerning_joins: int = 0
    body_size: float = 0.0
    removed_examples: list[str] = field(default_factory=list)


def expand_ligatures(text: str) -> tuple[str, int]:
    count = len(_LIGATURE_RE.findall(text))
    return _LIGATURE_RE.sub(lambda m: LIGATURES[m.group(0)], text), count


def roman_to_int(token: str) -> int | None:
    values = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    token = token.lower()
    if not token or not _ROMAN_RE.match(token):
        return None
    total = 0
    for a, b in zip(token, token[1:] + " ", strict=True):
        va, vb = values[a], values.get(b, 0)
        total += -va if va < vb else va
    return total if total > 0 else None


def _edge_number(text: str) -> tuple[str, int] | None:
    """A page number at the start or end of a header/footer line."""
    parts = text.split()
    if not parts:
        return None
    for token in (parts[0], parts[-1]):
        if token.isascii() and token.isdigit() and len(token) <= 4:  # not "②"
            return "arabic", int(token)
        roman = roman_to_int(token)
        if roman is not None:
            return "roman", roman
    return None


def body_font_size(pages: list[Page]) -> float:
    sizes: Counter[float] = Counter()
    for page in pages:
        for line in page.lines:
            sizes[round(line.size, 1)] += sum(len(r.text) for r in line.runs)
    return sizes.most_common(1)[0][0] if sizes else 10.0


def strip_figure_text(pages: list[Page], report: RepairReport) -> list[Page]:
    """Drop runs drawn inside form XObjects, unless forms hold most of the text."""
    total = sum(len(r.text) for p in pages for ln in p.lines for r in ln.runs)
    inside = sum(len(r.text) for p in pages for ln in p.lines for r in ln.runs if r.in_figure)
    if total == 0 or inside / total > 0.5:
        return pages
    out = []
    for page in pages:
        lines = []
        for line in page.lines:
            kept = [r for r in line.runs if not r.in_figure]
            report.figure_runs_removed += len(line.runs) - len(kept)
            if kept:
                lines.append(Line(page=line.page, y=line.y, runs=kept))
        out.append(Page(page.index, page.width, page.height, lines))
    return out


def strip_headers(pages: list[Page], report: RepairReport) -> list[list[Line]]:
    """Remove running headers, footers and page numbers from each page."""
    edges: list[tuple[int, Line]] = []
    for page in pages:
        if page.lines:
            edges.append((page.index, page.lines[0]))
            if len(page.lines) > 1:
                edges.append((page.index, page.lines[-1]))

    offsets: Counter[tuple[str, int]] = Counter()
    for index, line in edges:
        found = _edge_number(line.text())
        if found:
            offsets[(found[0], found[1] - index)] += 1
    # An offset counts only if many pages agree on it: a stray number at the
    # top of a page ("3 is prime") must not define the numbering.
    good = {k for k, n in offsets.items() if n >= max(3, len(pages) // 20)}
    arabic = [k for k in good if k[0] == "arabic"]
    if arabic:
        report.page_number_offset = max(arabic, key=lambda k: offsets[k])[1]

    repeated: Counter[str] = Counter(re.sub(r"\d+", "#", line.text()) for _, line in edges)

    # Running headers sit in a fixed band. A chapter opener's "Chapter 3" also
    # starts a page with the right number, but it sits lower on the page.
    bands: Counter[int] = Counter()
    for index, line in edges:
        found = _edge_number(line.text())
        if found and (found[0], found[1] - index) in good:
            bands[round(line.y)] += 1
    band_ys = [y for y, n in bands.items() if n >= max(3, len(pages) // 20)]

    # Unnumbered boilerplate must also sit where most edge lines sit.
    edge_ys = Counter(round(line.y) for _, line in edges)
    common_ys = [y for y, n in edge_ys.items() if n >= max(3, len(pages) // 10)]

    # Every line is checked, not only the first and last: text inside a figure
    # can be ordered above the running header on the page it shares.
    drop: set[int] = set()
    for index, line in ((p.index, ln) for p in pages for ln in p.lines):
        text = line.text()
        found = _edge_number(text)
        in_band = any(abs(line.y - y) <= 3 for y in band_ys)
        at_edge = any(abs(line.y - y) <= 3 for y in common_ys)
        numbered = found is not None and (found[0], found[1] - index) in good and in_band
        boiler = repeated[re.sub(r"\d+", "#", text)] >= 4 and len(text) < 120 and at_edge
        if numbered or boiler:
            drop.add(id(line))
            report.header_lines_removed += 1
            if len(report.removed_examples) < 6:
                report.removed_examples.append(text)
    return [[ln for ln in page.lines if id(ln) not in drop] for page in pages]


def _is_code(line: Line, opts: RepairOptions) -> bool:
    return opts.code and line.mono_fraction >= 0.9


def _is_heading(line: Line, body: float) -> bool:
    # A heading has at least one real word: large type made only of letters
    # and fragments is a figure label ("' b a n na a '").
    text = line.text()
    return line.size >= body + 1.0 and len(text) < 150 and bool(re.search("[A-Za-z]{3,}", text))


def _line_text(line: Line, opts: RepairOptions, code: bool = False) -> str:
    if opts.spacing:
        # Some producers pad code with no-break spaces; they are plain spaces.
        return line.text(code=code).replace(chr(0xA0), " ")
    # Without geometric spacing, runs are joined the way a naive consumer of
    # the decoder output would: with a single space between runs.
    return " ".join(r.text for r in line.runs)


def _page_geometry(lines: list[Line]) -> tuple[float, float]:
    """Left margin and right edge of the text block on one page."""
    body = [ln for ln in lines if len(ln.text()) > 40]
    if not body:
        return (min((ln.x0 for ln in lines), default=0.0), 0.0)
    left = Counter(round(ln.x0) for ln in body).most_common(1)[0][0]
    right = max(ln.runs[-1].x_end for ln in body)
    return float(left), right


def _paragraph_break(
    line: Line,
    text: str,
    prev_line: Line,
    prev_text: str,
    nxt: Line | None,
    *,
    gap: float,
    left: float,
    prev_right: float,
    body: float,
    leading: float,
) -> bool:
    """Does ``line`` start a new paragraph after ``prev_line``?"""
    # First-line indent: this line sits right of both the previous line and the
    # next one by at most a few ems, the next line is ordinary text, and the
    # previous line ended a sentence (otherwise it is a hanging indent, such as
    # the second line of a glossary entry).
    indented = (
        nxt is not None
        and 0.5 * body < line.x0 - nxt.x0 < 3 * body
        and abs(prev_line.x0 - nxt.x0) < 2
        and line.x0 > left + 4
        and prev_text.rstrip().endswith(_SENTENCE_END)
        and not _BULLET_RE.match(nxt.text())
    )
    # A short previous line that ended a sentence closed its paragraph. Its
    # own page's right edge decides "short": facing pages have different margins.
    short_prev = (
        prev_right > 0
        and prev_line.runs[-1].x_end < prev_right - 3 * body
        and prev_text.rstrip().endswith(_SENTENCE_END)
    )
    return gap > 1.28 * leading or bool(_BULLET_RE.match(text)) or indented or short_prev


def _leading(page_lines: list[list[Line]], body: float) -> float:
    """The most common baseline-to-baseline distance between body lines.

    A median would be pulled up by the larger gaps around headings and listings.
    """
    spacings = [
        a.y - b.y
        for lines in page_lines
        for a, b in zip(lines, lines[1:], strict=False)
        if abs(a.size - body) < 0.5 and abs(b.size - body) < 0.5 and 0 < a.y - b.y < 3 * body
    ]
    modes = Counter(round(s * 2) / 2 for s in spacings).most_common(1)
    return modes[0][0] if modes else body * 1.2


class _Assembler:
    """Groups consecutive lines into headings, paragraphs and code blocks."""

    def __init__(
        self,
        page_lines: list[list[Line]],
        first_page: int,
        body: float,
        opts: RepairOptions,
        report: RepairReport,
    ) -> None:
        self.page_lines = page_lines
        self.first_page = first_page
        self.body = body
        self.opts = opts
        self.report = report
        self.leading = _leading(page_lines, body)
        self.geometry = {i: _page_geometry(lines) for i, lines in enumerate(page_lines)}
        self.blocks: list[Block] = []
        self.current: list[tuple[Line, str]] = []
        self.kind = ""

    def flush(self) -> None:
        if not self.current:
            return
        page = self.current[0][0].page
        if self.kind == "code":
            self.blocks.append(
                Block("code", _code_text(self.current, self.leading), page, self.body)
            )
            self.report.code_blocks += 1
        elif self.kind == "heading":
            text = " ".join(t for _, t in self.current)
            size = max(ln.size for ln, _ in self.current)
            self.blocks.append(Block("heading", text, page, size))
        else:
            text = _join_lines([t for _, t in self.current])
            self.blocks.append(Block("paragraph", text, page, self.body))
        self.current, self.kind = [], ""

    def _classify(self, line: Line) -> str:
        if _is_heading(line, self.body):
            return "heading"
        return "code" if _is_code(line, self.opts) else "paragraph"

    def _starts_new_block(self, kind: str, line: Line, text: str, nxt: Line | None) -> bool:
        if kind != self.kind or not self.current:
            return True
        prev_line, prev_text = self.current[-1]
        gap = prev_line.y - line.y if prev_line.page == line.page else 0.0
        if kind == "heading":
            return abs(prev_line.size - line.size) > 0.5 or gap > 2.5 * line.size
        if kind == "code":
            # A blank line inside a listing is one extra leading; a gap much
            # larger than that is prose or a new listing.
            return gap > 2.6 * self.leading
        page = line.page - self.first_page
        return _paragraph_break(
            line,
            text,
            prev_line,
            prev_text,
            nxt,
            gap=gap,
            left=self.geometry[page][0],
            prev_right=self.geometry[prev_line.page - self.first_page][1],
            body=self.body,
            leading=self.leading,
        )

    def _inline_code(self, line: Line) -> bool:
        """A monospaced line continuing a sentence at normal leading is inline
        code wrapped onto its own line (a URL, an identifier), not a listing."""
        if self.kind != "paragraph" or not self.current:
            return False
        prev_line, prev_text = self.current[-1]
        return (
            prev_line.page == line.page
            and prev_line.y - line.y <= 1.15 * self.leading
            and not prev_text.rstrip().endswith(":")
        )

    def run(self) -> list[Block]:
        for lines in self.page_lines:
            for i, line in enumerate(lines):
                kind = self._classify(line)
                text = _line_text(line, self.opts, code=kind == "code")
                if not text.strip():
                    continue
                if not self.opts.reflow:
                    self.flush()
                    self.current, self.kind = [(line, text)], kind
                    self.flush()
                    continue
                if kind == "code" and self._inline_code(line):
                    kind = "paragraph"
                nxt = lines[i + 1] if i + 1 < len(lines) else None
                if self._starts_new_block(kind, line, text, nxt):
                    self.flush()
                    self.kind = kind
                self.current.append((line, text))
        self.flush()
        return self.blocks


def _text_repairs(blocks: list[Block], opts: RepairOptions, report: RepairReport) -> None:
    """Repairs on assembled text: ligatures, line-end hyphens, kerning splits."""
    if opts.ligatures:
        for block in blocks:
            block.text, n = expand_ligatures(block.text)
            report.ligatures_expanded += n
    if opts.dehyphenate:
        _dehyphenate(blocks, report)
    else:
        for block in blocks:
            block.text = block.text.replace(_BREAK, " ")
    if opts.spacing:
        _rejoin_kerning_splits(blocks, report)


def build_blocks(
    pages: list[Page], opts: RepairOptions | None = None
) -> tuple[list[Block], RepairReport]:
    """Turn positioned lines into headings, paragraphs and code blocks."""
    opts = opts or RepairOptions()
    report = RepairReport()
    if opts.figures:
        pages = strip_figure_text(pages, report)
    body = body_font_size(pages)
    report.body_size = body
    page_lines = strip_headers(pages, report) if opts.headers else [page.lines for page in pages]
    first_page = pages[0].index if pages else 0
    blocks = _Assembler(page_lines, first_page, body, opts, report).run()
    _text_repairs(blocks, opts, report)
    return blocks, report


def _code_text(lines: list[tuple[Line, str]], leading: float) -> str:
    """Code lines with indentation from x offsets and blank lines from y gaps."""
    left = min(ln.x0 for ln, _ in lines)
    out: list[str] = []
    prev: Line | None = None
    for line, text in lines:
        if prev is not None and prev.page == line.page:
            out.extend([""] * max(0, round((prev.y - line.y) / leading) - 1))
        char_w = line.runs[0].font.text_width("m", line.runs[0].size) or line.size * 0.5
        indent = max(0, round((line.x0 - left) / char_w))
        out.append(" " * indent + text.rstrip())
        prev = line
    return "\n".join(out)


# A soft line-break marker used between reflowed lines until de-hyphenation
# has decided what each "-<break>" means.
_BREAK = chr(0x2029)


def _join_lines(texts: list[str]) -> str:
    out = texts[0].strip()
    for t in texts[1:]:
        t = t.strip()
        out = out + _BREAK + t if out.endswith("-") and t[:1].isalpha() else out + " " + t
    return out


def _dehyphenate(blocks: list[Block], report: RepairReport) -> None:
    """Decide, for every word broken at a line end, whether the hyphen is real.

    The book itself is the dictionary. If only the closed-up word occurs
    elsewhere, join; if only the hyphenated compound does, keep the hyphen.
    When neither occurs, follow what this book's own attested cases say: a
    TeX book hyphenates ordinary words at line ends (so join), while a
    ragged-right book only ever breaks at real compound hyphens (so keep).
    """
    vocab: Counter[str] = Counter()
    for block in blocks:
        if block.kind == "paragraph":
            for w in _WORD_RE.findall(block.text.replace(_BREAK, " ")):
                vocab[w.lower()] += 1
    pattern = re.compile(r"([A-Za-z]+)-" + _BREAK + r"([A-Za-z]+)")

    def evidence(head: str, tail: str) -> str | None:
        if tail[:1].isupper():  # "Pro-" / "Git": a name, keep the hyphen
            return "keep"
        joined, hyphenated = vocab[(head + tail).lower()], vocab[f"{head}-{tail}".lower()]
        if joined > hyphenated:
            return "join"
        if hyphenated > joined:
            return "keep"
        return None

    attested = Counter(
        e
        for block in blocks
        if block.kind == "paragraph"
        for m in pattern.finditer(block.text)
        if (e := evidence(m.group(1), m.group(2))) is not None
    )
    default = "join" if attested["join"] >= attested["keep"] else "keep"

    def fix(m: re.Match[str]) -> str:
        head, tail = m.group(1), m.group(2)
        if (evidence(head, tail) or default) == "keep":
            report.hyphens_kept += 1
            return f"{head}-{tail}"
        report.hyphen_joins += 1
        return head + tail

    for block in blocks:
        if block.kind == "paragraph" and _BREAK in block.text:
            block.text = pattern.sub(fix, block.text)
        block.text = block.text.replace(_BREAK, "")


_KERN_SPLIT_RE = re.compile(r"\b([B-HJ-Z]) ([a-z]{2,})\b")


def _rejoin_kerning_splits(blocks: list[Block], report: RepairReport) -> None:
    """Rejoin "T uples" -> "Tuples".

    Display fonts kern pairs such as T-u and W-e so tightly that the decoder
    reads the kern as a word space. A lone capital that is not a word on its
    own ("A" and "I" are) followed by a fragment is rejoined when the joined
    word occurs elsewhere in the book.
    """
    vocab = {w.lower() for b in blocks if b.kind == "paragraph" for w in _WORD_RE.findall(b.text)}

    def fix(m: re.Match[str]) -> str:
        joined = m.group(1) + m.group(2)
        if joined.lower() in vocab:
            report.kerning_joins += 1
            return joined
        return m.group(0)

    for block in blocks:
        if block.kind != "code":
            block.text = _KERN_SPLIT_RE.sub(fix, block.text)
