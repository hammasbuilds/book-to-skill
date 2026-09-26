from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from booktoskill.answering import (
    Outcome,
    calls_per_item,
    judge,
    question,
    route,
    run_item,
    token_f1,
)
from booktoskill.bm25 import BM25
from booktoskill.chunking import chunk_book
from booktoskill.llm import CachedClient, DiskCache, FakeClient, cache_key
from booktoskill.llm_skill import REQUIRED_HEADINGS, build_llm_skill, chapter_markdown
from booktoskill.model_arm import summarise, term_mentioned
from booktoskill.pipeline import Conversion
from booktoskill.references import GoldItem
from booktoskill.skill import (
    MAX_DESCRIPTION,
    build_extractive_skill,
    skill_markdown,
    skill_name,
    write_skill,
)

ITEM = GoldItem(
    qid="t-01-00",
    book="tiny",
    chapter=1,
    chapter_title="Getting Started",
    term="variable",
    definition="A name that refers to a value.",
    gold_passage="A variable is a name that refers to a value.",
    gold_sentence="A variable is a name that refers to a value.",
)


def frontmatter(md: str) -> dict[str, str]:
    m = re.match(r"---\n(.*?)\n---\n", md, re.S)
    assert m, "SKILL.md must start with YAML frontmatter"
    out = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(": ")
        out[key] = json.loads(value) if value.startswith('"') else value
    return out


def test_extractive_skill_package_layout(tiny: Conversion, tmp_path: Path) -> None:
    pkg = build_extractive_skill(tiny.book)
    root = write_skill(pkg, tmp_path)
    assert root.name == "a-tiny-book"
    fm = frontmatter((root / "SKILL.md").read_text(encoding="utf-8"))
    assert fm["name"] == "a-tiny-book"
    assert "Getting Started; Next Steps" in fm["description"]
    files = sorted(p.name for p in (root / "references").iterdir())
    assert files == ["ch01-getting-started.md", "ch02-next-steps.md"]
    ref = (root / "references" / "ch01-getting-started.md").read_text(encoding="utf-8")
    for heading in ("## When to use", "## Sections", "## Key definitions", "## Worked examples"):
        assert heading in ref
    assert "A variable is a name that refers to a value." in ref  # a defining sentence
    assert "def double(x):\n    return 2 * x" in ref  # a worked example, indented


def test_skill_md_indexes_every_chapter_file(tiny: Conversion) -> None:
    pkg = build_extractive_skill(tiny.book)
    for fname in pkg.references:
        assert f"`{fname}`" in pkg.skill_md
    assert pkg.chapter_files == {
        "1": "references/ch01-getting-started.md",
        "2": "references/ch02-next-steps.md",
    }


def test_excluded_sections_do_not_reach_the_skill(tiny: Conversion) -> None:
    pkg = build_extractive_skill(tiny.book, exclude=("Glossary",))
    ref = pkg.reference_by_chapter()["1"]
    assert "Glossary" not in ref and "variable: A name" not in ref


def test_definitions_can_be_disabled(tiny: Conversion) -> None:
    pkg = build_extractive_skill(tiny.book, max_definitions=0)
    assert all("## Key definitions" not in t for t in pkg.references.values())


def test_description_is_capped_and_quoted() -> None:
    from booktoskill.structure import Chapter

    chapters = [Chapter(str(i), f"A: long chapter title number {i}", 0) for i in range(1, 80)]
    files = {c.number: f"references/ch{c.number}.md" for c in chapters}
    md = skill_markdown("x", 'Book "Q"', chapters, files, [["t"]] * len(chapters))
    fm = frontmatter(md)
    assert len(fm["description"]) <= MAX_DESCRIPTION
    assert fm["description"].endswith("...")


def test_skill_name_is_valid() -> None:
    name = skill_name("Think Python: How to Think Like a Computer Scientist (2nd Edition!!)" * 2)
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64


def test_no_chapters_is_an_error() -> None:
    from booktoskill.structure import Book

    with pytest.raises(ValueError, match="no numbered chapters"):
        build_extractive_skill(Book("t", [], {}))


def test_disk_cache_resumes_without_new_calls(tmp_path: Path) -> None:
    seen: list[str] = []

    def transport(model: str, system: str, prompt: str, options: dict) -> str:
        seen.append(prompt)
        return f"reply to {prompt}"

    client = CachedClient("m", transport, DiskCache(tmp_path))
    assert client.generate("hello") == "reply to hello"
    again = CachedClient("m", transport, DiskCache(tmp_path))
    assert again.generate("hello") == "reply to hello"
    assert (client.calls, again.calls, again.hits) == (1, 0, 1)
    assert seen == ["hello"]
    # a different model or option is a different key
    assert cache_key("m", "", "p", {"t": 0}) != cache_key("m2", "", "p", {"t": 0})
    assert cache_key("m", "", "p", {"t": 0}) != cache_key("m", "", "p", {"t": 1})


