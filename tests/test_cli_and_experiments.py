from __future__ import annotations

from pathlib import Path

import pytest

from booktoskill.cli import main
from booktoskill.experiments import book_specs as specs
from booktoskill.experiments import chapter_page_ranges, check_inputs, find_index_page
from booktoskill.pipeline import Conversion
from booktoskill.references import RefChapter
from booktoskill.skill import build_extractive_skill


def test_help_exits_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "convert" in capsys.readouterr().out


def test_missing_file_is_a_clean_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["inspect", str(tmp_path / "nope.pdf")]) == 2
    assert "no such file" in capsys.readouterr().err


def test_non_pdf_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "book.txt"
    f.write_text("hello", encoding="utf-8")
    assert main(["convert", str(f)]) == 2
    assert "expected a .pdf" in capsys.readouterr().err


def test_corrupt_pdf_is_a_clean_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "bad.pdf"
    f.write_bytes(b"not a pdf at all")
    assert main(["inspect", str(f)]) == 2
    assert "could not read" in capsys.readouterr().err


def test_textless_pdf_says_no_ocr(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from booktoskill.samplepdf import PageSpec, write_pdf

    f = write_pdf(tmp_path / "scan.pdf", [PageSpec()])
    assert main(["inspect", str(f)]) == 2
    assert "does not do OCR" in capsys.readouterr().err


def test_convert_writes_a_skill(
    tiny_pdf: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["convert", str(tiny_pdf), "--out", str(tmp_path), "--markdown"]) == 0
    root = tmp_path / "a-tiny-book"
    assert (root / "SKILL.md").is_file() and (root / "book.md").is_file()
    assert len(list((root / "references").glob("*.md"))) == 2
    assert "wrote" in capsys.readouterr().out


def test_inspect_and_search(tiny_pdf: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["inspect", str(tiny_pdf), "--sections"]) == 0
    out = capsys.readouterr().out
    assert "1 Getting Started" in out and "2.1 Loops" in out
    assert main(["search", str(tiny_pdf), "infinite loop", "-k", "1"]) == 0
    assert "chapter 2 / Loops" in capsys.readouterr().out
    assert main(["search", str(tiny_pdf), "zzzz"]) == 1


def test_experiments_need_their_inputs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="fetch_data"):
        check_inputs(specs(tmp_path))
    assert main(["experiments", "--data", str(tmp_path), "--results", str(tmp_path / "r")]) == 2


def test_chapter_page_ranges_pair_outline_with_reference() -> None:
    refs = [RefChapter("0", "Preface"), RefChapter("1", "Start"), RefChapter("2", "End")]
    outline = [(0, "Preface", 1), (0, "Start", 3), (1, "1.1 x", 3), (0, "End", 7)]
    ranges = chapter_page_ranges(outline, 20, refs, index_page=15)
    assert [(r.title, s, e) for r, s, e in ranges] == [("Start", 3, 7), ("End", 7, 15)]


def test_find_index_page() -> None:
    pages = ["Chapter", "text", "Index\nabstraction, 70", "Index 2"]
    assert find_index_page(pages, after=0) == 2
    assert find_index_page(pages, after=3) is None


def test_code_retention_counts_verbatim_blocks(tiny: Conversion) -> None:
    from booktoskill.experiments import code_retention

    pkg = build_extractive_skill(tiny.book)
    assert code_retention(tiny.book, pkg) == {"book_code_blocks": 1, "in_skill": 1}


def test_convert_without_chapters_explains(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from booktoskill.samplepdf import PageSpec, write_pdf

    spec = PageSpec()
    for i in range(12):
        spec.line(700 - 14 * i, [("R", f"Plain prose with no headings at all, line number {i}.")])
    f = write_pdf(tmp_path / "flat.pdf", [spec])
    assert main(["convert", str(f), "--out", str(tmp_path)]) == 3
    assert "only 0% of the book's text" in capsys.readouterr().err
    assert main(["convert", str(f), "--out", str(tmp_path), "--allow-low-coverage"]) == 2
    assert "no numbered chapters" in capsys.readouterr().err


@pytest.mark.parametrize("k", ["-3", "0"])
def test_search_rejects_non_positive_k(tiny_pdf: Path, k: str) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["search", str(tiny_pdf), "loop", "-k", k])
    assert exc.value.code == 2


def test_inspect_has_no_exclude_option(tiny_pdf: Path) -> None:
    with pytest.raises(SystemExit):
        main(["inspect", str(tiny_pdf), "--exclude-section", "Glossary"])


def test_directory_is_reported_as_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["inspect", str(tmp_path)]) == 2
    assert "is a directory" in capsys.readouterr().err


def test_non_ascii_title_on_a_legacy_console(
    tiny_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io
    import sys

    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252"))
    assert main(["inspect", str(tiny_pdf), "--title", "Ελλάδα — Steinberger"]) == 0
    sys.stdout.flush()
    assert raw.getvalue().startswith(b"title: ??????")  # replaced, not a crash


def test_convert_reports_ratio_and_writes_licence(
    tiny_pdf: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    licence = "Jane Doe, CC BY-NC 3.0"
    assert main(["convert", str(tiny_pdf), "--out", str(tmp_path), "--license", licence]) == 0
    out = capsys.readouterr().out
    assert "reference / chapter words:" in out and "kept" not in out
    skill_md = (tmp_path / "a-tiny-book" / "SKILL.md").read_text(encoding="utf-8")
    assert f'license: "{licence}"' in skill_md.split("---")[1]
    assert f"Extracted from *A Tiny Book*: {licence}." in skill_md


@pytest.mark.parametrize(
    ("title", "junk"),
    [
        ("thesis.dvi", True),
        ("main.tex", True),
        ("Microsoft Word - draft7.docx", True),
        ("Untitled", True),
        ("12345", True),
        ("Think Python", False),
        ("Pro Git", False),
    ],
)
def test_junk_metadata_titles(title: str, junk: bool) -> None:
    from booktoskill.pipeline import junk_title

    assert junk_title(title) is junk


def test_junk_metadata_falls_back_to_title_page(tmp_path: Path) -> None:
    from booktoskill.pipeline import convert
    from booktoskill.samplepdf import tiny_book, write_pdf

    pdf = write_pdf(tmp_path / "t.pdf", tiny_book(), title="thesis.dvi")
    assert convert(pdf).book.title == "A Tiny Book"
