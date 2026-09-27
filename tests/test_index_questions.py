from __future__ import annotations

from pathlib import Path

import pytest

from booktoskill.index_questions import (
    Anchor,
    asciidoc_anchors,
    asciidoc_term,
    asciidoc_text,
    items_from_anchors,
    latex_anchors,
    latex_term,
    sentences,
    split_of,
)


@pytest.mark.parametrize(
    ("entry", "term"),
    [
        ("variable", "variable"),
        ("statement!assignment", "assignment statement"),
        (r"str method@\_\_str\_\_ method", "__str__ method"),
        (r"join@{\tt join}", "join"),
        ("recursion|see{recursive}", "recursion"),
        (r"{\tt 1}", ""),
    ],
)
def test_latex_term(entry: str, term: str) -> None:
    assert latex_term(entry) == term


TEX = r"""
\mainmatter
\chapter{Variables}

\section{Assignment}
\index{assignment statement}
\index{statement!assignment}

An assignment statement creates a new variable and gives it a value
every time the program runs through it.

A state diagram shows what state each of the variables is in at a time.
\index{state diagram}

\begin{verbatim}
x = 1

\index{not an anchor}
\end{verbatim}

\section{Glossary}
\begin{description}
\item[variable:] A name that refers to a value.
\index{variable}
\end{description}

\chapter{Functions}
Every function call makes a new frame that holds the state diagram of its variables.
\index{state diagram}
\index{frame}
"""


def test_latex_anchors_follow_the_authors_placement() -> None:
    anchors = latex_anchors(TEX)
    by_term: dict[str, list[Anchor]] = {}
    for a in anchors:
        by_term.setdefault(a.term, []).append(a)
    # anchors after a heading, before the text, point at the next paragraph
    assert by_term["assignment statement"][0].paragraph.startswith("An assignment statement")
    # anchors at the end of a paragraph point at that paragraph
    assert by_term["state diagram"][0].paragraph.startswith("A state diagram shows")
    assert [a.chapter for a in by_term["state diagram"]] == ["1", "2"]
    assert "variable" not in by_term  # only anchored in the held-out glossary
    assert "not an anchor" not in by_term  # inside a listing
    assert by_term["frame"][0].chapter_title == "Functions"


def test_items_use_the_first_chapter_and_flag_glossary_terms() -> None:
    items = items_from_anchors(latex_anchors(TEX), "demo", glossary_terms={"state diagram"})
    by_term = {it.term: it for it in items}
    sd = by_term["state diagram"]
    assert sd.chapter == "1" and sd.kind == "index" and sd.in_glossary
    assert all("frame" not in s for s in sd.evidence)  # chapter 2's paragraph is not gold
    assert sd.gold_sentence == sd.evidence[0]
    assert not by_term["frame"].in_glossary
    # the two index spellings of one concept are one question
    assert sum(t.lower() == "assignment statement" for t in by_term) == 1
    assert {it.split for it in items} <= {"dev", "test"}


def test_split_is_stable_and_about_one_in_five() -> None:
    terms = [f"term {i}" for i in range(2000)]
    splits = [split_of("book", t) for t in terms]
    assert splits == [split_of("book", t) for t in terms]
    assert split_of("book", "Term 7") == split_of("book", "term 7")
    assert 0.17 < splits.count("test") / len(splits) < 0.23


def test_sentences_drop_short_fragments() -> None:
    assert sentences("Too short. This sentence is long enough to count.") == [
        "This sentence is long enough to count."
    ]


@pytest.mark.parametrize(
    ("entry", "term"),
    [
        ("git commands, add", "git add"),
        ("version control,local", "local version control"),
        ("SHA-1", "SHA-1"),
        (" ", ""),
    ],
)
def test_asciidoc_term(entry: str, term: str) -> None:
    assert asciidoc_term(entry) == term


def test_asciidoc_text_strips_markup() -> None:
    block = (
        "[NOTE]\n====\nRun `git add` to stage a _file_, see <<ch02,Git Basics>> and "
        "https://git-scm.com[the site].(((git commands, add)))\n===="
    )
    assert asciidoc_text(block) == "Run git add to stage a file, see Git Basics and the site."


def test_asciidoc_anchors_follow_includes_and_skip_listings(tmp_path: Path) -> None:
    (tmp_path / "sections").mkdir()
    (tmp_path / "ch01-start.asc").write_text(
        "[[ch01]]\n== Getting Started\n\ninclude::sections/intro.asc[]\n", encoding="utf-8"
    )
    (tmp_path / "sections" / "intro.asc").write_text(
        "=== Intro\n\n(((version control)))\n"
        "What is version control, and why should you care about it at all?\n\n"
        "[source,console]\n----\n$ git init\n\n(((not an anchor)))\n----\n\n"
        "The `git init` command creates a new repository here.(((git commands, init)))\n",
        encoding="utf-8",
    )
    anchors = asciidoc_anchors([("1", tmp_path / "ch01-start.asc")], tmp_path)
    got = {(a.term, a.chapter, a.chapter_title, a.paragraph) for a in anchors}
    assert got == {
        (
            "version control",
            "1",
            "Getting Started",
            "What is version control, and why should you care about it at all?",
        ),
        ("git init", "1", "Getting Started", "The git init command creates a new repository here."),
    }
