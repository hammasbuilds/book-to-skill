from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from booktoskill.layout import (
    Block,
    RepairOptions,
    RepairReport,
    build_blocks,
    expand_ligatures,
    roman_to_int,
)
from booktoskill.pdftext import read_pdf
from booktoskill.pipeline import Conversion, blocks_text, convert
from booktoskill.samplepdf import PageSpec, write_pdf


def test_fonts_are_classified_by_their_width_tables(tiny_pdf: Path) -> None:
    pages = read_pdf(tiny_pdf)
    fonts = {r.font.name: r.font for p in pages for ln in p.lines for r in ln.runs}
    assert fonts["/Courier"].mono
    assert not fonts["/Helvetica-Bold"].mono
    # Helvetica's name has no marker; its varying widths keep it proportional.
    assert not fonts["/Helvetica"].mono


def test_text_inside_a_form_xobject_is_flagged_as_figure(tiny_pdf: Path) -> None:
    pages = read_pdf(tiny_pdf)
    flagged = [r.text for ln in pages[2].lines for r in ln.runs if r.in_figure]
    assert flagged and all("fig label" in t for t in flagged)


def test_running_headers_and_page_numbers_are_removed(tiny: Conversion) -> None:
    text = blocks_text(tiny.blocks)
    assert "Chapter 1. Getting Started" not in text
    assert "1.2. Glossary 3" not in text
    assert tiny.report.page_number_offset == 0
    assert tiny.report.header_lines_removed == 4


def test_chapter_openers_survive_header_removal(tiny: Conversion) -> None:
    # "Chapter 1" starts page 1 and carries the right page number, but it is
    # not in the header band, so it must stay.
    assert any(b.text == "Chapter 1" for b in tiny.blocks if b.kind == "heading")


def test_figure_text_is_dropped(tiny: Conversion) -> None:
    assert "fig label" not in blocks_text(tiny.blocks)
    assert tiny.report.figure_runs_removed >= 1


def test_line_break_hyphen_is_joined_but_real_compound_is_kept(tiny: Conversion) -> None:
    text = blocks_text(tiny.blocks)
    assert "Programmers write assignments all the time." in text
    # "well-known" occurs elsewhere unbroken, so the break keeps its hyphen.
    assert "Short functions are a well-known way" in text
    assert "performs a computation is a function. Short" in text
    assert tiny.report.hyphen_joins == 2 and tiny.report.hyphens_kept == 1


def test_code_block_keeps_indentation(tiny: Conversion) -> None:
    code = [b.text for b in tiny.blocks if b.kind == "code"]
    assert code == ["def double(x):\n    return 2 * x"]


def test_word_spaces_are_recovered_at_font_changes(tiny: Conversion) -> None:
    text = blocks_text(tiny.blocks)
    assert "Call it with double(21) to get 42." in text
    assert "Use the print function inside a loop" in text


def test_paragraphs_are_reflowed_across_lines(tiny: Conversion) -> None:
    paras = [b.text for b in tiny.blocks if b.kind == "paragraph"]
    assert (
        "This book is a small test of the whole pipeline. A variable is a name that "
        "refers to a value. The interpreter reads each line and runs it."
    ) in paras


def test_every_repair_can_be_switched_off(tiny_pdf: Path) -> None:
    pages = read_pdf(tiny_pdf)
    off = RepairOptions(**{f.name: False for f in fields(RepairOptions)})
    blocks, report = build_blocks(pages, off)
    text = blocks_text(blocks)
    assert "fig label" in text
    assert "1.2. Glossary 3" in text
    assert "Programmers write assign-\n\nments" in text  # one block per line
    assert report.header_lines_removed == 0 and report.hyphen_joins == 0
    assert not any(b.kind == "code" for b in blocks)


def test_without_dehyphenation_the_break_is_left_visible(tiny_pdf: Path) -> None:
    pages = read_pdf(tiny_pdf)
    blocks, _ = build_blocks(pages, replace(RepairOptions(), dehyphenate=False))
    assert "assign- ments" in blocks_text(blocks)
    assert "\u2029" not in blocks_text(blocks)


def test_ligatures_expand_and_are_counted() -> None:
    text, n = expand_ligatures("\ufb01rst \ufb02oat e\ufb03cient")
    assert text == "first float efficient"
    assert n == 3


@pytest.mark.parametrize(("token", "value"), [("xxii", 22), ("iv", 4), ("mcm", 1900), ("ab", None)])
def test_roman_numerals(token: str, value: int | None) -> None:
    assert roman_to_int(token) == value


