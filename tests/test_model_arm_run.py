"""model_arm.run(), plan() and `book-to-skill model-arm`, end to end with a fake transport."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from booktoskill import model_arm
from booktoskill.cli import main
from booktoskill.experiments import BookSpec
from booktoskill.llm import CachedClient, DiskCache
from booktoskill.references import HEVEA

TINY_TEX = r"""
\mainmatter
\chapter{Getting Started}
This book is a small test of the whole pipeline. A {\bf variable} is a name that
refers to a value.

\section{Glossary}
\begin{description}
\item[variable:] A name that refers to a value.
\end{description}

\chapter{Next Steps}
A loop that never ends is called an {\bf infinite loop}.

\section{Glossary}
\begin{description}
\item[infinite loop:] A loop whose terminating condition is never satisfied.
\item[ghost:] Defined only here.
\end{description}
"""


class Transport:
    """Plays every role the model arm asks for, and counts calls."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, model: str, system: str, prompt: str, options: dict) -> str:
        self.calls += 1
        if "Which reference file" in prompt:
            m = re.search(r"`(references/[^`]+)`", prompt)
            return m.group(1) if m else "no idea"
        if "Reference definition" in prompt:
            return "CORRECT" if "refers to a value" in prompt.split("Candidate")[1] else "INCORRECT"
        if "CHAPTER TEXT" in prompt:
            return (
                "# Chapter\n\n## When to use\nx\n\n## Sections\n### 1.1 A\ny\n\n"
                "## Key definitions\n- **variable**: a name that refers to a value\n\n"
                "## Worked examples\n"
            )
        return "A name that refers to a value." if "Context:" in prompt else "Not sure."


@pytest.fixture()
def tiny_spec(tiny_pdf: Path, tmp_path: Path) -> BookSpec:
    tex = tmp_path / "tiny.tex"
    tex.write_text(TINY_TEX, encoding="utf-8")
    return BookSpec("tiny", "A Tiny Book", tiny_pdf, tmp_path / "no-html", HEVEA, tex)


def clients(cache: Path, transport: Transport) -> tuple[CachedClient, CachedClient]:
    return (
        CachedClient("fake", transport, DiskCache(cache)),
        CachedClient("fake-judge", transport, DiskCache(cache)),
    )


def test_run_end_to_end_matches_plan_and_resumes(tiny_spec: BookSpec, tmp_path: Path) -> None:
    plan = model_arm.plan([tiny_spec])
    assert plan["jobs"][0]["questions"] == 2  # "ghost" has no bold passage
    transport = Transport()
    client, judge = clients(tmp_path / "cache", transport)
    report = model_arm.run([tiny_spec], tmp_path / "res", tmp_path / "out", client, judge, k=2)

    # The dry-run estimate counts requests. Every request is either a real
    # model call or a cache hit (identical prompts, e.g. judging two identical
    # answers, are generated once), so the estimate is an upper bound.
    made, cached = client.calls + judge.calls, client.hits + judge.hits
    assert transport.calls == made and made + cached == plan["total_calls"]
    book = report["books"]["tiny"]
    assert book["generation"]["missing_headings"] == {}
    assert book["term_mentioned"]["llm"] == 0.5  # only "variable" is in the fake files
    table = report["pooled_qa"]["conditions"]
    assert table["-/closed_book"]["judge_accuracy"]["value"] == 0.0
    assert table["-/rag"]["judge_accuracy"]["value"] == 1.0
    assert table["llm/skill"]["route_parsed"] == 1.0
    assert (tmp_path / "res" / "model_arm.json").is_file()
    outcomes = (tmp_path / "res" / "model_outcomes.jsonl").read_text(encoding="utf-8")
    assert len(outcomes.splitlines()) == 2 * (2 + 2 * 2)
    assert (tmp_path / "out" / "llm" / "a-tiny-book" / "SKILL.md").is_file()

    # a second run is served entirely from the cache
    again = Transport()
    client2, judge2 = clients(tmp_path / "cache", again)
    model_arm.run([tiny_spec], tmp_path / "res", tmp_path / "out", client2, judge2, k=2)
    assert again.calls == 0 and client2.hits + judge2.hits == plan["total_calls"]


def test_plan_reports_missing_inputs(tmp_path: Path) -> None:
    spec = BookSpec("x", "X", tmp_path / "x.pdf", tmp_path, HEVEA, tmp_path / "x.tex")
    with pytest.raises(FileNotFoundError, match="fetch_data"):
        model_arm.plan([spec])


@pytest.fixture()
def data_dir(tiny_pdf: Path, tmp_path: Path) -> Path:
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    for key in ("thinkpython2", "thinkstats2"):
        shutil.copy(tiny_pdf, raw / f"{key}.pdf")
        (raw / f"{key}.tex").write_text(TINY_TEX, encoding="utf-8")
    return tmp_path / "data"


def test_cli_dry_run(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["model-arm", "--dry-run", "--data", str(data_dir)]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["total_calls"] == 2 * (2 + 2 * 14)


def test_cli_run_with_fake_ollama(
    data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import booktoskill.llm as llm

    transport = Transport()
    monkeypatch.setattr(llm, "list_models", lambda url: ["qwen2.5:14b-instruct"])
    monkeypatch.setattr(
        llm,
        "ollama_client",
        lambda cache, model, url: CachedClient(model, transport, DiskCache(Path(cache))),
    )
    args = ["model-arm", "--data", str(data_dir), "--results", str(tmp_path / "r")]
    args += ["--out", str(tmp_path / "o"), "--cache", str(tmp_path / "c")]
    assert main(args) == 0
    out = capsys.readouterr().out
    new, cached = map(int, re.search(r"model calls: (\d+) new, (\d+) cached", out).groups())
    assert new == transport.calls and new + cached == 2 * (2 + 2 * 14)
    assert (tmp_path / "r" / "model_arm.json").is_file()


def test_cli_refuses_when_model_not_pulled(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import booktoskill.llm as llm

    monkeypatch.setattr(llm, "list_models", lambda url: ["llama3:8b"])
    assert main(["model-arm", "--data", str(data_dir)]) == 2
    assert "ollama pull" in capsys.readouterr().err
