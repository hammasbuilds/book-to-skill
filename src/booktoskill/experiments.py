"""The no-model experiments: extraction fidelity, structure accuracy, retrieval.

Each function returns a JSON-serialisable dict; ``run_all`` writes them to
``results/``. Inputs are the files ``scripts/fetch_data.sh`` downloads.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path

from booktoskill.evaluation import (
    HOLDOUT,
    SetRun,
    build_corpora,
    evaluate,
    filter_to_pdf,
    rate,
    skill_variants,
    summarise,
)
from booktoskill.index_questions import asciidoc_anchors, items_from_anchors, latex_anchors
from booktoskill.layout import RepairOptions
from booktoskill.metrics import (
    code_block_recovery,
    defect_counts,
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
from booktoskill.skill import SkillPackage
from booktoskill.structure import Book, is_content_chapter


@dataclass(frozen=True)
class BookSpec:
    key: str
    title: str
    pdf: Path
    html: Path  # a folder of hevea pages, or one Asciidoctor file
    style: EditionStyle
    tex: Path | None  # LaTeX source with glossaries; None: no glossary question set
    asciidoc: Path | None = None  # top-level .asc file, for books without LaTeX

    @property
    def has_index(self) -> bool:
        return self.tex is not None or self.asciidoc is not None


def book_specs(data_dir: str | Path) -> list[BookSpec]:
    """Two LaTeX books and Pro Git (Asciidoctor PDF on Prawn).

    All three have an index question set (LaTeX ``\\index``, Asciidoc
    ``(((term)))``); only the two LaTeX books have glossaries.
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
        BookSpec(
            "progit",
            "Pro Git",
            raw / "progit.pdf",
            raw / "progit.html",
            ASCIIDOCTOR,
            None,
            raw / "progit-src" / "progit.asc",
        ),
    ]


def check_inputs(specs: list[BookSpec]) -> None:
    paths = [p for s in specs for p in (s.pdf, s.tex, s.html, s.asciidoc) if p is not None]
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
            "chapter_f1_minus_pypdf_plain": rate(diff),
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


# -------------------------------------------------------------- questions


def load_gold(spec: BookSpec) -> tuple[list[GoldItem], dict[str, int]]:
    """The glossary question set (secondary)."""
    if spec.tex is None:
        raise ValueError(f"{spec.key} has no LaTeX source, so no glossary question set")
    return gold_from_latex(spec.tex.read_text(encoding="utf-8"), spec.key)


def glossary_terms(spec: BookSpec) -> set[str]:
    """Every glossary term of the book, lowercased, for flagging index questions.

    Taken before the PDF-revision filter: a term belongs to the glossary even if
    its bold sentence was reworded in the PDF. Shared by ``run_book`` and the
    model arm so both flag the same index questions.
    """
    return {it.term.lower() for it in load_gold(spec)[0]} if spec.tex is not None else set()


def asciidoc_chapter_files(top: Path) -> list[tuple[str, Path]]:
    """Numbered chapters (``chNN-*.asc``) and appendices (``X-*.asc``) of a book."""
    out = []
    for inc in re.findall(r"^include::([^\[]+)\[\]", top.read_text(encoding="utf-8"), re.M):
        name = Path(inc).name
        m = re.match(r"ch(\d+)-", name) or re.match(r"([A-Z])-", name)
        if m:
            number = str(int(m.group(1))) if m.group(1).isdigit() else m.group(1)
            out.append((number, top.parent / inc))
    return out


def load_index(spec: BookSpec, glossary_terms: set[str]) -> list[GoldItem]:
    """The index question set (primary)."""
    if spec.tex is not None:
        anchors = latex_anchors(spec.tex.read_text(encoding="utf-8"), HOLDOUT)
    elif spec.asciidoc is not None:
        anchors = asciidoc_anchors(asciidoc_chapter_files(spec.asciidoc), spec.asciidoc.parent)
    else:
        return []
    return items_from_anchors(anchors, spec.key, glossary_terms)


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
        "reference_prose_words": sum(pkg.prose_budget_by_chapter().values()),
        "skill_md_words": len(pkg.skill_md.split()),
        "book_words": sum(
            len(blocks_text(ch.blocks(HOLDOUT)).split())
            for ch in conv.book.chapters
            if is_content_chapter(ch)
        ),
        **code_retention(conv.book, pkg),
    }


