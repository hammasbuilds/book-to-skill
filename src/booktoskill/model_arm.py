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
from booktoskill.evaluation import (
    CHUNK_WORDS,
    HOLDOUT,
    Corpus,
    evaluate,
    filter_to_pdf,
)
from booktoskill.evaluation import summarise as summarise_set
from booktoskill.experiments import BookSpec, glossary_terms, load_gold, load_index
from booktoskill.llm import Client
from booktoskill.llm_skill import MAX_CHAPTER_WORDS, build_llm_skill, chapter_markdown
from booktoskill.metrics import bootstrap_ci
from booktoskill.pipeline import Conversion, convert
from booktoskill.references import GoldItem
from booktoskill.skill import SkillPackage, build_extractive_skill, write_skill
from booktoskill.structure import is_content_chapter


@dataclass
class BookJob:
    spec: BookSpec
    conv: Conversion
    items: list[GoldItem]  # glossary questions: they have reference answers
    index_items: list[GoldItem]  # index questions: retention and retrieval only
    extractive: SkillPackage


def prepare(spec: BookSpec) -> BookJob:
    conv = convert(spec.pdf, title=spec.title)
    items, _ = load_gold(spec)
    items, _ = filter_to_pdf(items, conv)
    index_items, _ = filter_to_pdf(load_index(spec, glossary_terms(spec)), conv)
    extractive = build_extractive_skill(conv.book, exclude=HOLDOUT)
    return BookJob(spec, conv, items, index_items, extractive)


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


def question_books(specs: list[BookSpec]) -> list[BookSpec]:
    """The books with a question set, after checking their PDF and LaTeX exist."""
    books = [s for s in specs if s.tex is not None]
    missing = [str(p) for s in books for p in (s.pdf, s.tex) if p is None or not p.exists()]
    if missing:
        raise FileNotFoundError(
            "missing inputs (run scripts/fetch_data.sh first): " + ", ".join(missing)
        )
    return books


def plan(specs: list[BookSpec], judges: int = 1) -> dict:
    """The job list and call count, without calling any model."""
    specs = question_books(specs)
    per_item = calls_per_item(n_skills=2, judges=judges)
    jobs = []
    total = 0
    for spec in specs:
        job = prepare(spec)
        content = [ch for ch in job.conv.book.chapters if is_content_chapter(ch)]
        chapters = len(content)
        calls = chapters + len(job.items) * per_item["total"]
        total += calls
        cut = {
            ch.number: [t.kept_words, t.words]
            for ch in content
            if (t := chapter_markdown(ch, HOLDOUT, MAX_CHAPTER_WORDS)).truncated
        }
        jobs.append(
            {
                "book": spec.key,
                "skill_generation_calls": chapters,
                "chapters_truncated_for_the_writer": cut,
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
    out = {"conditions": table, "paired_vs_rag": diffs}
    pairs = [(o.correct, o.correct_second_judge) for o in outcomes]
    if pairs and all(b is not None for _, b in pairs):
        out["judge_agreement"] = judge_agreement([(a, bool(b)) for a, b in pairs])
        for (variant, condition), rows in by.items():
            vals = [float(bool(o.correct_second_judge)) for o in rows.values()]
            table[f"{variant}/{condition}"]["second_judge_accuracy"] = _rate(vals)
    return out


def judge_agreement(pairs: list[tuple[bool, bool]]) -> dict:
    """Raw agreement and Cohen's kappa between the primary and the second judge."""
    n = len(pairs)
    agree = sum(a == b for a, b in pairs) / n
    p_a = sum(a for a, _ in pairs) / n
    p_b = sum(b for _, b in pairs) / n
    chance = p_a * p_b + (1 - p_a) * (1 - p_b)
    kappa = (agree - chance) / (1 - chance) if chance < 1 else 1.0
    return {
        "n": n,
        "agreement": round(agree, 4),
        "cohen_kappa": round(kappa, 4),
        "primary_correct_rate": round(p_a, 4),
        "second_correct_rate": round(p_b, 4),
    }


def run(
    specs: list[BookSpec],
    results_dir: str | Path,
    out_dir: str | Path,
    client: Client,
    judge_client: Client,
    k: int = 5,
    second_judge: Client | None = None,
) -> dict:
    specs = question_books(specs)
    results_dir, out_dir = Path(results_dir), Path(out_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "model": client.model,
        "judge": judge_client.model,
        "second_judge": second_judge.model if second_judge is not None else None,
        "books": {},
    }
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
        chunks = chunk_book(job.conv.book, CHUNK_WORDS, HOLDOUT)
        extractive_refs = job.extractive.reference_by_chapter()
        corpora = [
            Corpus("book_chunks", chunks),
            Corpus("skill_chunks", chunk_markdown(extractive_refs, CHUNK_WORDS)),
            Corpus("llm_skill_chunks", chunk_markdown(refs, CHUNK_WORDS)),
            Corpus("llm_skill_files", whole_files(refs)),
        ]
        variants = {"skill": job.extractive, "llm_skill": llm_pkg}
        retrieval = {
            "index": summarise_set(evaluate(job.index_items, job.conv.book, corpora, variants)),
            "glossary": summarise_set(evaluate(job.items, job.conv.book, corpora, variants)),
        }
        index = BM25([c.text for c in chunks])
        skills = {"extractive": job.extractive, "llm": llm_pkg}
        book_outcomes: list[Outcome] = []
        for item in job.items:
            book_outcomes.extend(
                run_item(client, judge_client, item, skills, index, chunks, k, second_judge)
            )
        outcomes.extend(book_outcomes)
        report["books"][spec.key] = {
            "generation": asdict(gen),
            "llm_skill_words": sum(len(t.split()) for t in refs.values()),
            "extractive_skill_words": sum(budgets.values()),
            "llm_skill_prose_words": sum(llm_pkg.prose_budget_by_chapter().values()),
            "extractive_skill_prose_words": sum(job.extractive.prose_budget_by_chapter().values()),
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
