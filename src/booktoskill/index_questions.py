"""The primary question set: the author's own back-of-book index.

Every index entry is an anchor the author placed where a concept is
discussed - ``\\index{term}`` in LaTeX, ``(((term)))`` in Asciidoc. Each
distinct index term becomes a question ("Where does the book explain X?")
whose gold evidence is every sentence of the paragraph(s) that term's anchors
sit in, within the chapter of its first anchor. Nothing here looks at bold
type or at defining phrases, which is what makes this set independent of both
the glossary set and the skill writer's definitions regex.

Anchor-to-paragraph rule: an anchor belongs to the paragraph it sits in; an
anchor in a block with no prose of its own (index commands right after a
section heading, before the text) belongs to the next prose paragraph.

Every term is assigned once, by a hash of book and term, to ``dev`` (80%) or
``test`` (20%). The assignment was fixed before any result was computed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from booktoskill.references import GoldItem, detex

MIN_SENTENCE_WORDS = 5
_SENTENCE_RE = re.compile(r"(?<=[.?!:])\s+(?=[A-Z\"'(`])")


@dataclass(frozen=True)
class Anchor:
    term: str
    chapter: str
    chapter_title: str
    paragraph: str  # plain text of the paragraph the anchor points at


def split_of(book: str, term: str) -> str:
    digest = hashlib.sha256(f"{book}\x00{term.lower()}".encode()).hexdigest()
    return "test" if int(digest, 16) % 5 == 0 else "dev"


def sentences(paragraph: str) -> list[str]:
    return [
        s.strip() for s in _SENTENCE_RE.split(paragraph) if len(s.split()) >= MIN_SENTENCE_WORDS
    ]


def _paragraph_for(blocks: list[str], i: int) -> str | None:
    """The prose of block ``i``, or of the next block with prose."""
    for block in blocks[i:]:
        if len(block.split()) >= MIN_SENTENCE_WORDS:
            return block
    return None


def _anchors_in_blocks(
    raw_blocks: list[str],
    prose: list[str],
    pattern: re.Pattern[str],
    normalise: callable,  # type: ignore[valid-type]
    chapter: str,
    title: str,
) -> list[Anchor]:
    out = []
    for i, block in enumerate(raw_blocks):
        for m in pattern.finditer(block):
            term = normalise(m.group(1))
            paragraph = _paragraph_for(prose, i)
            if term and paragraph:
                out.append(Anchor(term, chapter, title, paragraph))
    return out


# --------------------------------------------------------------------- LaTeX

_INDEX_RE = re.compile(r"\\index\{((?:[^{}]|\{[^{}]*\})*)\}")
_DROP_ENVS = re.compile(r"\\begin\{(verbatim|code|stdout|figure|table)\}.*?\\end\{\1\}", re.S)
_HEADING_CMD = re.compile(r"\\(?:sub)*section\*?\{(?:[^{}]|\{[^{}]*\})*\}")


def latex_term(entry: str) -> str:
    """``statement!assignment`` -> ``assignment statement``; ``key@display`` -> display."""
    entry = entry.split("|", 1)[0]
    parts = []
    for part in entry.split("!"):
        part = part.split("@", 1)[-1]
        parts.append(detex(part).strip())
    term = " ".join(reversed([p for p in parts if p]))
    return term if re.search("[A-Za-z]{2}", term) else ""


def _latex_chapters(tex: str) -> list[tuple[str, str, str]]:
    """``(number, title, body)`` for each numbered chapter of the main matter."""
    main = tex.split("\\mainmatter")[-1].split("\\appendix")[0]
    out = []
    for n, part in enumerate(re.split(r"\\chapter\{", main)[1:], start=1):
        depth, i = 1, 0
        while depth and i < len(part):
            depth += {"{": 1, "}": -1}.get(part[i], 0)
            i += 1
        out.append((str(n), detex(part[: i - 1]), part[i:]))
    return out


def latex_anchors(tex: str, holdout: tuple[str, ...] = ("Glossary",)) -> list[Anchor]:
    anchors: list[Anchor] = []
    for number, title, body in _latex_chapters(tex):
        for name in holdout:
            body = re.sub(r"\\section\{" + name + r"\}.*?(?=\\section\{|$)", "", body, flags=re.S)
        body = _DROP_ENVS.sub("\n\n", body)
        body = _HEADING_CMD.sub("\n\n", body)
        raw = [b for b in re.split(r"\n\s*\n", body) if b.strip()]
        prose = [detex(_INDEX_RE.sub(" ", b)) for b in raw]
        anchors += _anchors_in_blocks(raw, prose, _INDEX_RE, latex_term, number, title)
    return anchors


# ------------------------------------------------------------------ Asciidoc

_ASC_INDEX_RE = re.compile(r"\(\(\(([^()]*)\)\)\)")
_INCLUDE_RE = re.compile(r"^include::([^\[]+)\[\]", re.M)
_ASC_INLINE = [
    (r"\(\(\([^()]*\)\)\)", ""),
    (r"footnote:\[([^\]]*)\]", r" \1"),
    (r"(?:link:)?(?:https?|ftp)://\S+?\[([^\]]*)\]", r"\1"),
    (r"<<[^,>]*,\s*([^>]*)>>", r"\1"),
    (r"<<[^>]*>>", ""),
    (r"kbd:\[([^\]]*)\]", r"\1"),
    (r"\"`([^`]*)`\"", r"\1"),
    (r"'`([^`]*)`'", r"\1"),
    (r"`+([^`]*)`+", r"\1"),
    (r"(?<!\w)[*_]{1,2}([^*_\n]+?)[*_]{1,2}(?!\w)", r"\1"),
    (r"\{(?:empty|nbsp|sp)\}", " "),
    (r"\s+\+$", ""),
]


def asciidoc_text(block: str) -> str:
    lines = []
    for line in block.splitlines():
        s = line.strip()
        if not s or s.startswith(("[", "image::", "include::", "//", "=", ":", "|===")):
            continue
        if re.match(r"^\.[A-Za-z]", s) or s in ("====", "****", "____", "--"):
            continue
        lines.append(re.sub(r"^[*.]+\s+", "", s))
    text = " ".join(lines)
    for pattern, repl in _ASC_INLINE:
        text = re.sub(pattern, repl, text)
    return re.sub(r"\s+", " ", text).strip()


def asciidoc_term(entry: str) -> str:
    """``git commands, add`` -> ``git add``; ``version control,local`` -> ``local
    version control``."""
    parts = [p.strip() for p in entry.split(",") if p.strip()]
    if not parts:
        return ""
    if parts[0].lower() == "git commands" and len(parts) > 1:
        return "git " + parts[1]
    return " ".join(reversed(parts))


def expand_includes(path: Path, root: Path) -> str:
    text = path.read_text(encoding="utf-8")

    def sub(m: re.Match[str]) -> str:
        target = (path.parent / m.group(1)).resolve()
        if not target.is_file() or root.resolve() not in target.parents:
            return ""
        return expand_includes(target, root)

    return _INCLUDE_RE.sub(sub, text)


def asciidoc_anchors(chapter_files: list[tuple[str, Path]], root: Path) -> list[Anchor]:
    """``chapter_files`` pairs a chapter number with its top-level .asc file."""
    anchors: list[Anchor] = []
    for number, path in chapter_files:
        text = expand_includes(path, root)
        title_m = re.search(r"^== (.+)$", text, re.M)
        title = title_m.group(1).strip() if title_m else path.stem
        # listings and literal blocks hold code, not prose, and may hold blank lines
        text = re.sub(r"^(-{4,}|\.{4,})\s*$.*?^\1\s*$", "\n\n", text, flags=re.M | re.S)
        raw = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
        prose = [asciidoc_text(b) for b in raw]
        anchors += _anchors_in_blocks(raw, prose, _ASC_INDEX_RE, asciidoc_term, number, title)
    return anchors


# ------------------------------------------------------------------- items


def items_from_anchors(
    anchors: list[Anchor], book: str, glossary_terms: set[str]
) -> list[GoldItem]:
    """One question per distinct term, in the chapter of its first anchor."""
    first: dict[str, Anchor] = {}
    paragraphs: dict[str, list[str]] = {}
    for a in anchors:
        key = a.term.lower()
        first.setdefault(key, a)
        if a.chapter == first[key].chapter and a.paragraph not in paragraphs.setdefault(key, []):
            paragraphs[key].append(a.paragraph)
    items = []
    for n, (key, anchor) in enumerate(first.items()):
        evidence = tuple(s for p in paragraphs[key] for s in sentences(p))
        if not evidence:
            continue
        items.append(
            GoldItem(
                qid=f"{book}-idx-{n:04d}",
                book=book,
                chapter=anchor.chapter,
                chapter_title=anchor.chapter_title,
                term=anchor.term,
                definition="",
                gold_passage="\n\n".join(paragraphs[key]),
                gold_sentence=evidence[0],
                evidence=evidence,
                kind="index",
                split=split_of(book, anchor.term),
                in_glossary=_variants(key) & glossary_terms != set(),
            )
        )
    return items


def _variants(term: str) -> set[str]:
    t = term.lower()
    out = {t, t.rstrip("s"), t + "s"}
    if t.endswith("ies"):
        out.add(t[:-3] + "y")
    return out