def test_kerning_split_is_rejoined_only_for_attested_words(tmp_path: Path) -> None:
    spec = PageSpec()
    spec.line(700, [("R", "Tuples are immutable, and tuples can be compared.")])
    spec.line(600, [("B", "T uples")], size=24)
    spec.line(560, [("B", "W e")], size=24)
    pages = read_pdf(write_pdf(tmp_path / "k.pdf", [spec]))
    blocks, report = build_blocks(pages)
    headings = [b.text for b in blocks if b.kind == "heading"]
    assert "Tuples" in headings
    assert report.kerning_joins == 1  # "We" is not attested in the body text


def test_convert_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        convert(tmp_path / "nope.pdf")


def test_blocks_text_joins_with_blank_lines() -> None:
    assert blocks_text([Block("paragraph", "a", 0), Block("code", "b", 0)]) == "a\n\nb"


def test_empty_pdf_gives_no_blocks(tmp_path: Path) -> None:
    pages = read_pdf(write_pdf(tmp_path / "empty.pdf", [PageSpec()]))
    blocks, report = build_blocks(pages)
    assert blocks == [] and report == replace(RepairReport(), body_size=10.0)


def test_blank_line_inside_a_listing_is_kept(tmp_path: Path) -> None:
    spec = PageSpec()
    spec.line(700, [("R", "Here is a function with a blank line in it, set in a listing")])
    spec.line(686, [("R", "that follows this paragraph of ordinary prose, like so:")])
    spec.line(662, [("M", "def clean(df):")])
    spec.line(648, [("M", "df.age /= 100")], x=72 + 4 * 6)
    spec.line(620, [("M", "return df")], x=72 + 4 * 6)
    spec.line(596, [("R", "That is the whole function, and the text goes on from here")])
    spec.line(582, [("R", "for another line or two, at the usual line spacing.")])
    blocks, _ = build_blocks(read_pdf(write_pdf(tmp_path / "c.pdf", [spec])))
    code = [b.text for b in blocks if b.kind == "code"]
    assert code == ["def clean(df):\n    df.age /= 100\n\n    return df"]


def test_parse_tounicode_handles_bfchar_and_both_bfrange_forms() -> None:
    from booktoskill.pdftext import parse_tounicode

    cmap = (
        b"2 beginbfchar\n<0003> <0020>\n<0004> <00660069>\nendbfchar\n"
        b"2 beginbfrange\n<0010> <0012> <0061>\n<0020> <0021> [<0041> <0042>]\nendbfrange\n"
    )
    assert parse_tounicode(cmap) == {
        3: " ",
        4: "fi",
        0x10: "a",
        0x11: "b",
        0x12: "c",
        0x20: "A",
        0x21: "B",
    }


def test_edge_numbers_ignore_non_ascii_digits() -> None:
    from booktoskill.layout import _edge_number

    assert _edge_number("12 Chapter 2. Variables") == ("arabic", 12)
    assert _edge_number("vii") == ("roman", 7)
    # Pro Git marks code callouts with circled digits, which str.isdigit accepts
    assert _edge_number(chr(0x2461) + " callout") is None


def test_unattested_breaks_follow_the_books_own_habit(tmp_path: Path) -> None:
    # A ragged-right book: its only attested break is a real compound, so an
    # unattested break ("branch-" / "management") keeps its hyphen too.
    spec = PageSpec()
    spec.line(700, [("R", "We use a well-")])
    spec.line(686, [("R", "known workflow here, which is a well-known thing to say, and")])
    spec.line(672, [("R", "then we discuss branch-")])
    spec.line(658, [("R", "management in the next part of the chapter.")])
    blocks, report = build_blocks(read_pdf(write_pdf(tmp_path / "r.pdf", [spec])))
    text = blocks_text(blocks)
    assert "well-known workflow" in text and "branch-management" in text
    assert report.hyphens_kept == 2 and report.hyphen_joins == 0


def test_indentation_drawn_as_no_break_spaces_is_kept(tmp_path: Path) -> None:
    # Asciidoctor PDF (Prawn) starts every code line at the same x and draws
    # the indentation as a no-break space followed by spaces.
    nbsp = chr(0xA0)
    spec = PageSpec()
    spec.line(700, [("R", "Some prose before the listing, long enough to look like a line:")])
    spec.line(686, [("R", "and a second line of prose that ends the paragraph right here.")])
    spec.line(662, [("M", "if ready:")])
    spec.line(648, [("M", nbsp + "   go()")])
    spec.line(620, [("R", "More prose follows the listing on the next line down the page.")])
    spec.line(606, [("R", "And one more line of prose to settle the line spacing for good.")])
    blocks, _ = build_blocks(read_pdf(write_pdf(tmp_path / "p.pdf", [spec])))
    assert [b.text for b in blocks if b.kind == "code"] == ["if ready:\n    go()"]
