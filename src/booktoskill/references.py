"""Independent references for grading the pipeline.

* The book's **HTML edition** (hevea for the Think books, Asciidoctor for Pro Git),
  generated from the same source as the PDF, gives the reference text of each
  chapter and the reference table of contents.
* The book's **LaTeX source** gives the definition question set: every
  end-of-chapter glossary entry is a question, and its gold passage is the
  body paragraph in which the author set that term in bold when introducing
  it. Both come from the author's own markup, never from this pipeline's
  output, so the question set is not circular.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

_BLOCK_TAGS = {"p", "pre", "li", "dd", "dt", "div", "tr", "blockquote", "br", "table", "h3", "h4"}


@dataclass
class RefSection:
    number: str
    title: str


@dataclass
class RefChapter:
    number: str  # "" for unnumbered front/back matter
    title: str
    sections: list[RefSection] = field(default_factory=list)
    text: str = ""
    code_blocks: list[str] = field(default_factory=list)

    @property
    def numbered(self) -> bool:
        """A real chapter or appendix (hevea numbers the preface "0")."""
        return self.number not in ("", "0")


@dataclass(frozen=True)
class EditionStyle:
    """How one HTML generator marks chapters, sections and the end of content."""

    chapter_tag: str
    section_tag: str
    number_title: Callable[[str, dict[str, str | None]], tuple[str, str]]
    is_end: Callable[[str, dict[str, str | None]], bool]
    chapter_label: bool  # does the PDF print "Chapter N" above each title?


def _hevea_chapter(text: str, attrs: dict[str, str | None]) -> tuple[str, str]:
    m = re.match(r"(?:Chapter|Appendix)\s+([0-9A-Z]+)\s+(.*)", text)
    return (m.group(1), m.group(2).strip()) if m else ("", text)


def _asciidoctor_chapter(text: str, attrs: dict[str, str | None]) -> tuple[str, str]:
    # Pro Git's ids carry the numbering the headings do not: "ch03-...", "A-...".
    ident = attrs.get("id") or ""
    m = re.match(r"ch(\d+)-", ident) or re.match(r"([A-Z])-", ident)
    if not m:
        return "", text
    return (str(int(m.group(1))) if m.group(1).isdigit() else m.group(1)), text


HEVEA = EditionStyle(
    "h1",
    "h2",
    _hevea_chapter,
    # the donation/ads column after the content, and hevea's site footer
    lambda tag, a: (tag == "td" and a.get("width") == "130") or tag == "h4",
    chapter_label=True,
)
ASCIIDOCTOR = EditionStyle(
    "h2",
    "h3",
    _asciidoctor_chapter,
    lambda tag, a: tag == "div" and a.get("id") == "footer",
    chapter_label=False,
)


class _EditionParser(HTMLParser):
    """Collect chapter text from an HTML edition, skipping site furniture."""

    def __init__(self, style: EditionStyle) -> None:
        super().__init__(convert_charrefs=True)
        self.style = style
        self.chapters: list[RefChapter] = []
        self._buf: list[str] = []
        self._heading: str | None = None
        self._heading_attrs: dict[str, str | None] = {}
        self._head_buf: list[str] = []
        self._in_pre = False
        self._pre_buf: list[str] = []
        self._skip_depth = 0
        self._done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if self.style.is_end(tag, a):
            self._done = True
        if self._done:
            return
        if tag in (self.style.chapter_tag, self.style.section_tag):
            self._heading, self._heading_attrs, self._head_buf = tag, a, []
        elif tag == "a" and "amzn.to" in (a.get("href") or ""):
            self._skip_depth += 1
        elif tag == "pre":
            self._in_pre = True
            self._pre_buf = []
            self._buf.append("\n")
        elif tag in _BLOCK_TAGS:
            self._buf.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._done:
            return
        if tag == self._heading:
            self._close_heading(tag)
        elif tag == "a" and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "pre":
            self._in_pre = False
            if self.chapters:
                self.chapters[-1].code_blocks.append("".join(self._pre_buf).strip("\n"))
            self._buf.append("\n")
        elif tag in _BLOCK_TAGS:
            self._buf.append("\n")

    def handle_data(self, data: str) -> None:
        if self._done or self._skip_depth:
            return
        if self._heading:
            self._head_buf.append(data)
        elif self.chapters:
            if self._in_pre:
                self._pre_buf.append(data)
            self._buf.append(data if self._in_pre else re.sub(r"\s+", " ", data))

    def _close_heading(self, tag: str) -> None:
        text = "".join(self._head_buf).replace(chr(0xA0), " ").strip()
        self._heading = None
        if tag == self.style.chapter_tag:
            self._flush()
            number, title = self.style.number_title(text, self._heading_attrs)
            self.chapters.append(RefChapter(number, title))
            label = f"Chapter {number}\n" if number and self.style.chapter_label else ""
            self._buf.append(f"{label}{title}\n")
        elif self.chapters:
            m = re.match(r"([0-9A-Z]+\.\d+)\s+(.*)", text)
            number, title = (m.group(1), m.group(2).strip()) if m else ("", text)
            self.chapters[-1].sections.append(RefSection(number, title))
            self._buf.append(f"\n{text}\n")

    def _flush(self) -> None:
        if self.chapters:
            self.chapters[-1].text += "".join(self._buf)
        self._buf = []

    def close(self) -> None:
        super().close()
        self._flush()


def parse_html_edition(path: str | Path, style: EditionStyle = HEVEA) -> list[RefChapter]:
    """All chapters of an HTML edition: a folder of pages (hevea) or one file."""
    path = Path(path)
    pages = sorted(path.glob("*[0-9][0-9][0-9].html")) if path.is_dir() else [path]
    chapters: list[RefChapter] = []
    for page in pages:
        parser = _EditionParser(style)
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        parser.close()
        chapters.extend(parser.chapters)
    for ch in chapters:
        ch.text = re.sub(r"\n\s*\n+", "\n\n", ch.text).strip()
    return chapters


# --------------------------------------------------------------------- LaTeX


@dataclass(frozen=True)
class GoldItem:
    qid: str
    book: str
    chapter: int
    chapter_title: str
    term: str
    definition: str  # the glossary entry: the reference answer
    gold_passage: str  # the body paragraph that introduces the term in bold
    gold_sentence: str  # the sentence of that paragraph containing the bold term


_TEX_SIMPLE = [
    (r"\\index\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", ""),
    (r"\\label\{[^{}]*\}", ""),
    (r"~\\ref\{[^{}]*\}", " N"),
    (r"\\ref\{[^{}]*\}", "N"),
    (r"\\cite\{[^{}]*\}", ""),
    (r"\\url\{([^{}]*)\}", r"\1"),
    (r"\\href\{[^{}]*\}\{([^{}]*)\}", r"\1"),
    (r"\\footnote\{[^{}]*\}", ""),
    (r"\\verb(.)(.*?)\1", r"\2"),
    (r"\\(?:emph|textbf|texttt|textit|mathrm|mbox|hbox|tt|bf|em|it)\b\s*", ""),
    (r"\\(?:ldots|dots)\b", "..."),
    (r"\\%", "%"),
    (r"\\_", "_"),
    (r"\\&", "&"),
    (r"\\#", "#"),
    (r"\\\$", "$"),
    (r"``|''", '"'),
    (r"---", "\u2014"),
    (r"--", "\u2013"),
    (r"\\[a-zA-Z]+\*?", ""),
    (r"[{}$]", ""),
    (r"~", " "),
]


def detex(text: str) -> str:
    """A small LaTeX-to-text conversion, enough for prose paragraphs."""
    text = re.sub(r"(?<!\\)%.*", "", text)
    for pattern, repl in _TEX_SIMPLE:
        text = re.sub(pattern, repl, text)
    return re.sub(r"\s+", " ", text).strip()


def _split_chapters(tex: str) -> list[tuple[str, str]]:
    """``(title, body)`` for each numbered chapter, up to the appendices."""
    main = tex.split("\\mainmatter")[-1].split("\\appendix")[0]
    parts = re.split(r"\\chapter\{", main)[1:]
    out = []
    for part in parts:
        depth, i = 1, 0
        while depth and i < len(part):
            depth += {"{": 1, "}": -1}.get(part[i], 0)
            i += 1
        out.append((detex(part[: i - 1]), part[i:]))
    return out


def _glossary(body: str) -> list[tuple[str, str]]:
    m = re.search(r"\\section\{Glossary\}(.*?)(?=\\section\{|\\chapter\{|$)", body, re.S)
    if not m:
        return []
    block = m.group(1)
    items = re.split(r"\\item\s*", block)[1:]
    out = []
    for item in items:
        m1 = re.match(r"\[(.*?):?\]\s*(.*)", item, re.S)  # \item[term:] definition
        m2 = re.match(r"\{\\bf\s+(.*?)\}:?\s*(.*)", item, re.S)  # \item {\bf term}: definition
        m = m1 or m2
        if not m:
            continue
        term = detex(m.group(1)).rstrip(":").strip()
        definition = detex(
            re.sub(r"\\end\{(?:description|itemize)\}.*", "", m.group(2), flags=re.S)
        )
        if term and definition:
            out.append((term, definition))
    return out


def _body_without(body: str, sections: tuple[str, ...]) -> str:
    for name in sections:
        body = re.sub(r"\\section\{" + name + r"\}.*?(?=\\section\{|$)", "", body, flags=re.S)
    return body


def _term_variants(term: str) -> set[str]:
    t = term.lower()
    variants = {t, t + "s", t + "es"}
    if t.endswith("y"):
        variants.add(t[:-1] + "ies")
    return variants


def _sentence_with(paragraph: str, bold: str) -> str:
    sentences = re.split(r"(?<=[.?!:])\s+(?=[A-Z\"(])", paragraph)
    for s in sentences:
        if bold.lower() in s.lower():
            return s
    return paragraph


def gold_from_latex(tex: str, book: str) -> tuple[list[GoldItem], dict[str, int]]:
    """Definition questions with gold passages, plus counts of what was dropped.

    A glossary term becomes a question only if the chapter body sets that same
    term (or its plural) in bold; the first such paragraph is the gold passage.
    Terms defined only in the glossary are dropped and counted.
    """
    items: list[GoldItem] = []
    stats = {"glossary_terms": 0, "no_bold_in_body": 0}
    for number, (title, body) in enumerate(_split_chapters(tex), start=1):
        glossary = _glossary(body)
        stats["glossary_terms"] += len(glossary)
        prose = _body_without(body, ("Glossary", "Exercises"))
        prose = re.sub(
            r"\\begin\{(verbatim|code|stdout)\}.*?\\end\{\1\}", "\n\n", prose, flags=re.S
        )
        paragraphs = [p for p in re.split(r"\n\s*\n", prose) if "\\bf" in p]
        for k, (term, definition) in enumerate(glossary):
            variants = _term_variants(term)
            found = None
            for para in paragraphs:
                for bold in re.findall(r"\{\\bf\s+([^{}]*)\}", para):
                    if detex(bold).lower().strip() in variants:
                        found = (para, detex(bold))
                        break
                if found:
                    break
            if found is None:
                stats["no_bold_in_body"] += 1
                continue
            passage = detex(found[0])
            items.append(
                GoldItem(
                    qid=f"{book}-{number:02d}-{k:02d}",
                    book=book,
                    chapter=number,
                    chapter_title=title,
                    term=term,
                    definition=definition,
                    gold_passage=passage,
                    gold_sentence=_sentence_with(passage, found[1]),
                )
            )
    return items, stats
