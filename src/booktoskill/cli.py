"""Command line: ``book-to-skill convert | inspect | search | experiments | model-arm``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pypdf.errors import PdfReadError

from booktoskill.bm25 import BM25
from booktoskill.chunking import chunk_book
from booktoskill.layout import RepairOptions
from booktoskill.llm import LLMError
from booktoskill.pipeline import Conversion, convert
from booktoskill.skill import build_extractive_skill, skill_name, write_skill
from booktoskill.structure import book_to_markdown, is_content_chapter


class UsageError(Exception):
    """A problem with the user's input, reported without a traceback."""


def _load(args: argparse.Namespace) -> Conversion:
    path = Path(args.pdf)
    if not path.is_file():
        raise UsageError(f"no such file: {path}")
    if path.suffix.lower() != ".pdf":
        raise UsageError(f"expected a .pdf file, got {path.name}")
    try:
        conv = convert(path, RepairOptions(), title=args.title)
    except PdfReadError as exc:
        raise UsageError(f"could not read {path.name} as a PDF: {exc}") from exc
    words = sum(len(b.text.split()) for b in conv.blocks)
    if words < 50:
        raise UsageError(
            f"{path.name} has almost no extractable text ({words} words). "
            "It is probably scanned; this tool does not do OCR."
        )
    return conv


def cmd_convert(args: argparse.Namespace) -> int:
    conv = _load(args)
    exclude = tuple(args.exclude_section or ())
    name = args.name or skill_name(conv.book.title)
    pkg = build_extractive_skill(conv.book, name=name, exclude=exclude)
    root = write_skill(pkg, args.out)
    if args.markdown:
        (root / "book.md").write_text(book_to_markdown(conv.book), encoding="utf-8")
    chapters = [ch for ch in conv.book.chapters if is_content_chapter(ch)]
    book_words = sum(len(b.text.split()) for ch in chapters for b in ch.blocks(exclude))
    print(f"wrote {root}")
    print(f"  SKILL.md         {len(pkg.skill_md.split()):>6} words")
    print(f"  references/      {len(pkg.references):>6} files, {pkg.words:>6} words")
    print(f"  book (chapters)  {book_words:>6} words -> {pkg.words / max(book_words, 1):.0%} kept")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    conv = _load(args)
    rep = conv.report
    print(f"title: {conv.book.title}")
    print(
        f"pages: {len(conv.pages)}   body font: {rep.body_size}pt   "
        f"heading sizes: {conv.book.heading_sizes}"
    )
    print(
        f"repairs: {rep.header_lines_removed} header/footer lines, "
        f"{rep.figure_runs_removed} figure runs removed; {rep.hyphen_joins} hyphenations "
        f"joined ({rep.hyphens_kept} kept); {rep.ligatures_expanded} ligatures; "
        f"{rep.code_blocks} code blocks; {rep.kerning_joins} kerning splits"
    )
    for ch in conv.book.chapters:
        label = f"{ch.number:>3} " if ch.number else "    "
        print(f"{label}{ch.title}  (p. {ch.page + 1}-{ch.last_page + 1})")
        if args.sections:
            for s in ch.sections:
                print(f"        {s.number} {s.title}".rstrip())
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    conv = _load(args)
    chunks = chunk_book(conv.book, args.chunk_words, tuple(args.exclude_section or ()))
    if not chunks:
        raise UsageError("no numbered chapters were detected, so there is nothing to search")
    hits = BM25([c.text for c in chunks]).search(args.query, k=args.k)
    if not hits:
        print("no matches")
        return 1
    for rank, h in enumerate(hits, 1):
        c = chunks[h.index]
        text = " ".join(c.text.split())
        print(f"{rank}. [chapter {c.chapter} / {c.section or 'intro'}] score {h.score:.2f}")
        print(f"   {text[:300]}{'...' if len(text) > 300 else ''}")
    return 0


def cmd_experiments(args: argparse.Namespace) -> int:
    from booktoskill.experiments import run_all

    summary = run_all(args.data, args.results)
    pooled = summary["pooled_retrieval"]["corpora"]
    print(f"wrote results to {args.results}")
    for name, entry in pooled.items():
        print(
            f"  {name:34s} recall@5 (term) {entry['term']['recall@5']['value']:.3f}  "
            f"evidence kept {entry['evidence_retained']['value']:.3f}"
        )
    return 0


def cmd_model_arm(args: argparse.Namespace) -> int:
    from booktoskill import model_arm
    from booktoskill.llm import list_models, ollama_client

    if args.dry_run:
        print(json.dumps(model_arm.plan(args.data), indent=2))
        return 0
    available = list_models(args.url)
    missing = [m for m in {args.model, args.judge_model} if m not in available]
    if missing:
        raise UsageError(f"ollama has not pulled {', '.join(missing)}; run `ollama pull` first")
    cache = Path(args.cache)
    client = ollama_client(cache, args.model, args.url)
    judge = ollama_client(cache, args.judge_model, args.url)
    report = model_arm.run(args.data, args.results, args.out, client, judge, k=args.k)
    print(json.dumps(report["pooled_qa"], indent=2))
    print(f"model calls: {client.calls + judge.calls} new, {client.hits + judge.hits} cached")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="book-to-skill",
        description="Turn a technical book PDF into a Claude Code skill package.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    def pdf_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("pdf", help="a born-digital PDF (not scanned)")
        sp.add_argument("--title", help="book title (default: the PDF's metadata or file name)")
        sp.add_argument(
            "--exclude-section",
            action="append",
            metavar="TITLE",
            help="leave out sections with this title, e.g. Exercises (repeatable)",
        )

    c = sub.add_parser("convert", help="write a skill package for a PDF")
    pdf_args(c)
    c.add_argument("--out", default="skills", help="output directory (default: skills)")
    c.add_argument("--name", help="skill name (default: slug of the title)")
    c.add_argument("--markdown", action="store_true", help="also write the full book as book.md")
    c.set_defaults(func=cmd_convert)

    i = sub.add_parser("inspect", help="show detected chapters and what was repaired")
    pdf_args(i)
    i.add_argument("--sections", action="store_true", help="list sections too")
    i.set_defaults(func=cmd_inspect)

    s = sub.add_parser("search", help="BM25 search over the book's chunks")
    pdf_args(s)
    s.add_argument("query")
    s.add_argument("-k", type=int, default=5, help="results to show (default 5)")
    s.add_argument("--chunk-words", type=int, default=200, help="chunk size (default 200)")
    s.set_defaults(func=cmd_search)

    e = sub.add_parser("experiments", help="rerun every no-model result in results/")
    e.add_argument("--data", default="data", help="folder holding raw/ (default: data)")
    e.add_argument("--results", default="results", help="output folder (default: results)")
    e.set_defaults(func=cmd_experiments)

    m = sub.add_parser("model-arm", help="skill generation and QA with a local model")
    m.add_argument("--data", default="data")
    m.add_argument("--results", default="results")
    m.add_argument("--out", default="out/skills", help="where generated skills are written")
    m.add_argument("--cache", default="data/cache/llm", help="generation cache folder")
    m.add_argument("--url", default="http://127.0.0.1:11434")
    m.add_argument("--model", default="qwen2.5:14b-instruct")
    m.add_argument("--judge-model", default="qwen2.5:14b-instruct")
    m.add_argument("-k", type=int, default=5, help="chunks retrieved for RAG (default 5)")
    m.add_argument("--dry-run", action="store_true", help="print the job list and call count")
    m.set_defaults(func=cmd_model_arm)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (UsageError, FileNotFoundError, LLMError) as exc:
        print(f"book-to-skill: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
