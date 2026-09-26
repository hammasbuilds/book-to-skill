from __future__ import annotations

from pathlib import Path

import pytest

from booktoskill.cli import main
from booktoskill.experiments import book_specs as specs
from booktoskill.experiments import (
    chapter_page_ranges,
    check_inputs,
    filter_to_pdf,
    find_index_page,
    random_budget_references,
)
from booktoskill.pipeline import Conversion
from booktoskill.references import GoldItem, RefChapter
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


def test_random_control_respects_the_budget(tiny: Conversion) -> None:
    pkg = build_extractive_skill(tiny.book)
    refs = random_budget_references(tiny.book, pkg, seed=0)
    for ch, text in refs.items():
        budget = len(pkg.reference_by_chapter()[ch].split())
        # stops at the first sentence that reaches the budget
        assert len(text.split()) <= budget + 40
    assert refs == random_budget_references(tiny.book, pkg, seed=0)


def test_filter_to_pdf_drops_reworded_items(tiny: Conversion) -> None:
    def item(sentence: str) -> GoldItem:
        return GoldItem("q", "b", 1, "t", "variable", "d", sentence, sentence)

    kept, dropped = filter_to_pdf(
        [
            item("A variable is a name that refers to a value."),
            item("Completely different wording that the book never printed."),
        ],
        tiny,
    )
    assert len(kept) == 1 and dropped == 1


def test_retention_by_threshold_counts_per_corpus() -> None:
    from booktoskill.chunking import Chunk
    from booktoskill.experiments import Corpus, retention_by_threshold

    sentence = "A variable is a name that refers to a value."
    item = GoldItem("q", "b", 1, "t", "variable", "d", sentence, sentence)
    full = Corpus("full", [Chunk("1", "1", "", "Intro. " + sentence)])
    half = Corpus("half", [Chunk("1", "1", "", "A variable is a name that")])
    out = retention_by_threshold([item], [full, half], thresholds=(0.4, 0.8))
    assert out["full"] == {">=0.4": 1, ">=0.8": 1, "n": 1}
    assert out["half"] == {">=0.4": 1, ">=0.8": 0, "n": 1}


def test_code_retention_counts_verbatim_blocks(tiny: Conversion) -> None:
    from booktoskill.experiments import code_retention

    pkg = build_extractive_skill(tiny.book)
    assert code_retention(tiny.book, pkg) == {"book_code_blocks": 1, "in_skill": 1}
