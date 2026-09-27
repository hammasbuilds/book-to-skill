from __future__ import annotations

from pathlib import Path

import pytest

from booktoskill.bm25 import BM25, stem, tokenize
from booktoskill.chunking import chunk_book, chunk_markdown, chunk_pieces
from booktoskill.layout import Block
from booktoskill.pipeline import Conversion
from booktoskill.structure import book_to_markdown, detect_structure, is_content_chapter


def test_chapters_and_sections_from_font_sizes(tiny: Conversion) -> None:
    book = tiny.book
    content = [ch for ch in book.chapters if is_content_chapter(ch)]
    assert [(c.number, c.title) for c in content] == [
        ("1", "Getting Started"),
        ("2", "Next Steps"),
    ]
    assert [(s.number, s.title) for s in content[0].sections] == [
        ("1.1", "Assignment"),
        ("1.2", "Glossary"),
    ]
    assert book.title == "A Tiny Book"  # from the title page, no metadata


def test_section_text_is_attached_to_its_section(tiny: Conversion) -> None:
    ch2 = [c for c in tiny.book.chapters if c.number == "2"][0]
    loops = ch2.sections[0]
    assert loops.title == "Loops"
    assert any("infinite loop" in b.text for b in loops.blocks)


def test_label_and_title_set_as_one_heading() -> None:
    blocks = [
        Block("heading", "Chapter 7 Iteration", 5, 24.0),
        Block("paragraph", "Intro text.", 5, 10.0),
        Block("heading", "7.1 Loops", 5, 14.0),
        Block("paragraph", "Body.", 5, 10.0),
        Block("heading", "7.2 More loops", 6, 14.0),
        Block("heading", "7.3 Even more", 6, 14.0),
        Block("heading", "Chapter 8 Strings", 7, 24.0),
    ]
    book = detect_structure(blocks, "T")
    assert [(c.number, c.title) for c in book.chapters] == [("7", "Iteration"), ("8", "Strings")]
    assert book.chapters[0].intro[0].text == "Intro text."


def test_unnumbered_chapters_are_not_content() -> None:
    blocks = [
        Block("heading", "Preface", 1, 24.0),
        Block("heading", "Chapter 1", 3, 20.0),
        Block("heading", "Start", 3, 24.0),
        Block("heading", "1.1 One", 3, 14.0),
        Block("heading", "1.2 Two", 3, 14.0),
        Block("heading", "1.3 Three", 3, 14.0),
    ]
    book = detect_structure(blocks)
    assert [is_content_chapter(c) for c in book.chapters] == [False, True]


def test_book_without_headings_is_all_front_matter() -> None:
    book = detect_structure([Block("paragraph", "just text", 0, 10.0)])
    assert len(book.chapters) == 1 and not is_content_chapter(book.chapters[0])


def test_markdown_rendering_fences_code(tiny: Conversion) -> None:
    md = book_to_markdown(tiny.book)
    assert "```\ndef double(x):\n    return 2 * x\n```" in md
    assert "### 2.1 Loops" in md


def test_chunks_respect_target_and_section_boundaries(tiny: Conversion) -> None:
    chunks = chunk_book(tiny.book, target=20)
    assert all(c.words <= 40 for c in chunks)
    assert {c.section for c in chunks} >= {"Assignment", "Loops", "Functions"}
    # No chunk mixes two sections: each starts with its own section title.
    for c in chunks:
        if c.section:
            assert c.text.startswith(c.section) or c.uid.endswith(("/1", "/2", "/3"))


def test_excluded_sections_are_not_chunked(tiny: Conversion) -> None:
    chunks = chunk_book(tiny.book, 200, exclude=("glossary",))
    assert not any(c.section == "Glossary" for c in chunks)
    assert not any("variable: A name" in c.text for c in chunks)


def test_long_paragraph_is_split_at_sentences() -> None:
    para = " ".join(f"Sentence number {i} is here." for i in range(30))
    chunks = chunk_pieces([para], target=25)
    assert len(chunks) > 1
    assert all(c.endswith(".") for c in chunks)
    assert " ".join(chunks) == para


