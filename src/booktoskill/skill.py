"""Write a book as a Claude Code skill package.

Layout of a package::

    <name>/
      SKILL.md                      frontmatter (name, description) + chapter index
      references/ch01-<slug>.md     one reference file per chapter

``SKILL.md`` is what an agent loads up front, so it stays short: one row per
chapter saying what the chapter covers and which file to open. Each reference
file carries "when to use" triggers, section summaries, key definitions and
worked examples.

Two writers produce the reference files. The extractive writer here selects
sentences and code from the book with fixed rules and no model. The model
writer (``llm_skill.py``) asks a local model to write the same sections.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from booktoskill.bm25 import STOPWORDS
from booktoskill.layout import Block
from booktoskill.structure import Book, Chapter, is_content_chapter

_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+(?=[A-Z(\"'])")
_WORD_RE = re.compile(r"[a-z][a-z-]{2,}")
# Sentences that define a term. Font weight is deliberately NOT used: the
# evaluation's gold passages are the author's bold terms, and a writer that
# keyed on bold would pass the test by construction.
_DEFINING_RE = re.compile(
    r"\b(?:is called|are called|is known as|are known as|we call|refers? to|"
    r"is defined as|are defined as|is a (?:\w+ ){0,3}(?:that|which|used)|"
    r"means that|is short for|stands for)\b",
    re.I,
)
MAX_DESCRIPTION = 1024


@dataclass
class SkillPackage:
    name: str
    skill_md: str
    references: dict[str, str]  # file name -> markdown
    chapter_files: dict[str, str] = field(default_factory=dict)  # chapter number -> file name

    def reference_by_chapter(self) -> dict[str, str]:
        return {ch: self.references[f] for ch, f in self.chapter_files.items()}

    @property
    def words(self) -> int:
        return len(self.skill_md.split()) + sum(len(t.split()) for t in self.references.values())


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].rstrip("-") or "untitled"


def skill_name(title: str) -> str:
    """A valid skill name: lowercase letters, digits and hyphens, at most 64 chars."""
    return slugify(title, 64)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]


def distinctive_terms(
    chapters: list[Chapter], exclude: tuple[str, ...], n: int = 8
) -> list[list[str]]:
    """Per chapter, the words and two-word phrases that most distinguish it.

    Scored by TF-IDF across the book's chapters. A phrase replaces a picked
    word it contains ("tuple" gives way to "tuple assignment"), so the list
    reads as topics rather than as fragments.
    """
    docs: list[Counter[str]] = []
    for ch in chapters:
        counts: Counter[str] = Counter()
        for b in ch.blocks(exclude):
            if b.kind != "paragraph":
                continue
            words = _WORD_RE.findall(b.text.lower())
            counts.update(w for w in words if len(w) >= 4 and w not in STOPWORDS)
            counts.update(
                f"{x} {y}"
                for x, y in zip(words, words[1:], strict=False)
                if x not in STOPWORDS and y not in STOPWORDS
            )
        docs.append(counts)
    df: Counter[str] = Counter()
    for d in docs:
        df.update(d.keys())
    out = []
    for d in docs:
        scored = sorted(
            ((tf * math.log(len(docs) / df[t]), t) for t, tf in d.items() if tf >= 3),
            reverse=True,
        )
        picked: list[str] = []
        for _, term in scored:
            parts = set(term.split())
            covered = [p for p in picked if parts & set(p.split())]
            if covered:
                # A phrase may absorb one single word it contains; otherwise skip.
                if " " in term and len(covered) == 1 and " " not in covered[0]:
                    picked[picked.index(covered[0])] = term
                continue
            picked.append(term)
            if len(picked) == n:
                break
        out.append(picked)
    return out


def _definitions(blocks: list[Block], limit: int) -> list[str]:
    found = []
    for b in blocks:
        if b.kind != "paragraph":
            continue
        for s in sentences(b.text):
            if _DEFINING_RE.search(s) and 6 <= len(s.split()) <= 45 and s not in found:
                found.append(s)
    return found[:limit]


def _examples(ch: Chapter, exclude: tuple[str, ...], limit: int, max_lines: int) -> list[str]:
    out = []
    excluded = {e.lower() for e in exclude}
    for section in ch.sections:
        if section.title.lower() in excluded:
            continue
        prev = ""
        for b in section.blocks:
            if b.kind == "code" and b.text.count("\n") >= 1:
                code = "\n".join(b.text.splitlines()[:max_lines])
                lead = sentences(prev)[-1] if prev else ""
                out.append(f"From *{section.title}*: {lead}\n\n```\n{code}\n```")
                break  # one example per section keeps the file short
            if b.kind == "paragraph":
                prev = b.text
        if len(out) == limit:
            break
    return out


def extractive_reference(
    ch: Chapter,
    triggers: list[str],
    exclude: tuple[str, ...] = (),
    lead_sentences: int = 2,
    max_definitions: int = 12,
    max_examples: int = 4,
    max_code_lines: int = 12,
) -> str:
    """A reference file built from the chapter by fixed selection rules."""
    excluded = {e.lower() for e in exclude}
    lines = [f"# Chapter {ch.number}: {ch.title}", ""]
    lines += [f"Source pages {ch.page + 1}-{ch.last_page + 1} of the PDF.", ""]
    lines += ["## When to use", ""]
    lines += [f"Open this file for questions about: {', '.join(triggers)}.", ""]
    lines += ["## Sections", ""]
    intro = [b for b in ch.intro if b.kind == "paragraph"]
    if intro:
        lines += [" ".join(sentences(intro[0].text)[:lead_sentences]), ""]
    for s in ch.sections:
        if s.title.lower() in excluded:
            continue
        lines.append(f"### {s.number} {s.title}".replace("###  ", "### "))
        paras = [b for b in s.blocks if b.kind == "paragraph"]
        if paras:
            lines += ["", " ".join(sentences(paras[0].text)[:lead_sentences])]
        lines.append("")
    defs = _definitions(ch.blocks(exclude), max_definitions)
    if defs:
        lines += ["## Key definitions", ""] + [f"- {d}" for d in defs] + [""]
    examples = _examples(ch, exclude, max_examples, max_code_lines)
    if examples:
        lines += ["## Worked examples", ""]
        for ex in examples:
            lines += [ex, ""]
    return "\n".join(lines).strip() + "\n"


def skill_markdown(
    name: str, title: str, chapters: list[Chapter], files: dict[str, str], triggers: list[list[str]]
) -> str:
    """SKILL.md: YAML frontmatter plus a one-row-per-chapter index."""
    names = "; ".join(ch.title for ch in chapters)
    description = (
        f'Knowledge from the book "{title}": {names}. Use when a task needs the '
        f"book's definitions, explanations or worked examples on these topics."
    )
    if len(description) > MAX_DESCRIPTION:
        description = description[: MAX_DESCRIPTION - 4].rsplit(";", 1)[0] + " ..."
    lines = [
        "---",
        f"name: {name}",
        f"description: {json.dumps(description, ensure_ascii=False)}",
        "---",
        "",
        f"# {title}",
        "",
        "Each chapter of the book has a reference file with its sections, key definitions "
        "and worked examples. Find the chapter below whose topics match the task, then "
        "read only that file.",
        "",
        "| Chapter | Topics | File |",
        "|---|---|---|",
    ]
    for ch, t in zip(chapters, triggers, strict=True):
        lines.append(f"| {ch.number}. {ch.title} | {', '.join(t)} | `{files[ch.number]}` |")
    return "\n".join(lines) + "\n"


def build_extractive_skill(
    book: Book,
    name: str | None = None,
    exclude: tuple[str, ...] = (),
    max_definitions: int = 12,
) -> SkillPackage:
    """A skill package whose reference files are selected from the book, no model."""
    chapters = [ch for ch in book.chapters if is_content_chapter(ch)]
    if not chapters:
        raise ValueError("no numbered chapters were detected; cannot build a skill")
    name = name or skill_name(book.title)
    triggers = distinctive_terms(chapters, exclude)
    files = {ch.number: reference_file_name(ch) for ch in chapters}
    refs = {
        files[ch.number]: extractive_reference(ch, t, exclude, max_definitions=max_definitions)
        for ch, t in zip(chapters, triggers, strict=True)
    }
    md = skill_markdown(name, book.title, chapters, files, triggers)
    return SkillPackage(name, md, refs, files)


def reference_file_name(ch: Chapter) -> str:
    number = ch.number.zfill(2) if ch.number.isdigit() else ch.number
    return f"references/ch{number}-{slugify(ch.title)}.md"


def write_skill(pkg: SkillPackage, out_dir: str | Path) -> Path:
    root = Path(out_dir) / pkg.name
    (root / "references").mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(pkg.skill_md, encoding="utf-8")
    for fname, text in pkg.references.items():
        (root / fname).write_text(text, encoding="utf-8")
    return root
