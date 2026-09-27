"""Chapter and section detection from repaired blocks.

Heading levels come from font size alone, ranked: the size used for chapter
titles (the one that follows a "Chapter N" label, or failing that the largest
size used more than once) is level 1, the next size down that occurs at least
three times is level 2. Anything smaller stays inside its section as an inline
sub-heading. The PDF outline is never consulted; ``experiments.py`` compares
this against the outline and against the book's real table of contents.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from booktoskill.layout import Block

_LABEL_RE = re.compile(r"^(?:chapter|appendix|part)\s+([0-9]+|[A-Z])\.?$", re.I)
# A label and its title set at the same size are joined into one heading block.
_LABELLED_TITLE_RE = re.compile(r"^(?:chapter|appendix|part)\s+([0-9]+|[A-Z])\.?\s+(.+)$", re.I)
_APPENDIX_RE = re.compile(r"^appendix\s+([A-Z])\b", re.I)
_SECTION_NUM_RE = re.compile(r"^((?:[0-9]+|[A-Z])\.[0-9]+)\.?\s+(.*)$")
_CHAPTER_NUM_RE = re.compile(r"^([0-9]+)\.?\s+(\D.*)$")


@dataclass
class Section:
    number: str
    title: str
    page: int
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Chapter:
    number: str
    title: str
    page: int
    intro: list[Block] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.number} {self.title}".strip()

    def blocks(self, exclude: tuple[str, ...] = ()) -> list[Block]:
        out = list(self.intro)
        for s in self.sections:
            if s.title.lower() not in {e.lower() for e in exclude}:
                out.extend(s.blocks)
        return out

    @property
    def last_page(self) -> int:
        pages = [b.page for b in self.blocks()] or [self.page]
        return max(pages)


@dataclass
class Book:
    title: str
    chapters: list[Chapter]
    heading_sizes: dict[str, float]


def _round(size: float) -> float:
    return round(size * 2) / 2


def heading_levels(blocks: list[Block]) -> tuple[float | None, float | None]:
    """The font sizes used for chapter titles and for section titles."""
    headings = [b for b in blocks if b.kind == "heading"]
    if not headings:
        return None, None
    # "Chapter 3" labels are not titles of anything; counting them would make
    # the label size look like a heading level of its own.
    counts = Counter(_round(b.size) for b in headings if not _LABEL_RE.match(b.text.strip()))
    if not counts:
        return None, None
    chapter_size = None
    for a, b in zip(headings, headings[1:], strict=False):
        if _LABEL_RE.match(a.text.strip()) and b.page == a.page:
            chapter_size = _round(b.size)
            break
    if chapter_size is None:
        repeated = [s for s, n in counts.items() if n >= 2]
        chapter_size = max(repeated) if repeated else max(counts)
    # Sections are the largest size below chapter level that recurs (>= 3
    # times); smaller recurring sizes are subsections, which may well be more
    # numerous than sections.
    smaller = [s for s, n in counts.items() if s < chapter_size and n >= 3]
    return chapter_size, (max(smaller) if smaller else None)


def detect_structure(blocks: list[Block], title: str = "") -> Book:
    chapter_size, section_size = heading_levels(blocks)
    chapters: list[Chapter] = []
    pending_label: str | None = None
    front = Chapter("", "Front matter", 0)
    for block in blocks:
        size = _round(block.size) if block.kind == "heading" else 0.0
        if block.kind == "heading":
            label = _LABEL_RE.match(block.text.strip())
            if label:
                pending_label = label.group(1)
                continue
        if block.kind == "heading" and chapter_size is not None and size >= chapter_size:
            number, text = pending_label or "", block.text.strip()
            m = _LABELLED_TITLE_RE.match(text) or _CHAPTER_NUM_RE.match(text)
            if not number and m:
                number, text = m.group(1), m.group(2)
            chapters.append(Chapter(number, text, block.page))
            pending_label = None
            continue
        pending_label = None
        current = chapters[-1] if chapters else front
        if block.kind == "heading" and section_size is not None and size >= section_size:
            m = _SECTION_NUM_RE.match(block.text.strip())
            number, text = (m.group(1), m.group(2)) if m else ("", block.text.strip())
            current.sections.append(Section(number, text, block.page))
            continue
        if current.sections:
            current.sections[-1].blocks.append(block)
        else:
            current.intro.append(block)
    if _numbers_unreliable(chapters):
        for ch in chapters:
            ch.number = ""
        _number_unlabelled(chapters)
    if front.intro or front.sections:
        chapters.insert(0, front)
    return Book(
        title=title,
        chapters=chapters,
        heading_sizes={"chapter": chapter_size or 0.0, "section": section_size or 0.0},
    )


def _numbers_unreliable(chapters: list[Chapter]) -> bool:
    """Too few title-level headings carry a number for the numbering to be the book's.

    A book that prints chapter numbers numbers (nearly) all of its chapters.
    When fewer than half of the headings that look like chapters (two or more
    sections) are numbered, the numbers that were found are accidents - a
    thesis title page reading "1 Introduction to ..." or a year - and the
    whole book is renumbered instead. One stray number must not switch the
    fallback off.
    """
    candidates = [ch for ch in chapters if len(ch.sections) >= 2]
    numbered = [ch for ch in candidates if ch.number]
    stray = [ch for ch in chapters if ch.number and len(ch.sections) < 2]
    if not candidates:
        return False
    return len(numbered) < len(candidates) / 2 or len(stray) > len(numbered)


def _number_unlabelled(chapters: list[Chapter]) -> None:
    """Number chapters in a book that prints no chapter numbers (Pro Git).

    Title-level headings with at least two sections are chapters, numbered in
    order; "Appendix X: ..." takes its letter. Headings without sections
    (license, prefaces, dedication, contents) stay front or back matter.
    """
    n = 0
    for ch in chapters:
        if len(ch.sections) < 2:
            continue
        m = _APPENDIX_RE.match(ch.title)
        if m:
            ch.number = m.group(1)
        else:
            n += 1
            ch.number = str(n)


def is_content_chapter(chapter: Chapter) -> bool:
    """Numbered chapters and appendices; not contents, preface or index."""
    return bool(chapter.number)


def content_coverage(book: Book) -> float:
    """Share of the book's words that sit inside numbered chapters."""
    total = sum(len(b.text.split()) for ch in book.chapters for b in ch.blocks())
    inside = sum(
        len(b.text.split()) for ch in book.chapters if is_content_chapter(ch) for b in ch.blocks()
    )
    return inside / total if total else 0.0


def book_to_markdown(book: Book) -> str:
    out = [f"# {book.title}\n"] if book.title else []
    for ch in book.chapters:
        out.append(f"\n## {ch.label}\n")
        out.extend(_blocks_md(ch.intro))
        for s in ch.sections:
            out.append(f"\n### {s.number} {s.title}".rstrip() + "\n")
            out.extend(_blocks_md(s.blocks))
    return "\n".join(out).strip() + "\n"


def _blocks_md(blocks: list[Block]) -> list[str]:
    out = []
    for b in blocks:
        if b.kind == "code":
            out.append(f"```\n{b.text}\n```")
        elif b.kind == "heading":
            out.append(f"**{b.text}**")
        else:
            out.append(b.text)
    return out
