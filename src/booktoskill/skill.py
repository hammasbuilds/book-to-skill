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

from booktoskill.bm25 import STOPWORDS, stem
from booktoskill.layout import Block
from booktoskill.structure import Book, Chapter, is_content_chapter

_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+(?=[A-Z(\"'])")
_WORD_RE = re.compile(r"[a-z][a-z-]{2,}")
# Sentences that define a term. Font weight is deliberately NOT used: the
# evaluation's gold passages are the author's bold terms, and a writer that
# keyed on bold would pass the test by construction.
DEFINING_RE = re.compile(
    r"\b(?:is called|are called|is known as|are known as|we call|refers? to|"
    r"is defined as|are defined as|is a (?:\w+ ){0,3}(?:that|which|used)|"
    r"means that|is short for|stands for)\b",
    re.I,
)
MAX_DESCRIPTION = 1024
SKILL_NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
MAX_NAME = 64


@dataclass
class SkillPackage:
    name: str
    skill_md: str
    references: dict[str, str]  # file name -> markdown
    chapter_files: dict[str, str] = field(default_factory=dict)  # chapter number -> file name

    def reference_by_chapter(self) -> dict[str, str]:
        return {ch: self.references[f] for ch, f in self.chapter_files.items()}

    def prose_budget_by_chapter(self) -> dict[str, int]:
        """Per chapter, the words of its reference file that can hold book prose."""
        return {ch: prose_words(t) for ch, t in self.reference_by_chapter().items()}

    @property
    def words(self) -> int:
        return len(self.skill_md.split()) + sum(len(t.split()) for t in self.references.values())


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].rstrip("-") or "untitled"


def skill_name(title: str) -> str:
    """A valid skill name: lowercase letters, digits and hyphens, at most 64 chars."""
    return slugify(title, MAX_NAME)


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
            parts = {stem(w) for w in term.split()}  # "card" and "cards" overlap
            covered = [p for p in picked if parts & {stem(w) for w in p.split()}]
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


_FENCE_RE = re.compile(r"^```.*?^```[ \t]*$", re.S | re.M)
_BOILERPLATE = ("Source pages ", "Open this file for questions about:")
_EXAMPLE_LEAD_RE = re.compile(r"^From \*[^*\n]+\*:\s*")
_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def prose_text(markdown: str) -> str:
    """The part of a reference file that can hold book prose.

    Drops what cannot: fenced code, headings, table rows, the "Source pages"
    and "Open this file for questions about" boilerplate, the "From *Section*:"
    label of a worked example and list markers. The random control is given
    this many words, so skill and control are compared on the same prose budget.
    """
    kept = []
    for line in _FENCE_RE.sub("", markdown).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "|")) or stripped.startswith(_BOILERPLATE):
            continue
        kept.append(_BULLET_RE.sub("", _EXAMPLE_LEAD_RE.sub("", stripped)))
    return "\n".join(kept)


def prose_words(markdown: str) -> int:
    return len(prose_text(markdown).split())


def _definitions(blocks: list[Block], limit: int, already: set[str]) -> list[str]:
    """Defining sentences not already in the file (``already``: the section leads)."""
    found = []
    for b in blocks:
        if b.kind != "paragraph":
            continue
        for s in sentences(b.text):
            fresh = s not in found and s not in already
            if fresh and DEFINING_RE.search(s) and 6 <= len(s.split()) <= 45:
                found.append(s)
    return found[:limit]


def _examples(
    ch: Chapter, exclude: tuple[str, ...], limit: int, max_lines: int, already: set[str]
) -> list[str]:
    """One code example per section, led by the sentence before it unless the
    file already has that sentence (``already``)."""
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
                lead = "" if lead in already else lead
                label = f"From *{section.title}*:" + (f" {lead}" if lead else "")
                out.append(f"{label}\n\n```\n{code}\n```")
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
    leads: set[str] = set()
    intro = [b for b in ch.intro if b.kind == "paragraph"]
    if intro:
        lead = sentences(intro[0].text)[:lead_sentences]
        leads.update(lead)
        lines += [" ".join(lead), ""]
    for s in ch.sections:
        if s.title.lower() in excluded:
            continue
        lines.append(f"### {s.number} {s.title}".replace("###  ", "### "))
        paras = [b for b in s.blocks if b.kind == "paragraph"]
        if paras:
            # a section may open with a sentence the chapter intro already used
            lead = [s for s in sentences(paras[0].text)[:lead_sentences] if s not in leads]
            leads.update(lead)
            if lead:
                lines += ["", " ".join(lead)]
        lines.append("")
    defs = _definitions(ch.blocks(exclude), max_definitions, leads)
    if defs:
        lines += ["## Key definitions", ""] + [f"- {d}" for d in defs] + [""]
    examples = _examples(ch, exclude, max_examples, max_code_lines, leads | set(defs))
    if examples:
        lines += ["## Worked examples", ""]
        for ex in examples:
            lines += [ex, ""]
    return "\n".join(lines).strip() + "\n"


def skill_markdown(
    name: str,
    title: str,
    chapters: list[Chapter],
    files: dict[str, str],
    triggers: list[list[str]],
    source: str | None = None,
) -> str:
    """SKILL.md: YAML frontmatter plus a one-row-per-chapter index.

    ``source`` (author, publisher, licence) goes into the frontmatter's
    ``license`` field and under the title: the reference files are extracts
    of the book and carry its licence, not this tool's.
    """
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
        *([f"license: {json.dumps(source, ensure_ascii=False)}"] if source else []),
        "---",
        "",
        f"# {title}",
        "",
        *([f"Extracted from *{title}*: {source}.", ""] if source else []),
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
    source: str | None = None,
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
    md = skill_markdown(name, book.title, chapters, files, triggers, source)
    return SkillPackage(name, md, refs, files)


def reference_file_name(ch: Chapter) -> str:
    number = ch.number.zfill(2) if ch.number.isdigit() else ch.number
    return f"references/ch{number}-{slugify(ch.title)}.md"


def write_skill(pkg: SkillPackage, out_dir: str | Path) -> Path:
    """Write the package to ``out_dir/<name>``.

    Reference files left from an earlier conversion into the same folder
    (``references/*.md`` this package does not have) are removed, so an agent
    never routes to a chapter that no longer exists. Other files are kept.
    """
    if len(pkg.name) > MAX_NAME or not SKILL_NAME_RE.fullmatch(pkg.name):
        raise ValueError(f"invalid skill name {pkg.name!r}: it would not stay inside {out_dir}")
    root = Path(out_dir) / pkg.name
    refs = root / "references"
    refs.mkdir(parents=True, exist_ok=True)
    wanted = {Path(f).name for f in pkg.references}
    for old in refs.glob("*.md"):
        if old.name not in wanted:
            old.unlink()
    (root / "SKILL.md").write_text(pkg.skill_md, encoding="utf-8", newline="\n")
    for fname, text in pkg.references.items():
        (root / fname).write_text(text, encoding="utf-8", newline="\n")
    return root