def fake_reference(prompt: str, system: str) -> str:
    title = re.search(r'chapter (\S+), "([^"]+)"', prompt)
    assert title
    return (
        f"# Chapter {title.group(1)}: {title.group(2)}\n\n## When to use\nQuestions.\n\n"
        "## Sections\n### x\nSummary.\n\n## Key definitions\n- **variable**: a name.\n"
    )


def test_llm_skill_with_fake_model(tiny: Conversion) -> None:
    client = FakeClient(fake_reference)
    pkg, report = build_llm_skill(tiny.book, client, budgets={"1": 50, "2": 60})
    assert len(client.prompts) == 2
    assert "under 50 words" in client.prompts[0] and "under 60 words" in client.prompts[1]
    assert "def double(x):" in client.prompts[0]  # the chapter text is in the prompt
    assert report.missing_headings == {"1": ["## Worked examples"], "2": ["## Worked examples"]}
    assert set(pkg.references) == {
        "references/ch01-getting-started.md",
        "references/ch02-next-steps.md",
    }


def test_chapter_markdown_truncates(tiny: Conversion) -> None:
    ch = [c for c in tiny.book.chapters if c.number == "1"][0]
    assert len(chapter_markdown(ch, (), max_words=20).split()) <= 20
    assert "Glossary" not in chapter_markdown(ch, ("glossary",), max_words=10_000)


def test_required_headings_match_extractive_writer(tiny: Conversion) -> None:
    ref = build_extractive_skill(tiny.book).reference_by_chapter()["1"]
    assert all(h in ref for h in REQUIRED_HEADINGS)


def test_routing_parses_and_falls_back(tiny: Conversion) -> None:
    pkg = build_extractive_skill(tiny.book)
    ok = FakeClient(lambda p, s: "references/ch02-next-steps.md")
    assert route(ok, pkg, ITEM) == ("references/ch02-next-steps.md", True)
    bare = FakeClient(lambda p, s: "Read ch01-getting-started.md please")
    assert route(bare, pkg, ITEM) == ("references/ch01-getting-started.md", True)
    junk = FakeClient(lambda p, s: "I am not sure")
    assert route(junk, pkg, ITEM) == ("references/ch01-getting-started.md", False)


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [("CORRECT", True), ("correct.", True), ("INCORRECT", False), ("", False), ("Yes", False)],
)
def test_judge_parsing(verdict: str, expected: bool) -> None:
    assert judge(FakeClient(lambda p, s: verdict), ITEM, "x") is expected


def test_token_f1() -> None:
    assert token_f1("A name that refers to a value.", ITEM.definition) == 1.0
    assert token_f1("", ITEM.definition) == 0.0
    assert 0 < token_f1("a name", ITEM.definition) < 1


def test_run_item_makes_exactly_the_estimated_calls(tiny: Conversion) -> None:
    extractive = build_extractive_skill(tiny.book)
    skills = {"extractive": extractive, "llm": extractive}

    def responder(prompt: str, system: str) -> str:
        if "Which reference file" in prompt:
            return "references/ch01-getting-started.md"
        if "Reference definition" in prompt:
            return (
                "CORRECT"
                if "refers to a value" in prompt.split("Candidate answer:")[1]
                else "INCORRECT"
            )
        return "A name that refers to a value." if "Context:" in prompt else "No idea."

    answerer, grader = FakeClient(responder), FakeClient(responder)
    chunks = chunk_book(tiny.book, 200)
    outcomes = run_item(answerer, grader, ITEM, skills, BM25([c.text for c in chunks]), chunks, k=2)
    est = calls_per_item(n_skills=2)
    assert len(answerer.prompts) == est["answer_and_route"]
    assert len(grader.prompts) == est["judge"]
    by = {(o.skill_variant, o.condition): o for o in outcomes}
    assert not by[("-", "closed_book")].correct
    assert by[("-", "rag")].correct and by[("llm", "both")].correct
    assert by[("extractive", "skill")].routed_to_gold_chapter
    assert question(ITEM) == 'In the book, what is meant by "variable"?'


def test_summarise_pairs_conditions_against_rag() -> None:
    outcomes = [
        Outcome("q1", "-", "rag", "a", True, 1.0),
        Outcome("q2", "-", "rag", "a", False, 0.0),
        Outcome("q1", "llm", "skill", "a", True, 1.0, "f", True, True),
        Outcome("q2", "llm", "skill", "a", True, 1.0, "f", True, False),
    ]
    s = summarise(outcomes)
    assert s["conditions"]["-/rag"]["judge_accuracy"]["value"] == 0.5
    assert s["conditions"]["llm/skill"]["routed_to_gold_chapter"]["value"] == 0.5
    assert s["paired_vs_rag"]["llm/skill minus rag"]["value"] == 0.5


def test_term_mentioned() -> None:
    refs = {"1": "A Variable holds values."}
    assert term_mentioned([ITEM], refs) == 1.0
    assert term_mentioned([ITEM], {"2": "variable"}) == 0.0
    assert term_mentioned([], refs) == 0.0
