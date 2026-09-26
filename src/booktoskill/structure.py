"""Chapter and section detection from repaired blocks.

Heading levels come from font size alone, ranked: the size used for chapter
titles (the one that follows a "Chapter N" label, or failing that the largest
size used more than once) is level 1, the next size down that occurs at least
three times is level 2. Anything smaller stays inside its section as a bold
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
    counts = Counter(_round(b.size) for b in headings)
    chapter_size = None
    for a, b in zip(headings, headings[1:], strict=False):
        if _LABEL_RE.match(a.text.strip()) and b.page == a.page:
            chapter_size = _round(b.size)
            break
    if chapter_size is None:
        repeated = [s for s, n in counts.items() if n >= 2]
        chapter_size = max(repeated) if repeated else max(counts)
    # Sections are the most frequent heading below chapter level; the largest
    # smaller size can be a one-off (a figure label set in a display font).
    smaller = [(n, s) for s, n in counts.items() if s < chapter_size and n >= 3]
    return chapter_size, (max(smaller)[1] if smaller else None)


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
    if front.intro or front.sections:
        chapters.insert(0, front)
    return Book(
        title=title,
        chapters=chapters,
        heading_sizes={"chapter": chapter_size or 0.0, "section": section_size or 0.0},
    )


def is_content_chapter(chapter: Chapter) -> bool:
    """Numbered chapters and appendices; not contents, preface or index."""
    return bool(chapter.number)


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
