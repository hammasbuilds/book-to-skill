from __future__ import annotations

from pathlib import Path

from booktoskill.metrics import (
    bootstrap_ci,
    code_block_recovery,
    contains_evidence,
    defect_counts,
    evidence_coverage,
    fidelity,
    prf,
    title_key,
    vocabulary,
)
from booktoskill.references import detex, gold_from_latex, parse_html_edition

LIG_FI = chr(0xFB01)


def test_fidelity_identical_and_disjoint() -> None:
    same = fidelity("a b c d", "a b c d")
    assert (same.precision, same.recall, same.f1) == (1.0, 1.0, 1.0)
    none = fidelity("x y", "a b")
    assert none.f1 == 0.0
    assert fidelity("", "a").f1 == 0.0


def test_fidelity_penalises_extra_and_missing_text() -> None:
    f = fidelity("a b c HEADER 12", "a b c")
    assert f.recall == 1.0 and f.precision < 1.0
    g = fidelity("a b", "a b c d")
    assert g.precision == 1.0 and g.recall == 0.5


def test_fidelity_ignores_quote_style_but_not_ligatures() -> None:
    assert fidelity("it\u2019s", "it's").f1 == 1.0
    assert fidelity(f"{LIG_FI}rst", "first").f1 == 0.0


def test_defect_counts() -> None:
    vocab = vocabulary("first expression print function")
    d = defect_counts(f"{LIG_FI}rst expres- sion printfunction", vocab)
    assert d == {"ligature_glyphs": 1, "broken_hyphenations": 1, "glued_words": 1}


def test_code_block_recovery_requires_indentation() -> None:
    ref = ["def f(x):\n    return x", "print(1)\nprint(2)", "single"]
    good = code_block_recovery("text\ndef f(x):\n    return x\nprint(1)\nprint(2)", ref)
    assert good == {"blocks": 2, "indented_blocks": 1, "exact": 1.0, "exact_indented": 1.0}
    flat = code_block_recovery("def f(x):\nreturn x\nprint(1)\nprint(2)", ref)
    assert flat["exact"] == 0.5 and flat["exact_indented"] == 0.0


def test_evidence_coverage_and_threshold() -> None:
    gold = "A variable is a name that refers to a value."
    assert evidence_coverage("Intro. " + gold + " More.", gold) == 1.0
    assert evidence_coverage("A variable is a name.", gold) < 0.6
    assert contains_evidence("a variable is a name that refers to a value", gold)
    # ligatures in the unit do not hide evidence
    assert contains_evidence(f"{LIG_FI}nding a variable is a name that refers to a value", gold)
    assert evidence_coverage("anything", "") == 0.0


def test_prf_is_multiset_aware() -> None:
    r = prf(["a", "a", "b"], ["a", "b", "c"])
    assert (r.tp, r.predicted, r.gold) == (2, 3, 3)
    assert prf([], ["a"]).f1 == 0.0


def test_title_key_normalises() -> None:
    assert title_key("Case study: word play") == title_key("Case Study - Word Play")


def test_bootstrap_ci_brackets_the_mean() -> None:
    vals = [1.0] * 30 + [0.0] * 70
    lo, hi = bootstrap_ci(vals)
    assert lo < 0.3 < hi and lo > 0.15 and hi < 0.45
    assert bootstrap_ci([]) == (0.0, 0.0)
    assert bootstrap_ci([1.0, 1.0]) == (1.0, 1.0)


HEVEA = """<html><body><table><tr><td width="600">
<p><a href="http://amzn.to/x">Buy this book at Amazon.com</a>
<h1 class="chapter">Chapter&#XA0;1&#XA0;&#XA0;Getting started</h1>
<p>A <span>variable</span> is a name.</p>
<h2 class="section">1.1&#XA0;&#XA0;Assignment</h2>
<pre class="verbatim">&gt;&gt;&gt; n = 17
&gt;&gt;&gt; n
17
</pre>
<p>More text.</p>
</td><td width=130><h4>Contribute</h4><p>Donate now</p></td></tr></table>
</body></html>"""


def test_parse_html_edition(tmp_path: Path) -> None:
    (tmp_path / "book001.html").write_text(HEVEA, encoding="utf-8")
    chapters = parse_html_edition(tmp_path)
    assert len(chapters) == 1
    ch = chapters[0]
    assert (ch.number, ch.title, ch.numbered) == ("1", "Getting started", True)
    assert [(s.number, s.title) for s in ch.sections] == [("1.1", "Assignment")]
    assert ch.code_blocks == [">>> n = 17\n>>> n\n17"]
    assert "Donate" not in ch.text and "Amazon" not in ch.text
    assert ch.text.startswith("Chapter 1\nGetting started")


TEX = r"""
\frontmatter
\chapter{Preface}
{\bf ignored} front matter.
\mainmatter
\chapter{Variables}

A {\bf variable} is a name that refers to a value.  Values have
{\bf types}.

\begin{verbatim}
x = {\bf not} code
\end{verbatim}

\section{Glossary}
\begin{description}
\item[variable:] A name that refers to a value.
\index{variable}
\item[type:] A category of values.
\item[ghost:] Only in the glossary.
\end{description}

\section{Exercises}
A {\bf ghost} appears here, in an exercise.

\chapter{Stats}
Some {\bf samples} are small.

\section{Glossary}
\begin{itemize}
\item {\bf sample}: A subset of a population.
\end{itemize}
\appendix
\chapter{Extra}
"""


def test_gold_from_latex() -> None:
    items, stats = gold_from_latex(TEX, "demo")
    assert stats == {"glossary_terms": 4, "no_bold_in_body": 1}
    by_term = {it.term: it for it in items}
    assert set(by_term) == {"variable", "type", "sample"}  # plural bold matches
    v = by_term["variable"]
    assert (v.chapter, v.chapter_title, v.qid) == (1, "Variables", "demo-01-00")
    assert v.gold_sentence == "A variable is a name that refers to a value."
    assert v.definition == "A name that refers to a value."
    assert by_term["sample"].chapter == 2
    assert "ghost" not in by_term  # bold only in the Exercises section


def test_detex() -> None:
    tex = r"a {\bf bold} and \verb|x_1| and ``quote'' \index{k}"
    assert detex(tex) == 'a bold and x_1 and "quote"'
    assert detex(r"50\% of \emph{it}~now % a comment") == "50% of it now"
