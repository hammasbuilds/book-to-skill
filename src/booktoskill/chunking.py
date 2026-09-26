"""Split text into retrieval units of roughly equal size.

Chunks never cross a section boundary. Paragraphs and code blocks are kept
whole where they fit; a paragraph longer than the target is split at sentence
boundaries. The same chunker is used for the book text and for the skill's
reference files, so the two retrieval arms differ only in what they contain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from booktoskill.structure import Book, is_content_chapter

_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+(?=[A-Z(\"'])")


@dataclass(frozen=True)
class Chunk:
    uid: str
    chapter: str  # chapter number
    section: str  # section title, or "" for chapter intro / whole files
    text: str

    @property
    def words(self) -> int:
        return len(self.text.split())


def _split_long(text: str, target: int) -> list[str]:
    if len(text.split()) <= target:
        return [text]
    out: list[str] = []
    cur: list[str] = []
    for sentence in _SENTENCE_RE.split(text):
        if cur and len(" ".join(cur + [sentence]).split()) > target:
            out.append(" ".join(cur))
            cur = []
        cur.append(sentence)
    if cur:
        out.append(" ".join(cur))
    return out


def chunk_pieces(pieces: list[str], target: int) -> list[str]:
    """Greedily pack pieces (paragraphs, code) into chunks of ~``target`` words."""
    chunks: list[str] = []
    cur: list[str] = []
    size = 0
    for piece in pieces:
        for part in _split_long(piece, target):
            n = len(part.split())
            if cur and size + n > target:
                chunks.append("\n\n".join(cur))
                cur, size = [], 0
            cur.append(part)
            size += n
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


def chunk_book(book: Book, target: int = 200, exclude: tuple[str, ...] = ()) -> list[Chunk]:
    """Chunks of every numbered chapter, skipping sections named in ``exclude``."""
    excluded = {e.lower() for e in exclude}
    out: list[Chunk] = []
    for ch in book.chapters:
        if not is_content_chapter(ch):
            continue
        groups = [("", ch.intro)] + [
            (s.title, s.blocks) for s in ch.sections if s.title.lower() not in excluded
        ]
        for title, blocks in groups:
            pieces = [b.text for b in blocks if b.text.strip()]
            if title:
                pieces = [title] + pieces
            for i, text in enumerate(chunk_pieces(pieces, target)):
                out.append(Chunk(f"{ch.number}/{title or 'intro'}/{i}", ch.number, title, text))
    return out


def chunk_markdown(files: dict[str, str], target: int = 200) -> list[Chunk]:
    """Chunk markdown reference files, splitting at headings and blank lines.

    ``files`` maps a chapter number to that chapter's reference-file text.
    """
    out: list[Chunk] = []
    for chapter, text in files.items():
        sections = re.split(r"\n(?=#{1,3} )", text)
        for s_index, section in enumerate(sections):
            pieces = [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]
            for i, chunk in enumerate(chunk_pieces(pieces, target)):
                out.append(Chunk(f"{chapter}/s{s_index}/{i}", chapter, "", chunk))
    return out


def whole_files(files: dict[str, str]) -> list[Chunk]:
    """Each file as a single retrieval unit (``files`` maps chapter -> text)."""
    return [Chunk(f"{chapter}/file", chapter, "", text) for chapter, text in files.items()]
