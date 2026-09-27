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


def test_budget_hits_truncates_the_crossing_unit() -> None:
    from booktoskill.experiments import budget_hits

    gold = "A variable is a name that refers to a value."
    filler = "lorem " * 100
    texts = [filler, "Intro words here. " + gold]
    flags = [False, True]
    assert not budget_hits(texts, flags, gold, 100)  # budget spent on the first unit
    assert not budget_hits(texts, flags, gold, 103)  # gold cut off mid-sentence
    assert budget_hits(texts, flags, gold, 115)  # gold fits in the truncated unit
    assert budget_hits([gold], [True], gold, 1000)


def test_random_control_uses_each_variants_own_budget() -> None:
    from booktoskill.experiments import skill_variants
    from booktoskill.layout import Block
    from booktoskill.structure import Book, Chapter, Section

    prose = " ".join(f"Sentence {i} talks about loops and lists at length." for i in range(80))
    defs = " ".join(f"A thing{i} is called a widget{i} in this book." for i in range(12))
    ch = Chapter("1", "C", 0)
    ch.sections = [Section("1.1", "S", 0, [Block("paragraph", defs + " " + prose, 0)])]
    book = Book("B", [ch], {})
    variants = skill_variants(book)
    budget = {n: len(p.reference_by_chapter()["1"].split()) for n, p in variants.items()}
    got = {n: len(random_budget_references(book, p, 0)["1"].split()) for n, p in variants.items()}
    # Regression: the no-definitions skill was compared with random text at the
    # full skill's (larger) budget.
    assert budget["skill_without_definitions"] < budget["skill"]
    for name in variants:
        assert budget[name] <= got[name] < budget[name] + 15


def test_controls_and_counts_are_summarised_over_seeds() -> None:
    from booktoskill.experiments import _add_counts, describe_controls

    total: dict = {}
    _add_counts(
        total, {"skill": {"kept": 3, "words": 10, "random_same_budget_kept_by_seed": [1, 2]}}
    )
    _add_counts(
        total, {"skill": {"kept": 1, "words": 5, "random_same_budget_kept_by_seed": [1, 0]}}
    )
    assert total == {"skill": {"kept": 4, "words": 15, "random_same_budget_kept_by_seed": [2, 2]}}
    d = describe_controls(total, n=8)["skill"]
    assert d["kept"] == 0.5 and d["random_same_budget_mean"] == 0.25 and d["seeds"] == 2


def test_definition_rule_overlap_counts_regex_matches(tiny: Conversion) -> None:
    from booktoskill.experiments import definition_rule_overlap, skill_variants

    s1 = "A variable is a name that refers to a value."
    s2 = "Loops can also be nested inside each other, which is common when processing tables."
    items = [
        GoldItem("a", "b", 1, "t", "variable", "d", s1, s1),
        GoldItem("b", "b", 2, "t", "nested", "d", s2, s2),
    ]
    d = definition_rule_overlap(items, tiny.book, skill_variants(tiny.book))
    assert d["gold"] == 2 and d["gold_matching"] == 1
    assert d["kept_by_skill_matching"] == 1 and d["kept_by_definitions_section"] == 1
    assert 0 < d["book_sentences_matching"] < d["book_sentences"]
