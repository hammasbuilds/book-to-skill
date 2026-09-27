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
from booktoskill.structure import book_to_markdown, content_coverage, is_content_chapter

# Below this share of the book's words inside numbered chapters, the structure
# detector has almost certainly misread the book (a title page taken for the
# only chapter), and a skill built from it would silently drop the book.
MIN_COVERAGE = 0.2


class UsageError(Exception):
    """A problem with the user's input, reported without a traceback."""


def _positive(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def _load(args: argparse.Namespace) -> Conversion:
    path = Path(args.pdf)
    if path.is_dir():
        raise UsageError(f"{path} is a directory; give the path of one PDF file")
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
    coverage = content_coverage(conv.book)
    if coverage < MIN_COVERAGE and not args.allow_low_coverage:
        raise LowCoverage(
            f"only {coverage:.0%} of the book's text is inside the chapters that were "
            "detected, so the skill would leave most of the book out. Run "
            "`book-to-skill inspect --sections` to see what was found, or pass "
            "--allow-low-coverage to write it anyway."
        )
    name = args.name or skill_name(conv.book.title)
    try:
        pkg = build_extractive_skill(conv.book, name=name, exclude=exclude, source=args.license)
    except ValueError as exc:
        raise UsageError(f"{exc}; run `book-to-skill inspect` to see what was found") from exc
    root = write_skill(pkg, args.out)
    if args.markdown:
        (root / "book.md").write_text(book_to_markdown(conv.book), encoding="utf-8", newline="\n")
    chapters = [ch for ch in conv.book.chapters if is_content_chapter(ch)]
    book_words = sum(len(b.text.split()) for ch in chapters for b in ch.blocks(exclude))
    ref_words = sum(len(t.split()) for t in pkg.references.values())
    print(f"wrote {root}")
    print(f"  SKILL.md           {len(pkg.skill_md.split()):>7} words")
    print(f"  references/*.md    {ref_words:>7} words in {len(pkg.references)} files")
    print(f"  chapter text       {book_words:>7} words ({coverage:.0%} of the book's text)")
    print(f"  reference / chapter words: {ref_words / max(book_words, 1):.2f}")
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
    print(f"text inside numbered chapters: {content_coverage(conv.book):.0%}")
    if rep.removed_examples:
        print("header/footer lines removed, e.g.: " + " | ".join(rep.removed_examples[:3]))
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
            f"  {name:34s} recall@1000w (term) "
            f"{entry['term']['recall@1000w']['value']:.3f}  "
            f"evidence kept {entry['evidence_retained']['value']:.3f}"
        )
    return 0


def cmd_model_arm(args: argparse.Namespace) -> int:
    from booktoskill import model_arm
    from booktoskill.experiments import book_specs
    from booktoskill.llm import list_models, ollama_client

    specs = book_specs(args.data)
    if args.dry_run:
        print(json.dumps(model_arm.plan(specs), indent=2))
        return 0
    available = list_models(args.url)
    missing = [m for m in {args.model, args.judge_model} if m not in available]
    if missing:
        raise UsageError(f"ollama has not pulled {', '.join(missing)}; run `ollama pull` first")
    cache = Path(args.cache)
    client = ollama_client(cache, args.model, args.url)
    judge = ollama_client(cache, args.judge_model, args.url)
    report = model_arm.run(specs, args.results, args.out, client, judge, k=args.k)
    print(json.dumps(report["pooled_qa"], indent=2))
    print(f"model calls: {client.calls + judge.calls} new, {client.hits + judge.hits} cached")
    return 0


class LowCoverage(UsageError):
    """The detected chapters hold too little of the book (exit code 3)."""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="book-to-skill",
        description="Turn a technical book PDF into a Claude Code skill package.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    def pdf_args(sp: argparse.ArgumentParser, exclude: bool) -> None:
        sp.add_argument("pdf", help="a born-digital PDF (not scanned)")
        sp.add_argument("--title", help="book title (default: the PDF's metadata or first heading)")
        if exclude:
            sp.add_argument(
                "--exclude-section",
                action="append",
                metavar="TITLE",
                help="leave out sections with this title, e.g. Exercises (repeatable)",
            )

    c = sub.add_parser("convert", help="write a skill package for a PDF")
    pdf_args(c, exclude=True)
    c.add_argument("--out", default="skills", help="output directory (default: skills)")
    c.add_argument("--name", help="skill name (default: slug of the title)")
    c.add_argument(
        "--license",
        metavar="TEXT",
        help='source attribution and licence, written into SKILL.md, e.g. "Allen B. Downey, '
        'Green Tea Press, CC BY-NC 3.0"',
    )
    c.add_argument("--markdown", action="store_true", help="also write the full book as book.md")
    c.add_argument(
        "--allow-low-coverage",
        action="store_true",
        help=f"write the skill even if under {MIN_COVERAGE * 100:.0f}%% of the text is in chapters",
    )
    c.set_defaults(func=cmd_convert)

    i = sub.add_parser("inspect", help="show detected chapters and what was repaired")
    pdf_args(i, exclude=False)
    i.add_argument("--sections", action="store_true", help="list sections too")
    i.set_defaults(func=cmd_inspect)

    s = sub.add_parser("search", help="BM25 search over the book's chunks")
    pdf_args(s, exclude=True)
    s.add_argument("query")
    s.add_argument("-k", type=_positive, default=5, help="results to show (default 5)")
    s.add_argument("--chunk-words", type=_positive, default=200, help="chunk size (default 200)")
    s.set_defaults(func=cmd_search)

    e = sub.add_parser("experiments", help="rerun every no-model result in results/")
    e.add_argument("--data", default="data", help="folder holding raw/ (default: data)")
    e.add_argument("--results", default="results", help="output folder (default: results)")
    e.set_defaults(func=cmd_experiments)

    m = sub.add_parser("model-arm", help="skill generation and QA with a local model")
    m.add_argument("--data", default="data", help="folder holding raw/ (default: data)")
    m.add_argument("--results", default="results", help="output folder (default: results)")
    m.add_argument("--out", default="out/skills", help="where generated skills are written")
    m.add_argument("--cache", default="data/cache/llm", help="generation cache folder")
    m.add_argument("--url", default="http://127.0.0.1:11434", help="Ollama server (default: local)")
    m.add_argument(
        "--model", default="qwen2.5:14b-instruct", help="answering and skill-writing model"
    )
    m.add_argument("--judge-model", default="qwen2.5:14b-instruct", help="grading model")
    m.add_argument("-k", type=_positive, default=5, help="chunks retrieved for RAG (default 5)")
    m.add_argument("--dry-run", action="store_true", help="print the job list and call count")
    m.set_defaults(func=cmd_model_arm)
    return p


def main(argv: list[str] | None = None) -> int:
    # Titles and page text are Unicode; a Windows console or pipe may not be.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except LowCoverage as exc:
        print(f"book-to-skill: error: {exc}", file=sys.stderr)
        return 3
    except (UsageError, FileNotFoundError, LLMError) as exc:
        print(f"book-to-skill: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
