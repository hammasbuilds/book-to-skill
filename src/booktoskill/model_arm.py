"""The model arm, end to end: generate the model-written skill, then answer.

Nothing here runs at import or in the test suite against a real server; tests
drive it with ``FakeClient``. ``scripts/run_models.sh`` runs it for real.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from booktoskill.answering import CONDITIONS, Outcome, calls_per_item, run_item
from booktoskill.bm25 import BM25
from booktoskill.chunking import chunk_book, chunk_markdown, whole_files
from booktoskill.experiments import (
    HOLDOUT,
    BookSpec,
    Corpus,
    book_specs,
    check_inputs,
    filter_to_pdf,
    load_gold,
    run_retrieval,
    summarise_retrieval,
)
from booktoskill.llm import Client
from booktoskill.llm_skill import build_llm_skill
from booktoskill.metrics import bootstrap_ci
from booktoskill.pipeline import Conversion, convert
from booktoskill.references import GoldItem
from booktoskill.skill import SkillPackage, build_extractive_skill, write_skill
from booktoskill.structure import is_content_chapter


@dataclass
class BookJob:
    spec: BookSpec
    conv: Conversion
    items: list[GoldItem]
    extractive: SkillPackage


def prepare(spec: BookSpec) -> BookJob:
    conv = convert(spec.pdf, title=spec.title)
    items, _ = load_gold(spec)
    items, _ = filter_to_pdf(items, conv)
    return BookJob(spec, conv, items, build_extractive_skill(conv.book, exclude=HOLDOUT))


def term_mentioned(items: list[GoldItem], refs: dict[str, str]) -> float:
    """Share of questions whose term appears in its chapter's reference file.

    A looser test than verbatim evidence, fair to a writer that paraphrases.
    """
    if not items:
        return 0.0
    hits = 0
    for it in items:
        text = refs.get(str(it.chapter), "").lower()
        hits += bool(re.search(r"\b" + re.escape(it.term.lower()), text))
    return hits / len(items)


def plan(data_dir: str | Path) -> dict:
    """The job list and call count, without calling any model."""
    specs = [s for s in book_specs(data_dir) if s.tex is not None]  # books with questions
    check_inputs(specs)
    per_item = calls_per_item(n_skills=2)
    jobs = []
    total = 0
    for spec in specs:
        job = prepare(spec)
        chapters = sum(1 for ch in job.conv.book.chapters if is_content_chapter(ch))
        calls = chapters + len(job.items) * per_item["total"]
        total += calls
        jobs.append(
            {
                "book": spec.key,
                "skill_generation_calls": chapters,
                "questions": len(job.items),
                "qa_calls": len(job.items) * per_item["total"],
                "calls": calls,
            }
        )
    return {"jobs": jobs, "calls_per_question": per_item, "total_calls": total}


def _rate(values: list[float]) -> dict:
    lo, hi = bootstrap_ci(values)
    return {"value": round(sum(values) / len(values), 4), "ci95": [round(lo, 4), round(hi, 4)]}


def summarise(outcomes: list[Outcome]) -> dict:
    by: dict[tuple[str, str], dict[str, Outcome]] = {}
    for o in outcomes:
        by.setdefault((o.skill_variant, o.condition), {})[o.qid] = o
    table = {}
    for (variant, condition), rows in sorted(by.items()):
        vals = list(rows.values())
        entry = {
            "n": len(vals),
            "judge_accuracy": _rate([float(o.correct) for o in vals]),
            "token_f1": round(sum(o.f1 for o in vals) / len(vals), 4),
        }
        if condition in ("skill", "both"):
            entry["route_parsed"] = round(sum(o.routed_ok for o in vals) / len(vals), 4)
            entry["routed_to_gold_chapter"] = _rate([float(o.routed_to_gold_chapter) for o in vals])
        table[f"{variant}/{condition}"] = entry
    diffs = {}
    rag = by.get(("-", "rag"), {})
    for (variant, condition), rows in by.items():
        if condition in ("skill", "both", "closed_book"):
            common = sorted(set(rows) & set(rag))
            if common:
                d = [float(rows[q].correct) - float(rag[q].correct) for q in common]
                diffs[f"{variant}/{condition} minus rag"] = _rate(d)
    return {"conditions": table, "paired_vs_rag": diffs}


def run(
    data_dir: str | Path,
    results_dir: str | Path,
    out_dir: str | Path,
    client: Client,
    judge_client: Client,
    k: int = 5,
) -> dict:
    specs = [s for s in book_specs(data_dir) if s.tex is not None]  # books with questions
    check_inputs(specs)
    results_dir, out_dir = Path(results_dir), Path(out_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {"model": client.model, "judge": judge_client.model, "books": {}}
    outcomes: list[Outcome] = []
    for spec in specs:
        job = prepare(spec)
        budgets = {
            ch: len(text.split()) for ch, text in job.extractive.reference_by_chapter().items()
        }
        llm_pkg, gen = build_llm_skill(job.conv.book, client, budgets, exclude=HOLDOUT)
        write_skill(llm_pkg, out_dir / "llm")
        write_skill(job.extractive, out_dir / "extractive")
        refs = llm_pkg.reference_by_chapter()
        chunks = chunk_book(job.conv.book, 200, HOLDOUT)
        extractive_refs = job.extractive.reference_by_chapter()
        retrieval = summarise_retrieval(
            run_retrieval(
                job.items,
                [
                    Corpus("book_chunks", chunks),
                    Corpus("skill_reference_files", whole_files(extractive_refs)),
                    Corpus("llm_skill_reference_chunks", chunk_markdown(refs, 200)),
                    Corpus("llm_skill_reference_files", whole_files(refs)),
                ],
            )
        )
        index = BM25([c.text for c in chunks])
        skills = {"extractive": job.extractive, "llm": llm_pkg}
        book_outcomes: list[Outcome] = []
        for item in job.items:
            book_outcomes.extend(run_item(client, judge_client, item, skills, index, chunks, k))
        outcomes.extend(book_outcomes)
        report["books"][spec.key] = {
            "generation": asdict(gen),
            "llm_skill_words": sum(len(t.split()) for t in refs.values()),
            "extractive_skill_words": sum(budgets.values()),
            "term_mentioned": {
                "extractive": round(term_mentioned(job.items, extractive_refs), 4),
                "llm": round(term_mentioned(job.items, refs), 4),
            },
            "llm_skill_retrieval": retrieval,
            "qa": summarise(book_outcomes),
        }
    report["pooled_qa"] = summarise(outcomes)
    report["conditions"] = list(CONDITIONS)
    (results_dir / "model_arm.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8", newline="\n"
    )
    with (results_dir / "model_outcomes.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for o in outcomes:
            fh.write(json.dumps(asdict(o), ensure_ascii=False) + "\n")
    return report
