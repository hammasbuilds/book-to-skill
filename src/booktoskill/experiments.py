"""The no-model experiments: extraction fidelity, structure accuracy, retrieval.

Each function returns a JSON-serialisable dict; ``run_all`` writes them to
``results/``. Inputs are the files ``scripts/fetch_data.sh`` downloads.
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path

from booktoskill.bm25 import BM25
from booktoskill.chunking import Chunk, chunk_book, chunk_markdown, whole_files
from booktoskill.layout import RepairOptions
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
from booktoskill.pdftext import Page, read_outline, read_pdf
from booktoskill.pipeline import Conversion, blocks_text, convert, plain_page_texts
from booktoskill.references import (
    ASCIIDOCTOR,
    HEVEA,
    EditionStyle,
    GoldItem,
    RefChapter,
    gold_from_latex,
    parse_html_edition,
)
from booktoskill.skill import DEFINING_RE, SkillPackage, build_extractive_skill, sentences
from booktoskill.structure import Book, is_content_chapter

HOLDOUT = ("Glossary",)
KS = (1, 3, 5, 10)
WORD_BUDGETS = (250, 500, 1000, 2000)
HEADLINE_BUDGET = 1000
CHUNK_WORDS = 200
RANDOM_SEEDS = 20


@dataclass(frozen=True)
class BookSpec:
    key: str
    title: str
    pdf: Path
    html: Path  # a folder of hevea pages, or one Asciidoctor file
    style: EditionStyle
    tex: Path | None  # LaTeX source with glossaries; None: no question set


def book_specs(data_dir: str | Path) -> list[BookSpec]:
    """Two LaTeX books with question sets, and Pro Git as a non-LaTeX control.

    Pro Git (Asciidoctor PDF on Prawn) is scored on extraction and structure
    only: it has no glossary, so no definition questions.
    """
    raw = Path(data_dir) / "raw"
    return [
        BookSpec(
            "thinkpython2",
            "Think Python 2e",
            raw / "thinkpython2.pdf",
            raw / "html" / "thinkpython2",
            HEVEA,
            raw / "thinkpython2.tex",
        ),
        BookSpec(
            "thinkstats2",
            "Think Stats 2e",
            raw / "thinkstats2.pdf",
            raw / "html" / "thinkstats2",
            HEVEA,
            raw / "thinkstats2.tex",
        ),
        BookSpec("progit", "Pro Git", raw / "progit.pdf", raw / "progit.html", ASCIIDOCTOR, None),
    ]


def check_inputs(specs: list[BookSpec]) -> None:
    paths = [p for s in specs for p in (s.pdf, s.tex, s.html) if p is not None]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "missing inputs (run scripts/fetch_data.sh first): " + ", ".join(missing)
        )


# ----------------------------------------------------------------- extraction


def chapter_page_ranges(
    outline: list[tuple[int, str, int]],
    n_pages: int,
    refs: list[RefChapter],
    index_page: int | None = None,
) -> list[tuple[RefChapter, int, int]]:
    """Pair each reference chapter with its page range from the PDF outline.

    The outline is used here only to cut both texts into comparable pieces;
    it is independent of the pipeline's own structure detection. Neither
    book's outline lists its index, so the last chapter ends at
    ``index_page`` (see :func:`find_index_page`).
    """
    top = [(title, page) for depth, title, page in outline if depth == 0]
    by_key = {title_key(r.title): r for r in refs}
    out = []
    for i, (title, start) in enumerate(top):
        end = top[i + 1][1] if i + 1 < len(top) else index_page or n_pages
        ref = by_key.get(title_key(title))
        if ref is not None and ref.numbered:  # numbered chapters and appendices only
            out.append((ref, start, end))
    return out


def find_index_page(plain_pages: list[str], after: int) -> int | None:
    """The first page after ``after`` whose plain text starts with "Index"."""
    for i in range(after + 1, len(plain_pages)):
        first = plain_pages[i].strip().split("\n", 1)[0].strip()
        if first == "Index":
            return i
    return None


def _system_texts(conv: Conversion, ranges: list[tuple[RefChapter, int, int]]) -> list[str]:
    return [blocks_text([b for b in conv.blocks if s <= b.page < e]) for _, s, e in ranges]


def extraction_experiment(spec: BookSpec, pages: list[Page]) -> dict:
    refs = parse_html_edition(spec.html, spec.style)
    plain = plain_page_texts(spec.pdf)
    outline = read_outline(spec.pdf)
    last_start = max(page for depth, _, page in outline if depth == 0)
    ranges = chapter_page_ranges(outline, len(pages), refs, find_index_page(plain, last_start))
    ref_texts = [r.text for r, _, _ in ranges]
    ref_vocab = vocabulary("\n".join(r.text for r in refs))

    systems: dict[str, list[str]] = {
        "pypdf_plain": ["\n".join(plain[s:e]) for _, s, e in ranges],
    }
    configs = {"repaired": RepairOptions()}
    for f in fields(RepairOptions):
        configs[f"without_{f.name}"] = replace(RepairOptions(), **{f.name: False})
    configs["no_repairs"] = RepairOptions(**{f.name: False for f in fields(RepairOptions)})
    for name, opts in configs.items():
        systems[name] = _system_texts(convert(spec.pdf, opts, pages=pages), ranges)

    ref_code = [b for r, _, _ in ranges for b in r.code_blocks]
    out: dict = {"chapters_compared": len(ranges), "systems": {}}
    baseline_f1: list[float] = []
    for name, texts in systems.items():
        per = [fidelity(t, r) for t, r in zip(texts, ref_texts, strict=True)]
        if name == "pypdf_plain":
            baseline_f1 = [f.f1 for f in per]
        diff = [f.f1 - b for f, b in zip(per, baseline_f1, strict=True)]
        matched_p = sum(f.precision * f.out_tokens for f in per)
        matched_r = sum(f.recall * f.ref_tokens for f in per)
        out_tokens = sum(f.out_tokens for f in per)
        ref_tokens = sum(f.ref_tokens for f in per)
        p, r = matched_p / out_tokens, matched_r / ref_tokens
        defects: dict[str, int] = {}
        for t in texts:
            for k, v in defect_counts(t, ref_vocab).items():
                defects[k] = defects.get(k, 0) + v
        out["systems"][name] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4),
            "per_chapter_f1": [round(f.f1, 4) for f in per],
            "chapter_f1_minus_pypdf_plain": _rate(diff),
            "tokens_out": out_tokens,
            "tokens_ref": ref_tokens,
            "defects": defects,
            "code_blocks": code_block_recovery("\n\n".join(texts), ref_code),
        }
    return out


# ------------------------------------------------------------------ structure


def _structure_scores(chapters: list[tuple[str, list[str]]], refs: list[RefChapter]) -> dict:
    gold_ch = [title_key(r.title) for r in refs if r.numbered]
    gold_sec = [title_key(s.title) for r in refs if r.numbered for s in r.sections]
    pred_ch = [title_key(t) for t, _ in chapters]
    pred_sec = [title_key(s) for _, secs in chapters for s in secs]
    parent_ok = parent_n = 0
    gold_parent = {
        (title_key(r.title), title_key(s.title)) for r in refs if r.numbered for s in r.sections
    }
    gold_titles = {k for _, k in gold_parent}
    for t, secs in chapters:
        for s in secs:
            if title_key(s) in gold_titles:
                parent_n += 1
                parent_ok += (title_key(t), title_key(s)) in gold_parent
    return {
        "chapters": asdict(prf(pred_ch, gold_ch)),
        "sections": asdict(prf(pred_sec, gold_sec)),
        "section_parent_accuracy": round(parent_ok / parent_n, 4) if parent_n else 0.0,
    }


def structure_experiment(spec: BookSpec, conv: Conversion, raw_conv: Conversion) -> dict:
    refs = parse_html_edition(spec.html, spec.style)

    def detected(book: Book) -> list[tuple[str, list[str]]]:
        return [
            (ch.title, [s.title for s in ch.sections])
            for ch in book.chapters
            if is_content_chapter(ch)
        ]

    outline = read_outline(spec.pdf)
    from_outline: list[tuple[str, list[str]]] = []
    for depth, title, _ in outline:
        if depth == 0:
            from_outline.append((title, []))
        elif depth == 1 and from_outline:
            from_outline[-1][1].append(title)
    ref_keys = {title_key(r.title) for r in refs if r.numbered}
    # The outline also lists front and back matter; keep what a numbered
    # chapter could be, so both methods are scored on the same footing.
    from_outline = [c for c in from_outline if title_key(c[0]) in ref_keys or c[1]]
    return {
        "reference_chapters": sum(1 for r in refs if r.numbered),
        "reference_sections": sum(len(r.sections) for r in refs if r.numbered),
        "font_size_detector": _structure_scores(detected(conv.book), refs),
        "font_size_detector_without_repairs": _structure_scores(detected(raw_conv.book), refs),
        "pdf_outline": _structure_scores(from_outline, refs),
        "heading_sizes": conv.book.heading_sizes,
    }


# ------------------------------------------------------------------ retrieval


@dataclass
class Corpus:
    name: str
    units: list[Chunk]

    @property
    def words(self) -> int:
        return sum(u.words for u in self.units)


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


def skill_variants(book: Book) -> dict[str, SkillPackage]:
    """The evaluated skill and its ablation without the definitions section."""
    return {
        "skill": build_extractive_skill(book, exclude=HOLDOUT),
        "skill_without_definitions": build_extractive_skill(
            book, exclude=HOLDOUT, max_definitions=0
        ),
    }


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


def random_control_retention(
    items: list[GoldItem], book: Book, pkg: SkillPackage, seeds: int = RANDOM_SEEDS
) -> list[int]:
    """Questions whose gold sentence the random control keeps, one count per seed."""
    out = []
    for seed in range(seeds):
        refs = random_budget_references(book, pkg, seed)
        out.append(
            sum(contains_evidence(refs.get(str(it.chapter), ""), it.gold_sentence) for it in items)
        )
    return out


def queries(item: GoldItem) -> dict[str, str]:
    return {"term": f"What is {item.term}?", "definition": item.definition}


def budget_hits(texts: list[str], full_hits: list[bool], gold: str, budget: int) -> bool:
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
        return remaining > 0 and contains_evidence(" ".join(words[:remaining]), gold)
    return False


@dataclass
class RetrievalRun:
    """Per-question outcomes for every corpus, before summarising.

    ``hits[(corpus, query_type)][i]`` holds, for question ``i``, a 0/1 flag per
    retrieved rank saying whether that unit contains the gold evidence;
    ``word_hits`` the same question at each word budget in ``WORD_BUDGETS``.
    """

    corpora: dict[str, dict[str, int]]
    present: dict[str, list[bool]]
    hits: dict[tuple[str, str], list[list[int]]]
    word_hits: dict[tuple[str, str], list[dict[int, bool]]] = field(default_factory=dict)

    def extend(self, other: RetrievalRun) -> None:
        for name, meta in other.corpora.items():
            mine = self.corpora.setdefault(name, {"units": 0, "words": 0})
            mine["units"] += meta["units"]
            mine["words"] += meta["words"]
        for name, flags in other.present.items():
            self.present.setdefault(name, []).extend(flags)
        for key, rows in other.hits.items():
            self.hits.setdefault(key, []).extend(rows)
        for key, wrows in other.word_hits.items():
            self.word_hits.setdefault(key, []).extend(wrows)


def run_retrieval(items: list[GoldItem], corpora: list[Corpus]) -> RetrievalRun:
    run = RetrievalRun({}, {}, {})
    for corpus in corpora:
        index = BM25([u.text for u in corpus.units])
        run.corpora[corpus.name] = {"units": len(corpus.units), "words": corpus.words}
        # Evidence retention: is the gold sentence anywhere in the corpus?
        run.present[corpus.name] = [
            any(contains_evidence(u.text, it.gold_sentence) for u in corpus.units) for it in items
        ]
        for qtype in ("term", "definition"):
            rows, wrows = [], []
            for it in items:
                ranked = [corpus.units[h.index].text for h in index.search(queries(it)[qtype], 100)]
                flags = [contains_evidence(t, it.gold_sentence) for t in ranked]
                rows.append([int(f) for f in flags[: max(KS)]])
                wrows.append(
                    {w: budget_hits(ranked, flags, it.gold_sentence, w) for w in WORD_BUDGETS}
                )
            run.hits[(corpus.name, qtype)] = rows
            run.word_hits[(corpus.name, qtype)] = wrows
    return run


def _rate(values: list[float]) -> dict:
    lo, hi = bootstrap_ci(values)
    return {"value": round(sum(values) / len(values), 4), "ci95": [round(lo, 4), round(hi, 4)]}


def _outcomes(run: RetrievalRun, name: str, qtype: str, metric: str) -> list[float]:
    if metric.endswith("w"):
        budget = int(metric.removeprefix("recall@").removesuffix("w"))
        return [float(r[budget]) for r in run.word_hits[(name, qtype)]]
    k = int(metric.removeprefix("recall@"))
    return [float(any(r[:k])) for r in run.hits[(name, qtype)]]


def summarise_retrieval(run: RetrievalRun, base: str = "book_chunks") -> dict:
    n = len(next(iter(run.present.values())))
    metrics = [f"recall@{k}" for k in KS] + [f"recall@{w}w" for w in WORD_BUDGETS]
    out: dict = {"n_questions": n, "corpora": {}}
    for name, meta in run.corpora.items():
        entry: dict = dict(meta)
        entry["mean_unit_words"] = round(meta["words"] / max(meta["units"], 1), 1)
        entry["evidence_retained"] = _rate([float(p) for p in run.present[name]])
        for qtype in ("term", "definition"):
            entry[qtype] = {m: _rate(_outcomes(run, name, qtype, m)) for m in metrics}
        out["corpora"][name] = entry
    diffs: dict = {}
    for name in run.corpora:
        if name == base:
            continue
        for qtype in ("term", "definition"):
            for metric in ("recall@5", f"recall@{HEADLINE_BUDGET}w"):
                a = _outcomes(run, base, qtype, metric)
                b = _outcomes(run, name, qtype, metric)
                diffs[f"{name} minus {base} / {qtype} / {metric}"] = _rate(
                    [y - x for x, y in zip(a, b, strict=True)]
                )
    out["paired_differences"] = diffs
    return out


def definition_rule_overlap(
    items: list[GoldItem], book: Book, variants: dict[str, SkillPackage]
) -> dict[str, int]:
    """How far the skill's defining-sentence regex overlaps the gold rule.

    Gold sentences are the ones holding an author-bolded term, and authors
    bold a term where they define it, so a regex for defining phrases selects
    gold sentences far more often than book sentences in general. Retention
    is split by whether the gold sentence matches the regex, and the
    definitions section is scored on its own.
    """
    book_sentences = [
        s
        for ch in book.chapters
        if is_content_chapter(ch)
        for b in ch.blocks(HOLDOUT)
        if b.kind == "paragraph"
        for s in sentences(b.text)
    ]
    refs = variants["skill"].reference_by_chapter()
    out = {
        "book_sentences": len(book_sentences),
        "book_sentences_matching": sum(bool(DEFINING_RE.search(s)) for s in book_sentences),
        "gold": len(items),
        "gold_matching": 0,
        "kept_by_skill_matching": 0,
        "kept_by_skill_not_matching": 0,
        "kept_by_definitions_section": 0,
    }
    for it in items:
        ref = refs.get(str(it.chapter), "")
        matches = bool(DEFINING_RE.search(it.gold_sentence))
        kept = contains_evidence(ref, it.gold_sentence)
        defs = (
            ref.split("## Key definitions")[1].split("## Worked examples")[0]
            if ("## Key definitions" in ref)
            else ""
        )
        out["gold_matching"] += matches
        out["kept_by_skill_matching"] += kept and matches
        out["kept_by_skill_not_matching"] += kept and not matches
        out["kept_by_definitions_section"] += contains_evidence(defs, it.gold_sentence)
    return out


# ------------------------------------------------------------------ run all


def load_gold(spec: BookSpec) -> tuple[list[GoldItem], dict[str, int]]:
    if spec.tex is None:
        raise ValueError(f"{spec.key} has no LaTeX source, so no question set")
    return gold_from_latex(spec.tex.read_text(encoding="utf-8"), spec.key)


def filter_to_pdf(items: list[GoldItem], conv: Conversion) -> tuple[list[GoldItem], int]:
    """Keep questions whose gold sentence is present in the extracted PDF text.

    The LaTeX on GitHub and the published PDF are not the same revision; an
    item whose sentence was reworded between them cannot be scored fairly.
    """
    text_by_chapter: dict[str, str] = {
        ch.number: blocks_text(ch.blocks(HOLDOUT)) for ch in conv.book.chapters
    }
    kept = [
        it
        for it in items
        if contains_evidence(text_by_chapter.get(str(it.chapter), ""), it.gold_sentence)
    ]
    return kept, len(items) - len(kept)


def retention_by_threshold(
    items: list[GoldItem], corpora: list[Corpus], thresholds: tuple[float, ...] = (0.4, 0.6, 0.8)
) -> dict[str, dict[str, int]]:
    """How many gold sentences each corpus keeps, at several match thresholds.

    The headline uses 0.6 of the sentence's word trigrams; this shows the
    comparison between corpora does not hinge on that choice.
    """
    out: dict[str, dict[str, int]] = {}
    for corpus in corpora:
        best = [
            max((evidence_coverage(u.text, it.gold_sentence) for u in corpus.units), default=0.0)
            for it in items
        ]
        out[corpus.name] = {f">={t}": sum(b >= t for b in best) for t in thresholds}
        out[corpus.name]["n"] = len(items)
    return out


def code_retention(book: Book, pkg: SkillPackage) -> dict[str, int]:
    """Multi-line code blocks of the book that appear verbatim in the skill."""
    refs = pkg.reference_by_chapter()
    total = kept = 0
    for ch in book.chapters:
        if ch.number not in refs:
            continue
        for b in ch.blocks(HOLDOUT):
            if b.kind == "code" and "\n" in b.text:
                total += 1
                kept += b.text in refs[ch.number]
    return {"book_code_blocks": total, "in_skill": kept}


def _skill_stats(conv: Conversion, pkg: SkillPackage) -> dict[str, int]:
    return {
        "reference_words": sum(len(t.split()) for t in pkg.references.values()),
        "skill_md_words": len(pkg.skill_md.split()),
        "book_words": sum(
            len(blocks_text(ch.blocks(HOLDOUT)).split())
            for ch in conv.book.chapters
            if is_content_chapter(ch)
        ),
        **code_retention(conv.book, pkg),
    }


def run_book(spec: BookSpec) -> dict:
    """Every no-model result for one book.

    Keys: extraction, structure, repair_report, skill; and for a book with a
    question set also gold, retrieval, controls, definition_rule, and the
    unsummarised ``_items``, ``_run`` and ``_threshold_counts`` for pooling.
    """
    pages = read_pdf(spec.pdf)
    conv = convert(spec.pdf, title=spec.title, pages=pages)
    raw_opts = RepairOptions(**{f.name: False for f in fields(RepairOptions)})
    raw_conv = convert(spec.pdf, raw_opts, title=spec.title, pages=pages)
    variants = skill_variants(conv.book)
    summary: dict = {
        "extraction": extraction_experiment(spec, pages),
        "structure": structure_experiment(spec, conv, raw_conv),
        "repair_report": {k: v for k, v in asdict(conv.report).items() if k != "removed_examples"},
        "skill": _skill_stats(conv, variants["skill"]),
    }
    if spec.tex is None:
        return summary
    items, gold_stats = load_gold(spec)
    items, dropped = filter_to_pdf(items, conv)
    gold_stats["not_in_pdf_revision"] = dropped
    gold_stats["questions"] = len(items)
    corpora = build_corpora(conv, raw_conv, variants)
    run = run_retrieval(items, corpora)
    summary["gold"] = gold_stats
    summary["retrieval"] = summarise_retrieval(run)
    summary["controls"] = {
        name: {
            "kept": sum(
                contains_evidence(
                    pkg.reference_by_chapter().get(str(it.chapter), ""), it.gold_sentence
                )
                for it in items
            ),
            "words": sum(len(t.split()) for t in pkg.reference_by_chapter().values()),
            "random_same_budget_kept_by_seed": random_control_retention(items, conv.book, pkg),
        }
        for name, pkg in variants.items()
    }
    rule = definition_rule_overlap(items, conv.book, variants)
    unmatched = [it for it in items if not DEFINING_RE.search(it.gold_sentence)]
    rule["random_kept_not_matching_by_seed"] = random_control_retention(
        unmatched, conv.book, variants["skill"]
    )
    summary["definition_rule"] = rule
    summary["_items"] = items
    summary["_run"] = run
    summary["_threshold_counts"] = retention_by_threshold(items, corpora)
    return summary


def _add_counts(total: dict, part: dict) -> None:
    """Sum nested dicts of ints and lists of ints (per-seed counts add elementwise)."""
    for key, value in part.items():
        if isinstance(value, dict):
            _add_counts(total.setdefault(key, {}), value)
        elif isinstance(value, list):
            mine = total.setdefault(key, [0] * len(value))
            total[key] = [x + y for x, y in zip(mine, value, strict=True)]
        else:
            total[key] = total.get(key, 0) + value


def describe_controls(controls: dict, n: int) -> dict:
    """Retention of each skill variant vs random sentences at its own budget."""
    out = {}
    for name, c in controls.items():
        rates = [k / n for k in c["random_same_budget_kept_by_seed"]]
        out[name] = {
            "words": c["words"],
            "kept": round(c["kept"] / n, 4),
            "random_same_budget_mean": round(statistics.mean(rates), 4),
            "random_same_budget_sd": round(statistics.stdev(rates), 4),
            "random_same_budget_min": round(min(rates), 4),
            "random_same_budget_max": round(max(rates), 4),
            "seeds": len(rates),
        }
    return out


def describe_definition_rule(d: dict) -> dict:
    m, g = d["gold_matching"], d["gold"]
    random_rates = [k / max(g - m, 1) for k in d["random_kept_not_matching_by_seed"]]
    return {
        **d,
        "random_same_budget_keeps_not_matching_mean": round(statistics.mean(random_rates), 4),
        "random_same_budget_keeps_not_matching_sd": round(statistics.stdev(random_rates), 4),
        "gold_match_rate": round(m / g, 4),
        "book_sentence_match_rate": round(d["book_sentences_matching"] / d["book_sentences"], 4),
        "enrichment": round((m / g) / (d["book_sentences_matching"] / d["book_sentences"]), 1),
        "skill_keeps_matching": round(d["kept_by_skill_matching"] / max(m, 1), 4),
        "skill_keeps_not_matching": round(d["kept_by_skill_not_matching"] / max(g - m, 1), 4),
        "definitions_section_keeps": round(d["kept_by_definitions_section"] / g, 4),
    }


NOTICE = (
    "questions.jsonl holds glossary definitions and sentences quoted from Think Python 2e "
    "and Think Stats 2e by Allen B. Downey (Green Tea Press), licensed CC BY-NC 3.0 "
    "(https://creativecommons.org/licenses/by-nc/3.0/). They are shared here, "
    "non-commercially and with this attribution, as the answer key for the evaluation.\n"
)


def run_all(data_dir: str | Path, results_dir: str | Path) -> dict:
    """Run every no-model experiment and write ``results/*.json``."""
    specs = book_specs(data_dir)
    check_inputs(specs)
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    pooled = RetrievalRun({}, {}, {})
    all_items: list[GoldItem] = []
    sensitivity: dict = {}
    controls: dict = {}
    rule: dict = {}
    for spec in specs:
        print(f"[{spec.key}] extraction, structure, retrieval ...", file=sys.stderr, flush=True)
        book = run_book(spec)
        if "_run" in book:
            all_items.extend(book.pop("_items"))
            pooled.extend(book.pop("_run"))
            _add_counts(sensitivity, book.pop("_threshold_counts"))
            _add_counts(controls, book["controls"])
            _add_counts(rule, book["definition_rule"])
            n = book["gold"]["questions"]
            book["controls"] = describe_controls(book["controls"], n)
            book["definition_rule"] = describe_definition_rule(book["definition_rule"])
        summary[spec.key] = book

    def write(name: str, payload: object) -> None:
        (results_dir / name).write_text(
            json.dumps(payload, indent=2), encoding="utf-8", newline="\n"
        )

    with (results_dir / "questions.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for it in all_items:
            fh.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")
    (results_dir / "NOTICE").write_text(NOTICE, encoding="utf-8", newline="\n")
    for name in ("extraction", "structure"):
        write(f"{name}.json", {k: v[name] for k, v in summary.items()})
    write("retrieval.json", {k: v["retrieval"] for k, v in summary.items() if "retrieval" in v})
    pooled_summary = summarise_retrieval(pooled)
    pooled_summary["evidence_threshold_sensitivity"] = sensitivity
    pooled_summary["controls"] = describe_controls(controls, len(all_items))
    pooled_summary["definition_rule"] = describe_definition_rule(rule)
    write("retrieval_pooled.json", pooled_summary)
    keys = ("repair_report", "gold", "skill", "controls", "definition_rule")
    write("books.json", {k: {key: v[key] for key in keys if key in v} for k, v in summary.items()})
    summary["pooled_retrieval"] = pooled_summary
    return summary
