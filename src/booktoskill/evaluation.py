"""Scoring a question set against the book, the skill and their controls.

For every question this records, once: whether each corpus still contains the
gold evidence, where BM25 ranks it (by rank and by words read), whether each
skill variant's chapter file and each random same-budget control keeps it,
and whether the gold evidence matches the skill writer's definitions regex.
Any subset of questions (a split, a book, the ones outside the glossary) is
then summarised from those per-question records.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field, replace
from functools import cached_property

from booktoskill.bm25 import BM25
from booktoskill.chunking import Chunk, chunk_book, chunk_markdown, whole_files
from booktoskill.metrics import Evidence, bootstrap_ci, cluster_bootstrap_ci, gram_set
from booktoskill.pipeline import Conversion, blocks_text
from booktoskill.references import GoldItem
from booktoskill.skill import DEFINING_RE, SkillPackage, build_extractive_skill, sentences
from booktoskill.structure import Book, is_content_chapter

HOLDOUT = ("Glossary",)
KS = (1, 3, 5, 10)
WORD_BUDGETS = (250, 500, 1000, 2000)
HEADLINE_BUDGET = 1000
CHUNK_WORDS = 200
RANDOM_SEEDS = 20
RANKED = 40  # enough units to cover the largest word budget in every corpus
THRESHOLDS = (0.4, 0.6, 0.8)


@dataclass
class Corpus:
    name: str
    units: list[Chunk]

    @property
    def words(self) -> int:
        return sum(u.words for u in self.units)

    @cached_property
    def grams(self) -> list[frozenset[tuple[str, ...]]]:
        return [gram_set(u.text) for u in self.units]


# ------------------------------------------------------------ skill variants


def skill_variants(book: Book) -> dict[str, SkillPackage]:
    """The evaluated skill and its ablation without the definitions section."""
    return {
        "skill": build_extractive_skill(book, exclude=HOLDOUT),
        "skill_without_definitions": build_extractive_skill(
            book, exclude=HOLDOUT, max_definitions=0
        ),
    }


def random_budget_references(book: Book, pkg: SkillPackage, seed: int) -> dict[str, str]:
    """Control: per chapter, random sentences up to ``pkg``'s file word count.

    Same budget, no selection rule. Built against each skill variant's own
    budget: a control at a larger budget than the variant it is compared with
    would make that variant look worse than chance by construction.
    """
    rng = random.Random(seed)
    budgets = {ch: len(t.split()) for ch, t in pkg.reference_by_chapter().items()}
    out: dict[str, str] = {}
    for ch in book.chapters:
        if ch.number not in budgets:
            continue
        pool = [s for b in ch.blocks(HOLDOUT) if b.kind == "paragraph" for s in sentences(b.text)]
        order = list(range(len(pool)))
        rng.shuffle(order)
        picked: list[int] = []
        words = 0
        for i in order:
            if words >= budgets[ch.number]:
                break
            picked.append(i)
            words += len(pool[i].split())
        out[ch.number] = "\n\n".join(pool[i] for i in sorted(picked))
    return out


def build_corpora(
    conv: Conversion, raw_conv: Conversion, variants: dict[str, SkillPackage]
) -> list[Corpus]:
    """Retrieval corpora. Every chunked corpus uses the same ~200-word chunker."""
    refs = variants["skill"].reference_by_chapter()
    no_defs = variants["skill_without_definitions"].reference_by_chapter()
    return [
        Corpus("book_chunks", chunk_book(conv.book, CHUNK_WORDS, HOLDOUT)),
        Corpus("book_chunks_no_repair", chunk_book(raw_conv.book, CHUNK_WORDS, HOLDOUT)),
        Corpus("skill_chunks", chunk_markdown(refs, CHUNK_WORDS)),
        Corpus("skill_files", whole_files(refs)),
        Corpus("skill_without_definitions_chunks", chunk_markdown(no_defs, CHUNK_WORDS)),
        Corpus(
            "random_sentences_chunks",
            chunk_markdown(random_budget_references(conv.book, variants["skill"], 0), CHUNK_WORDS),
        ),
    ]


# ------------------------------------------------------------- questions


def queries(item: GoldItem) -> dict[str, str]:
    if item.kind == "index":
        return {"term": f"Where does the book explain {item.term}?"}
    return {"term": f"What is {item.term}?", "definition": item.definition}


def filter_to_pdf(items: list[GoldItem], conv: Conversion) -> tuple[list[GoldItem], int]:
    """Keep the gold sentences present in the extracted PDF text of their chapter.

    The sources (LaTeX, Asciidoc) and the published PDF are not always the same
    revision; a sentence reworded between them cannot be scored fairly. A
    question left with no gold sentence is dropped; the count is returned.
    """
    grams = {
        ch.number: gram_set(blocks_text(ch.blocks(HOLDOUT)))
        for ch in conv.book.chapters
        if is_content_chapter(ch)
    }
    kept = []
    for it in items:
        chapter = grams.get(str(it.chapter), frozenset())
        present = tuple(s for s in it.evidence_sentences if Evidence.of([s]).found(chapter))
        if not present:
            continue
        if it.evidence:
            it = replace(it, evidence=present, gold_sentence=present[0])
        kept.append(it)
    return kept, len(items) - len(kept)


def budget_hits(texts: list[str], full_hits: list[bool], gold: Evidence, budget: int) -> bool:
    """Is the gold evidence inside the first ``budget`` words of the ranked units?

    Units are read in rank order; the unit that crosses the budget is cut at
    it. This compares corpora of differently sized units at equal reading cost.
    """
    used = 0
    for text, hit in zip(texts, full_hits, strict=True):
        words = text.split()
        if used + len(words) <= budget:
            if hit:
                return True
            used += len(words)
            continue
        remaining = budget - used
        return remaining > 0 and gold.found_in(" ".join(words[:remaining]))
    return False


# ---------------------------------------------------------------- records


@dataclass
class SetRun:
    """Per-question records for one question set (one book, or pooled)."""

    items: list[GoldItem] = field(default_factory=list)
    corpora: dict[str, dict[str, int]] = field(default_factory=dict)
    best: dict[str, list[float]] = field(default_factory=dict)  # best coverage per corpus
    hits: dict[tuple[str, str], list[list[int]]] = field(default_factory=dict)
    word_hits: dict[tuple[str, str], list[dict[int, bool]]] = field(default_factory=dict)
    kept: dict[str, list[bool]] = field(default_factory=dict)  # per skill variant
    random_kept: dict[str, list[list[bool]]] = field(default_factory=dict)  # [seed][item]
    regex: list[bool] = field(default_factory=list)
    defs_section: list[bool] = field(default_factory=list)
    book_sentences: int = 0
    book_sentences_matching: int = 0

    def extend(self, other: SetRun) -> None:
        self.items += other.items
        for name, meta in other.corpora.items():
            mine = self.corpora.setdefault(name, {"units": 0, "words": 0})
            mine["units"] += meta["units"]
            mine["words"] += meta["words"]
        for attr in ("best", "hits", "word_hits", "kept"):
            mine_d, theirs = getattr(self, attr), getattr(other, attr)
            for key, rows in theirs.items():
                mine_d.setdefault(key, []).extend(rows)
        for name, seeds in other.random_kept.items():
            mine_s = self.random_kept.setdefault(name, [[] for _ in seeds])
            for mine_row, row in zip(mine_s, seeds, strict=True):
                mine_row.extend(row)
        self.regex += other.regex
        self.defs_section += other.defs_section
        self.book_sentences += other.book_sentences
        self.book_sentences_matching += other.book_sentences_matching

    def subset(self, keep: list[bool]) -> SetRun:
        def pick(rows: list) -> list:
            return [r for r, k in zip(rows, keep, strict=True) if k]

        out = SetRun(
            items=pick(self.items),
            corpora=self.corpora,
            best={k: pick(v) for k, v in self.best.items()},
            hits={k: pick(v) for k, v in self.hits.items()},
            word_hits={k: pick(v) for k, v in self.word_hits.items()},
            kept={k: pick(v) for k, v in self.kept.items()},
            random_kept={k: [pick(s) for s in v] for k, v in self.random_kept.items()},
            regex=pick(self.regex),
            defs_section=pick(self.defs_section),
            book_sentences=self.book_sentences,
            book_sentences_matching=self.book_sentences_matching,
        )
        return out


def evaluate(
    items: list[GoldItem],
    book: Book,
    corpora: list[Corpus],
    variants: dict[str, SkillPackage],
    seeds: int = RANDOM_SEEDS,
) -> SetRun:
    run = SetRun(items=list(items))
    evidence = [Evidence.of(it.evidence_sentences) for it in items]
    for corpus in corpora:
        run.corpora[corpus.name] = {"units": len(corpus.units), "words": corpus.words}
        run.best[corpus.name] = [
            max((e.coverage(g) for g in corpus.grams), default=0.0) for e in evidence
        ]
        index = BM25([u.text for u in corpus.units])
        qtypes = sorted({q for it in items for q in queries(it)})
        for qtype in qtypes:
            rows, wrows = [], []
            for it, ev in zip(items, evidence, strict=True):
                query = queries(it).get(qtype)
                if query is None:
                    continue
                ranked = index.search(query, RANKED)
                texts = [corpus.units[h.index].text for h in ranked]
                flags = [ev.found(corpus.grams[h.index]) for h in ranked]
                rows.append([int(f) for f in flags[: max(KS)]])
                wrows.append({w: budget_hits(texts, flags, ev, w) for w in WORD_BUDGETS})
            run.hits[(corpus.name, qtype)] = rows
            run.word_hits[(corpus.name, qtype)] = wrows
    for name, pkg in variants.items():
        refs = {ch: gram_set(t) for ch, t in pkg.reference_by_chapter().items()}
        run.kept[name] = [
            ev.found(refs.get(str(it.chapter), frozenset()))
            for it, ev in zip(items, evidence, strict=True)
        ]
        per_seed = []
        for seed in range(seeds):
            rnd = {ch: gram_set(t) for ch, t in random_budget_references(book, pkg, seed).items()}
            per_seed.append(
                [
                    ev.found(rnd.get(str(it.chapter), frozenset()))
                    for it, ev in zip(items, evidence, strict=True)
                ]
            )
        run.random_kept[name] = per_seed
    refs = variants["skill"].reference_by_chapter()
    for it, ev in zip(items, evidence, strict=True):
        run.regex.append(any(DEFINING_RE.search(s) for s in it.evidence_sentences))
        ref = refs.get(str(it.chapter), "")
        defs = (
            ref.split("## Key definitions")[1].split("## Worked examples")[0]
            if ("## Key definitions" in ref)
            else ""
        )
        run.defs_section.append(ev.found_in(defs))
    book_sents = [
        s
        for ch in book.chapters
        if is_content_chapter(ch)
        for b in ch.blocks(HOLDOUT)
        if b.kind == "paragraph"
        for s in sentences(b.text)
    ]
    run.book_sentences = len(book_sents)
    run.book_sentences_matching = sum(bool(DEFINING_RE.search(s)) for s in book_sents)
    return run


# --------------------------------------------------------------- summaries


def rate(values: list[float]) -> dict:
    if not values:
        return {"value": None, "ci95": None}
    lo, hi = bootstrap_ci(values)
    return {"value": round(sum(values) / len(values), 4), "ci95": [round(lo, 4), round(hi, 4)]}


def _outcomes(run: SetRun, name: str, qtype: str, metric: str) -> list[float]:
    if metric.endswith("w"):
        budget = int(metric.removeprefix("recall@").removesuffix("w"))
        return [float(r[budget]) for r in run.word_hits[(name, qtype)]]
    k = int(metric.removeprefix("recall@"))
    return [float(any(r[:k])) for r in run.hits[(name, qtype)]]


def _clusters(run: SetRun) -> list[str]:
    return [f"{it.book}/{it.chapter}" for it in run.items]


def summarise_retrieval(run: SetRun, base: str = "book_chunks") -> dict:
    metrics = [f"recall@{k}" for k in KS] + [f"recall@{w}w" for w in WORD_BUDGETS]
    qtypes = sorted({q for (_, q) in run.hits})
    out: dict = {"corpora": {}, "paired_differences": {}}
    for name, meta in run.corpora.items():
        entry: dict = dict(meta)
        entry["mean_unit_words"] = round(meta["words"] / max(meta["units"], 1), 1)
        entry["evidence_retained"] = rate([float(b >= 0.6) for b in run.best[name]])
        entry["evidence_retained_by_threshold"] = {
            str(t): sum(b >= t for b in run.best[name]) for t in THRESHOLDS
        }
        for qtype in qtypes:
            entry[qtype] = {m: rate(_outcomes(run, name, qtype, m)) for m in metrics}
        out["corpora"][name] = entry
    for name in run.corpora:
        if name == base:
            continue
        for qtype in qtypes:
            for metric in ("recall@5", f"recall@{HEADLINE_BUDGET}w"):
                a, b = _outcomes(run, base, qtype, metric), _outcomes(run, name, qtype, metric)
                out["paired_differences"][f"{name} minus {base} / {qtype} / {metric}"] = rate(
                    [y - x for x, y in zip(a, b, strict=True)]
                )
    return out


def _control(run: SetRun, name: str, keep: list[bool] | None = None) -> dict:
    """A variant's retention against random text at its own budget, on ``keep``ed items."""
    idx = [i for i in range(len(run.items)) if keep is None or keep[i]]
    if not idx:
        return {"n": 0}
    kept = [float(run.kept[name][i]) for i in idx]
    seeds = run.random_kept[name]
    seed_rates = [sum(s[i] for i in idx) / len(idx) for s in seeds]
    random_mean = [sum(s[i] for s in seeds) / len(seeds) for i in idx]
    diff = [k - r for k, r in zip(kept, random_mean, strict=True)]
    clusters = [_clusters(run)[i] for i in idx]
    lo, hi = cluster_bootstrap_ci(diff, clusters)
    return {
        "n": len(idx),
        "kept": rate(kept),
        "random_same_budget_mean": round(statistics.mean(seed_rates), 4),
        "random_same_budget_sd": round(statistics.stdev(seed_rates), 4) if len(seeds) > 1 else 0.0,
        "random_same_budget_min": round(min(seed_rates), 4),
        "random_same_budget_max": round(max(seed_rates), 4),
        "seeds": len(seeds),
        "kept_minus_random": rate(diff),
        "kept_minus_random_ci95_by_chapter": [round(lo, 4), round(hi, 4)],
        "chapters": len(set(clusters)),
    }


def summarise_controls(run: SetRun) -> dict:
    """Retention vs random for each variant, overall and split by the regex."""
    n = len(run.items)
    unmatched = [not r for r in run.regex]
    return {
        "variants": {name: _control(run, name) for name in run.kept},
        "definition_rule": {
            "gold_matching": sum(run.regex),
            "gold": n,
            "gold_match_rate": round(sum(run.regex) / n, 4) if n else None,
            "book_sentence_match_rate": round(
                run.book_sentences_matching / max(run.book_sentences, 1), 4
            ),
            "enrichment": round(
                (sum(run.regex) / n) / (run.book_sentences_matching / run.book_sentences), 1
            )
            if n and run.book_sentences_matching
            else None,
            "definitions_section_keeps": rate([float(x) for x in run.defs_section]),
            "skill_on_matching": _control(run, "skill", run.regex),
            "skill_on_not_matching": _control(run, "skill", unmatched),
        },
    }


def summarise(run: SetRun) -> dict:
    return {"n": len(run.items), **summarise_retrieval(run), "controls": summarise_controls(run)}
