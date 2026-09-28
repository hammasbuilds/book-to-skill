"""The model writer: a local LLM writes each chapter's reference file.

It is given the same word budget as the extractive writer's file for that
chapter, so the two skills are compared at equal size, and the same SKILL.md
index, so they differ only in what the reference files say.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from booktoskill.llm import Client
from booktoskill.skill import (
    SkillPackage,
    distinctive_terms,
    reference_file_name,
    skill_markdown,
    skill_name,
)
from booktoskill.structure import Book, Chapter, is_content_chapter

SYSTEM = (
    "You write reference files for an AI agent skill built from a technical book. "
    "Use only information stated in the chapter text you are given."
)
REQUIRED_HEADINGS = ("## When to use", "## Sections", "## Key definitions", "## Worked examples")

PROMPT = """Below is chapter {number}, "{title}", of the book "{book}".
Write a reference file for this chapter in Markdown with exactly these parts:

# Chapter {number}: {title}
## When to use
One sentence naming the kinds of questions this chapter answers.
## Sections
One "### <number> <title>" heading for each section listed below, each followed by
one to three sentences summarising that section.
## Key definitions
A bullet list, "- **term**: definition", of the technical terms the chapter defines,
using the chapter's own wording where possible.
## Worked examples
Up to four short code examples copied from the chapter, each with one sentence
saying what it shows.

Sections of this chapter:
{sections}

Keep the whole file under {budget} words. Do not add anything the chapter does not say.

CHAPTER TEXT
{text}
"""


MAX_CHAPTER_WORDS = 9000  # fits num_ctx 16384 with the prompt and the reply


@dataclass(frozen=True)
class ChapterText:
    text: str
    words: int  # words of the chapter (excluded sections left out)
    kept_words: int  # words given to the model

    @property
    def truncated(self) -> bool:
        return self.kept_words < self.words


def chapter_markdown(ch: Chapter, exclude: tuple[str, ...], max_words: int) -> ChapterText:
    """The chapter as plain Markdown, cut at the last whole block within ``max_words``."""
    excluded = {e.lower() for e in exclude}
    parts: list[str] = [b.text for b in ch.intro]
    for s in ch.sections:
        if s.title.lower() in excluded:
            continue
        parts.append(f"### {s.number} {s.title}".strip())
        for b in s.blocks:
            parts.append(f"```\n{b.text}\n```" if b.kind == "code" else b.text)
    words = 0
    kept: list[str] = []
    for p in parts:
        n = len(p.split())
        if words + n > max_words:
            break
        kept.append(p)
        words += n
    total = sum(len(p.split()) for p in parts)
    return ChapterText("\n\n".join(kept), total, words)


def reference_prompt(
    book_title: str,
    ch: Chapter,
    budget: int,
    exclude: tuple[str, ...],
    max_words: int = MAX_CHAPTER_WORDS,
) -> tuple[str, ChapterText]:
    """The prompt for one chapter, and what of the chapter it contains."""
    sections = "\n".join(
        f"- {s.number} {s.title}".rstrip()
        for s in ch.sections
        if s.title.lower() not in {e.lower() for e in exclude}
    )
    text = chapter_markdown(ch, exclude, max_words)
    prompt = PROMPT.format(
        number=ch.number,
        title=ch.title,
        book=book_title,
        sections=sections or "- (no numbered sections)",
        budget=budget,
        text=text.text,
    )
    return prompt, text


@dataclass
class GenerationReport:
    missing_headings: dict[str, list[str]] = field(default_factory=dict)
    words: dict[str, int] = field(default_factory=dict)
    budgets: dict[str, int] = field(default_factory=dict)
    # chapter -> [words given to the model, words in the chapter], for chapters cut short
    truncated: dict[str, list[int]] = field(default_factory=dict)


def build_llm_skill(
    book: Book,
    client: Client,
    budgets: dict[str, int],
    name: str | None = None,
    exclude: tuple[str, ...] = (),
    max_chapter_words: int = MAX_CHAPTER_WORDS,
) -> tuple[SkillPackage, GenerationReport]:
    """One model call per chapter; ``budgets`` maps chapter number to a word cap."""
    chapters = [ch for ch in book.chapters if is_content_chapter(ch)]
    if not chapters:
        raise ValueError("no numbered chapters were detected; cannot build a skill")
    name = name or skill_name(book.title)
    triggers = distinctive_terms(chapters, exclude)
    files = {ch.number: reference_file_name(ch) for ch in chapters}
    report = GenerationReport()
    refs: dict[str, str] = {}
    for ch in chapters:
        budget = budgets.get(ch.number, 600)
        prompt, source = reference_prompt(book.title, ch, budget, exclude, max_chapter_words)
        if source.truncated:
            report.truncated[ch.number] = [source.kept_words, source.words]
        text = client.generate(prompt, SYSTEM).strip()
        missing = [h for h in REQUIRED_HEADINGS if h not in text]
        if missing:
            report.missing_headings[ch.number] = missing
        report.words[ch.number] = len(text.split())
        report.budgets[ch.number] = budget
        refs[files[ch.number]] = text + "\n"
    md = skill_markdown(name, book.title, chapters, files, triggers)
    return SkillPackage(name, md, refs, files), report
