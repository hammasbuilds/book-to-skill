"""The no-model experiments: extraction fidelity, structure accuracy, retrieval.

Each function returns a JSON-serialisable dict; ``run_all`` writes them to
``results/``. Inputs are the files ``scripts/fetch_data.sh`` downloads.
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import asdict, dataclass, fields, replace
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
from booktoskill.skill import SkillPackage, build_extractive_skill, sentences
from booktoskill.structure import Book, is_content_chapter

HOLDOUT = ("Glossary",)
KS = (1, 3, 5, 10)


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
    """Control: per chapter, random sentences up to the skill file's word count.

    Same budget, no selection rule. If the extractive writer keeps more gold
    evidence than this, its rules are doing something beyond compressing.
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


def build_corpora(conv: Conversion, raw_conv: Conversion, pkg: SkillPackage) -> list[Corpus]:
    refs = pkg.reference_by_chapter()
    no_defs = build_extractive_skill(conv.book, exclude=HOLDOUT, max_definitions=0)
    random_refs = random_budget_references(conv.book, pkg, seed=0)

    return [
        Corpus("book_chunks", chunk_book(conv.book, 200, HOLDOUT)),
        Corpus("book_chunks_no_repair", chunk_book(raw_conv.book, 200, HOLDOUT)),
        Corpus("skill_reference_chunks", chunk_markdown(refs, 200)),
        Corpus("skill_reference_files", whole_files(refs)),
        Corpus("skill_without_definitions_files", whole_files(no_defs.reference_by_chapter())),
        Corpus("random_same_budget_files", whole_files(random_refs)),
    ]


def random_control_retention(
    items: list[GoldItem], book: Book, pkg: SkillPackage, seeds: int = 5
) -> list[float]:
    """Evidence retention of the random-sentence control over several seeds."""
    out = []
    for seed in range(seeds):
        refs = random_budget_references(book, pkg, seed)
        hits = [contains_evidence(refs.get(str(it.chapter), ""), it.gold_sentence) for it in items]
        out.append(round(sum(hits) / len(items), 4))
    return out


def queries(item: GoldItem) -> dict[str, str]:
    return {"term": f"What is {item.term}?", "definition": item.definition}


@dataclass
class RetrievalRun:
    """Per-question outcomes for every corpus, before summarising.

    ``hits[(corpus, query_type)][i]`` holds, for question ``i``, a 0/1 flag per
    retrieved rank saying whether that unit contains the gold evidence.
    """

    corpora: dict[str, dict[str, int]]
    present: dict[str, list[bool]]
    hits: dict[tuple[str, str], list[list[int]]]

    def extend(self, other: RetrievalRun) -> None:
        for name, meta in other.corpora.items():
            mine = self.corpora.setdefault(name, {"units": 0, "words": 0})
            mine["units"] += meta["units"]
            mine["words"] += meta["words"]
        for name, flags in other.present.items():
            self.present.setdefault(name, []).extend(flags)
        for key, rows in other.hits.items():
            self.hits.setdefault(key, []).extend(rows)


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
            rows = []
            for it in items:
                hits = index.search(queries(it)[qtype], k=max(KS))
                rows.append(
                    [
                        int(contains_evidence(corpus.units[h.index].text, it.gold_sentence))
                        for h in hits
                    ]
                )
            run.hits[(corpus.name, qtype)] = rows
    return run


def _rate(values: list[float]) -> dict:
    lo, hi = bootstrap_ci(values)
    return {"value": round(sum(values) / len(values), 4), "ci95": [round(lo, 4), round(hi, 4)]}


