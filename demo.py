"""Run the whole pipeline on a PDF whose correct answer is known.

The input is a six-page book written by ``booktoskill.samplepdf``: it has a
running header with page numbers, a word hyphenated across a line break, a
genuine compound hyphen split at a line end, an indented code block, inline
code set in a second font with no space glyph between them, and a figure
label drawn inside a form XObject. Every one of those is a known defect with
a known correct output, checked below. Then the skill package is written and
printed.

    uv run python demo.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from booktoskill.pipeline import blocks_text, convert
from booktoskill.samplepdf import tiny_book, write_pdf
from booktoskill.skill import build_extractive_skill, write_skill
from booktoskill.structure import is_content_chapter


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="book-to-skill-demo-"))
    pdf = write_pdf(work / "tiny-book.pdf", tiny_book())
    conv = convert(pdf)
    text = blocks_text(conv.blocks)
    code = [b.text for b in conv.blocks if b.kind == "code"]
    chapters = [(c.number, c.title) for c in conv.book.chapters if is_content_chapter(c)]
    sections = [s.number for c in conv.book.chapters for s in c.sections if c.number]

    checks = [
        ("running header removed", "1.2. Glossary 3" not in text),
        ("page number offset found", conv.report.page_number_offset == 0),
        ("chapter opener kept", "Chapter 1" in text),
        ("figure label dropped", "fig label" not in text),
        ("line-break hyphen joined", "write assignments all the time" in text),
        ("real compound kept", "are a well-known way" in text),
        ("code indentation kept", code == ["def double(x):\n    return 2 * x"]),
        ("space at font change", "Call it with double(21) to get 42." in text),
        ("chapters", chapters == [("1", "Getting Started"), ("2", "Next Steps")]),
        ("sections", sections == ["1.1", "1.2", "2.1", "2.2"]),
    ]
    print(f"input: {pdf.name}, {len(conv.pages)} pages, title found: {conv.book.title!r}\n")
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    passed = sum(ok for _, ok in checks)
    print(f"\n{passed}/{len(checks)} checks passed against the known answer\n")

    root = write_skill(build_extractive_skill(conv.book), work / "skills")
    print(f"skill written to {root}\n")
    print("---- SKILL.md " + "-" * 50)
    print((root / "SKILL.md").read_text(encoding="utf-8"))
    ref = sorted((root / "references").iterdir())[0]
    print(f"---- {ref.relative_to(root).as_posix()} " + "-" * 30)
    print(ref.read_text(encoding="utf-8"))
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