def test_chunk_markdown_packs_across_headings_like_book_chunks() -> None:
    md = "# T\n\nintro\n\n## A\n\nalpha text\n\n## B\n\nbeta text\n"
    assert [c.text for c in chunk_markdown({"1": md}, target=200)] == [md.strip()]
    # Regression: splitting at every heading made "200-word" skill chunks
    # average ~44 words, not comparable with book chunks.
    long_md = "\n\n".join(f"## S{i}\n\n" + "word " * 60 for i in range(10))
    chunks = chunk_markdown({"1": long_md}, target=200)
    sizes = [len(c.text.split()) for c in chunks]
    assert len(chunks) == 4 and all(150 <= n <= 200 for n in sizes[:-1])


def test_chunk_markdown_keeps_fenced_code_whole() -> None:
    md = "intro text\n\n```\ndef f():\n\n    return 1\n```\n\nafter"
    chunks = chunk_markdown({"1": md}, target=3)
    assert "```\ndef f():\n\n    return 1\n```" in [c.text for c in chunks]


def test_bm25_ranks_the_matching_document_first() -> None:
    docs = ["cats and dogs", "the variable holds a value", "loops repeat statements"]
    hits = BM25(docs).search("what is a variable", k=3)
    assert hits[0].index == 1
    assert all(h.score > 0 for h in hits)


def test_bm25_rare_terms_outweigh_common_ones() -> None:
    docs = ["python python python list", "python tuple", "python dict"]
    assert BM25(docs).search("python tuple", k=1)[0].index == 1


def test_bm25_ties_break_by_position_and_no_match_returns_nothing() -> None:
    index = BM25(["alpha", "alpha", "beta"])
    assert [h.index for h in index.search("alpha", k=2)] == [0, 1]
    assert index.search("zeta") == []


def test_bm25_rejects_empty_corpus() -> None:
    with pytest.raises(ValueError):
        BM25([])


@pytest.mark.parametrize(
    ("word", "stemmed"),
    [
        ("variables", "variable"),
        ("classes", "class"),
        ("dictionaries", "dictionary"),
        ("this", "this"),
        ("running", "runn"),
        ("focus", "focus"),
    ],
)
def test_stemmer(word: str, stemmed: str) -> None:
    assert stem(word) == stemmed


def test_tokenize_drops_stopwords() -> None:
    assert tokenize("What is the Variable?") == ["variable"]


def thesis_like_pdf(path: Path) -> Path:
    """A thesis whose title page reads like a numbered chapter and whose real
    chapters are unnumbered (the reviewer's Steinberger thesis, reduced)."""
    from booktoskill.samplepdf import PageSpec, write_pdf

    body = "This paragraph is ordinary body text about the topic of the chapter here."
    title = PageSpec().line(600, [("B", "1 Automated Reasoning about Programs")], size=24)
    title.line(560, [("R", "A thesis submitted for the degree of Doctor of Philosophy.")])
    pages = [title]
    for name in ("Introduction", "Methods", "Results"):
        page = PageSpec().line(700, [("B", name)], size=24)
        y = 660
        for sec in ("Background", "Details"):
            page.line(y, [("B", f"{name} {sec}")], size=14)
            y -= 30
            for _ in range(4):
                page.line(y, [("R", body)])
                y -= 14
            y -= 10
        pages.append(page)
    return write_pdf(path, pages)


def test_one_stray_number_does_not_disable_chapter_numbering(tmp_path: Path) -> None:
    from booktoskill.pipeline import convert
    from booktoskill.structure import content_coverage

    book = convert(thesis_like_pdf(tmp_path / "thesis.pdf")).book
    numbered = [(c.number, c.title) for c in book.chapters if is_content_chapter(c)]
    assert numbered == [("1", "Introduction"), ("2", "Methods"), ("3", "Results")]
    assert content_coverage(book) > 0.9


def test_convert_writes_every_chapter_of_the_thesis(tmp_path: Path) -> None:
    from booktoskill.cli import main

    pdf = thesis_like_pdf(tmp_path / "thesis.pdf")
    assert main(["convert", str(pdf), "--out", str(tmp_path / "s")]) == 0
    files = list((tmp_path / "s").glob("*/references/*.md"))
    assert len(files) == 3