def summarise_retrieval(run: RetrievalRun, base: str = "book_chunks") -> dict:
    n = len(next(iter(run.present.values())))
    out: dict = {"n_questions": n, "corpora": {}}
    for name, meta in run.corpora.items():
        entry: dict = dict(meta)
        entry["evidence_retained"] = _rate([float(p) for p in run.present[name]])
        for qtype in ("term", "definition"):
            rows = run.hits[(name, qtype)]
            entry[qtype] = {f"recall@{k}": _rate([float(any(r[:k])) for r in rows]) for k in KS}
        out["corpora"][name] = entry
    diffs: dict = {}
    for name in run.corpora:
        if name == base:
            continue
        for qtype in ("term", "definition"):
            for k in (1, 5):
                a = [float(any(r[:k])) for r in run.hits[(base, qtype)]]
                b = [float(any(r[:k])) for r in run.hits[(name, qtype)]]
                diffs[f"{name} minus {base} / {qtype} / recall@{k}"] = _rate(
                    [y - x for x, y in zip(a, b, strict=True)]
                )
    out["paired_differences"] = diffs
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


def run_book(spec: BookSpec) -> tuple[dict, list[GoldItem], RetrievalRun | None, dict]:
    """Every no-model result for one book.

    Returns the book's summary, its questions, its per-question retrieval
    outcomes (None for a book without a question set) and the evidence
    threshold counts.
    """
    pages = read_pdf(spec.pdf)
    conv = convert(spec.pdf, title=spec.title, pages=pages)
    raw_opts = RepairOptions(**{f.name: False for f in fields(RepairOptions)})
    raw_conv = convert(spec.pdf, raw_opts, title=spec.title, pages=pages)
    pkg = build_extractive_skill(conv.book, exclude=HOLDOUT)
    summary: dict = {
        "extraction": extraction_experiment(spec, pages),
        "structure": structure_experiment(spec, conv, raw_conv),
        "repair_report": {k: v for k, v in asdict(conv.report).items() if k != "removed_examples"},
        "skill": _skill_stats(conv, pkg),
    }
    if spec.tex is None:
        return summary, [], None, {}
    items, gold_stats = load_gold(spec)
    items, dropped = filter_to_pdf(items, conv)
    gold_stats["not_in_pdf_revision"] = dropped
    gold_stats["questions"] = len(items)
    corpora = build_corpora(conv, raw_conv, pkg)
    run = run_retrieval(items, corpora)
    summary["gold"] = gold_stats
    summary["retrieval"] = summarise_retrieval(run)
    summary["random_control_retention_by_seed"] = random_control_retention(items, conv.book, pkg)
    return summary, items, run, retention_by_threshold(items, corpora)


def run_all(data_dir: str | Path, results_dir: str | Path) -> dict:
    """Run every no-model experiment and write ``results/*.json``."""
    specs = book_specs(data_dir)
    check_inputs(specs)
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    pooled = RetrievalRun({}, {}, {})
    all_items: list[GoldItem] = []
    sensitivity: dict[str, dict[str, int]] = {}
    for spec in specs:
        print(f"[{spec.key}] extraction, structure, retrieval ...", file=sys.stderr, flush=True)
        book, items, run, counts = run_book(spec)
        summary[spec.key] = book
        all_items.extend(items)
        if run is not None:
            pooled.extend(run)
        for name, row in counts.items():
            mine = sensitivity.setdefault(name, dict.fromkeys(row, 0))
            for key, value in row.items():
                mine[key] += value

    def write(name: str, payload: object) -> None:
        (results_dir / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with (results_dir / "questions.jsonl").open("w", encoding="utf-8") as fh:
        for it in all_items:
            fh.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")
    for name in ("extraction", "structure"):
        write(f"{name}.json", {k: v[name] for k, v in summary.items()})
    write("retrieval.json", {k: v["retrieval"] for k, v in summary.items() if "retrieval" in v})
    pooled_summary = summarise_retrieval(pooled)
    pooled_summary["evidence_threshold_sensitivity"] = sensitivity
    write("retrieval_pooled.json", pooled_summary)
    keys = ("repair_report", "gold", "skill", "random_control_retention_by_seed")
    write("books.json", {k: {key: v[key] for key in keys if key in v} for k, v in summary.items()})
    summary["pooled_retrieval"] = pooled_summary
    return summary
