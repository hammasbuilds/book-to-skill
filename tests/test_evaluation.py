from __future__ import annotations

import random

from booktoskill.chunking import Chunk
from booktoskill.evaluation import (
    Corpus,
    SetRun,
    budget_hits,
    evaluate,
    filter_to_pdf,
    queries,
    random_budget_references,
    skill_variants,
    summarise,
)
from booktoskill.layout import Block
from booktoskill.metrics import Evidence, cluster_bootstrap_ci, contains_evidence
from booktoskill.pipeline import Conversion
from booktoskill.references import GoldItem
from booktoskill.skill import build_extractive_skill
from booktoskill.structure import Book, Chapter, Section

S1 = "A variable is a name that refers to a value."
S2 = "Loops can also be nested inside each other, which is common when processing tables."


def glossary_item(sentence: str, chapter: int = 1) -> GoldItem:
    return GoldItem("q", "b", chapter, "t", "variable", "d", sentence, sentence)


def index_item(term: str, evidence: tuple[str, ...], chapter: str = "1", **kw) -> GoldItem:
    return GoldItem(
        f"i-{term}", "b", chapter, "t", term, "", "", evidence[0], evidence, "index", **kw
    )


def test_evidence_matches_contains_evidence() -> None:
    rng = random.Random(1)
    words = [
        "a",
        "variable",
        "is",
        "name",
        "that",
        "refers",
        "to",
        "value",
        "loop",
        "the",
        "of",
        "list",
    ]
    for _ in range(300):
        gold = " ".join(rng.choice(words) for _ in range(rng.randint(3, 12)))
        unit = " ".join(rng.choice(words) for _ in range(rng.randint(0, 40)))
        assert Evidence.of([gold]).found_in(unit) == contains_evidence(unit, gold)


def test_any_gold_sentence_counts() -> None:
    ev = Evidence.of([S1, S2, "too short"])
    assert len(ev.grams) == 2  # "too short" has no trigram
    assert ev.found_in("intro " + S2) and not ev.found_in("nothing relevant here at all")


def test_queries_by_kind() -> None:
    assert queries(index_item("frame", (S1,))) == {"term": "Where does the book explain frame?"}
    assert set(queries(glossary_item(S1))) == {"term", "definition"}


def test_filter_to_pdf_keeps_only_printed_gold_sentences(tiny: Conversion) -> None:
    kept, dropped = filter_to_pdf(
        [
            glossary_item(S1),
            glossary_item("Completely different wording that the book never printed."),
            index_item("variable", ("Never printed in this book, not even once.", S1)),
        ],
        tiny,
    )
    assert dropped == 1 and len(kept) == 2
    assert kept[1].evidence == (S1,) and kept[1].gold_sentence == S1


def test_budget_hits_truncates_the_crossing_unit() -> None:
    gold = Evidence.of([S1])
    texts = ["lorem " * 100, "Intro words here. " + S1]
    flags = [False, True]
    assert not budget_hits(texts, flags, gold, 100)  # budget spent on the first unit
    assert not budget_hits(texts, flags, gold, 103)  # gold cut off mid-sentence
    assert budget_hits(texts, flags, gold, 115)  # gold fits in the truncated unit
    assert budget_hits([S1], [True], gold, 1000)


def synthetic_book() -> Book:
    prose = " ".join(f"Sentence {i} talks about loops and lists at length." for i in range(80))
    defs = " ".join(f"A thing{i} is called a widget{i} in this book." for i in range(12))
    ch = Chapter("1", "C", 0)
    ch.sections = [Section("1.1", "S", 0, [Block("paragraph", defs + " " + prose, 0)])]
    return Book("B", [ch], {})


def test_random_control_uses_each_variants_own_budget() -> None:
    book = synthetic_book()
    variants = skill_variants(book)
    budget = {n: len(p.reference_by_chapter()["1"].split()) for n, p in variants.items()}
    got = {n: len(random_budget_references(book, p, 0)["1"].split()) for n, p in variants.items()}
    # Regression: the no-definitions skill was compared with random text at the
    # full skill's (larger) budget.
    assert budget["skill_without_definitions"] < budget["skill"]
    for name in variants:
        assert budget[name] <= got[name] < budget[name] + 15
    pkg = build_extractive_skill(book)
    assert random_budget_references(book, pkg, 3) == random_budget_references(book, pkg, 3)


def test_evaluate_and_summarise(tiny: Conversion) -> None:
    variants = skill_variants(tiny.book)
    corpus = Corpus(
        "book_chunks", [Chunk("1/a", "1", "", "Intro. " + S1), Chunk("2/a", "2", "", S2)]
    )
    items = [
        index_item("variable", (S1,), split="test"),
        index_item("nested loop", (S2,), chapter="2", split="dev", in_glossary=True),
    ]
    run = evaluate(items, tiny.book, [corpus], variants, seeds=3)
    assert run.best["book_chunks"] == [1.0, 1.0]
    assert run.kept["skill"] == [True, False]  # S1 is a defining sentence; S2 is not
    assert run.regex == [True, False] and run.defs_section == [True, False]
    assert len(run.random_kept["skill"]) == 3
    out = summarise(run)
    assert out["n"] == 2
    assert out["corpora"]["book_chunks"]["term"]["recall@1"]["value"] == 1.0
    rule = out["controls"]["definition_rule"]
    assert rule["gold_matching"] == 1 and rule["skill_on_matching"]["kept"]["value"] == 1.0
    assert rule["skill_on_not_matching"]["kept"]["value"] == 0.0
    test_only = run.subset([it.split == "test" for it in run.items])
    assert [it.term for it in test_only.items] == ["variable"]
    assert test_only.random_kept["skill"][0] == run.random_kept["skill"][0][:1]
    both = SetRun()
    both.extend(run)
    both.extend(test_only)
    assert len(both.items) == 3 and len(both.random_kept["skill"][2]) == 3
    assert both.corpora["book_chunks"]["units"] == 4


def test_cluster_bootstrap_is_wider_when_chapters_differ() -> None:
    from booktoskill.metrics import bootstrap_ci

    values = [1.0] * 20 + [0.0] * 20
    clusters = ["a"] * 20 + ["b"] * 20
    lo, hi = cluster_bootstrap_ci(values, clusters)
    ilo, ihi = bootstrap_ci(values)
    assert hi - lo > ihi - ilo
    assert cluster_bootstrap_ci([0.5, 0.5], ["x", "y"]) == (0.5, 0.5)
    assert cluster_bootstrap_ci([], []) == (0.0, 0.0)
