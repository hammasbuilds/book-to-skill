"""PDF -> repaired blocks -> chapter structure, in one call."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from booktoskill.layout import Block, RepairOptions, RepairReport, build_blocks
from booktoskill.pdftext import Page, read_pdf
from booktoskill.structure import Book, detect_structure


@dataclass
class Conversion:
    pages: list[Page]
    blocks: list[Block]
    report: RepairReport
    book: Book


def pdf_title(path: str | Path) -> str:
    """The PDF's own /Title metadata, or the file name when it has none."""
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    meta = PdfReader(str(path)).metadata
    title = (meta.title if meta else None) or ""
    return title.strip() or Path(path).stem


def convert(
    path: str | Path,
    opts: RepairOptions | None = None,
    title: str | None = None,
    pages: list[Page] | None = None,
) -> Conversion:
    """Run the whole extraction. Pass ``pages`` to reuse an earlier parse."""
    path = Path(path)
    if pages is None:
        if not path.is_file():
            raise FileNotFoundError(f"no such PDF: {path}")
        pages = read_pdf(path)
    blocks, report = build_blocks(pages, opts)
    book = detect_structure(blocks, title or pdf_title(path))
    return Conversion(pages, blocks, report, book)


def plain_page_texts(path: str | Path) -> list[str]:
    """The unrepaired baseline: pypdf's default ``extract_text`` per page."""
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    return [page.extract_text() or "" for page in PdfReader(str(path)).pages]


def blocks_text(blocks: list[Block]) -> str:
    return "\n\n".join(b.text for b in blocks)