def run_book(spec: BookSpec) -> tuple[dict, dict[str, SetRun]]:
    """Every no-model result for one book, and its per-question records by set."""
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
        "questions": {},
    }
    corpora = build_corpora(conv, raw_conv, variants)
    runs: dict[str, SetRun] = {}
    glossary: list[GoldItem] = []
    if spec.tex is not None:
        glossary, stats = load_gold(spec)
        glossary, dropped = filter_to_pdf(glossary, conv)
        summary["questions"]["glossary"] = {
            **stats,
            "not_in_pdf_revision": dropped,
            "questions": len(glossary),
        }
        runs["glossary"] = evaluate(glossary, conv.book, corpora, variants)
    if spec.has_index:
        index_items = load_index(spec, glossary_terms(spec))
        kept, dropped = filter_to_pdf(index_items, conv)
        summary["questions"]["index"] = {
            "terms_with_anchors": len(index_items),
            "not_in_pdf_revision": dropped,
            "questions": len(kept),
            "test": sum(it.split == "test" for it in kept),
            "also_glossary_terms": sum(it.in_glossary for it in kept),
        }
        runs["index"] = evaluate(kept, conv.book, corpora, variants)
    return summary, runs


def subsets(run: SetRun) -> dict[str, list[bool]]:
    """The views every set is summarised under."""
    items = run.items
    views = {"all": [True] * len(items)}
    if any(it.kind == "index" for it in items):
        views["dev"] = [it.split == "dev" for it in items]
        views["test"] = [it.split == "test" for it in items]
        views["not_glossary_terms"] = [not it.in_glossary for it in items]
        views["test_not_glossary_terms"] = [
            it.split == "test" and not it.in_glossary for it in items
        ]
    return views


NOTICE = (
    "questions_glossary.jsonl and questions_index.jsonl hold glossary definitions and sentences "
    "quoted from Think Python 2e and Think Stats 2e by Allen B. Downey (Green Tea Press), "
    "licensed CC BY-NC 3.0 (https://creativecommons.org/licenses/by-nc/3.0/), and from Pro Git "
    "by Scott Chacon and Ben Straub, licensed CC BY-NC-SA 3.0 "
    "(https://creativecommons.org/licenses/by-nc-sa/3.0/). They are shared here, "
    "non-commercially and with this attribution, as the answer key for the evaluation.\n"
)


def run_all(data_dir: str | Path, results_dir: str | Path) -> dict:
    """Run every no-model experiment and write ``results/``."""
    specs = book_specs(data_dir)
    check_inputs(specs)
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    pooled: dict[str, SetRun] = {}
    per_book: dict[str, dict[str, SetRun]] = {}
    for spec in specs:
        print(f"[{spec.key}] extraction, structure, questions ...", file=sys.stderr, flush=True)
        book, runs = run_book(spec)
        summary[spec.key] = book
        per_book[spec.key] = runs
        for name, run in runs.items():
            pooled.setdefault(name, SetRun()).extend(run)

    def write(name: str, payload: object) -> None:
        (results_dir / name).write_text(
            json.dumps(payload, indent=2), encoding="utf-8", newline="\n"
        )

    for name, run in pooled.items():
        with (results_dir / f"questions_{name}.jsonl").open(
            "w", encoding="utf-8", newline="\n"
        ) as fh:
            for it in run.items:
                fh.write(json.dumps(asdict(it), ensure_ascii=False) + "\n")
        write(
            f"{name}_eval.json",
            {
                "pooled": {view: summarise(run.subset(k)) for view, k in subsets(run).items()},
                "books": {
                    key: {view: summarise(r.subset(k)) for view, k in subsets(r).items()}
                    for key, runs in per_book.items()
                    if (r := runs.get(name)) is not None
                },
            },
        )
    (results_dir / "NOTICE").write_text(NOTICE, encoding="utf-8", newline="\n")
    for name in ("extraction", "structure"):
        write(f"{name}.json", {k: v[name] for k, v in summary.items()})
    keys = ("repair_report", "skill", "questions")
    write("books.json", {k: {key: v[key] for key in keys} for k, v in summary.items()})
    return {"books": summary, "pooled": {k: summarise(v) for k, v in pooled.items()}}
