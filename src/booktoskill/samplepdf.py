"""Write small, fully controlled PDFs (used by demo.py and the tests).

Three Type 1 fonts are declared with explicit width tables: a proportional
roman and bold (widths vary by character, so they are not mistaken for
monospace) and a monospaced Courier. Text is placed with exactly those
widths, so the geometry the pipeline reads back is known.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

FIRST, LAST = 32, 126


def prop_width(code: int) -> int:
    if code == 32:
        return 250
    return 400 + (code % 7) * 50


FONTS = {
    "R": ("Helvetica", [prop_width(c) for c in range(FIRST, LAST + 1)]),
    "B": ("Helvetica-Bold", [prop_width(c) + 20 for c in range(FIRST, LAST + 1)]),
    "M": ("Courier", [600] * (LAST - FIRST + 1)),
}


def text_width(font: str, text: str, size: float) -> float:
    widths = FONTS[font][1]
    return sum(widths[ord(ch) - FIRST] for ch in text) * size / 1000


@dataclass
class Run:
    font: str
    size: float
    x: float
    y: float
    text: str


@dataclass
class PageSpec:
    runs: list[Run] = field(default_factory=list)
    figure: list[Run] = field(default_factory=list)  # drawn inside a form XObject

    def line(
        self,
        y: float,
        parts: list[tuple[str, str]],
        size: float = 10,
        x: float = 72,
        space_between: bool = True,
    ) -> PageSpec:
        """Place ``(font, text)`` parts left to right on one baseline.

        A word space (0.25 em) separates parts unless the next part starts
        with punctuation or ``space_between`` is False.
        """
        cursor = x
        for i, (font, text) in enumerate(parts):
            if i and space_between and text[:1] not in ".,;:)":
                cursor += 0.25 * size
            self.runs.append(Run(font, size, cursor, y, text))
            cursor += text_width(font, text, size)
        return self


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _stream(runs: list[Run]) -> str:
    ops = []
    for r in runs:
        ops.append(
            f"BT /F{r.font} {r.size} Tf 1 0 0 1 {r.x:.2f} {r.y:.2f} Tm ({_esc(r.text)}) Tj ET"
        )
    return "\n".join(ops)


def write_pdf(path: str | Path, pages: list[PageSpec], title: str | None = None) -> Path:
    objects: list[str] = []

    def add(body: str) -> int:
        objects.append(body)
        return len(objects)

    catalog = add("")  # filled in below
    pages_obj = add("")
    font_ids = {}
    for key, (base, widths) in FONTS.items():
        font_ids[key] = add(
            f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /FirstChar {FIRST} "
            f"/LastChar {LAST} /Widths [{' '.join(map(str, widths))}] "
            "/Encoding /WinAnsiEncoding >>"
        )
    fonts = " ".join(f"/F{k} {v} 0 R" for k, v in font_ids.items())
    kids = []
    for spec in pages:
        xobjects = ""
        content = _stream(spec.runs)
        if spec.figure:
            form = _stream(spec.figure)
            form_id = add(
                f"<< /Type /XObject /Subtype /Form /BBox [0 0 612 792] "
                f"/Resources << /Font << {fonts} >> >> /Length {len(form)} >>\n"
                f"stream\n{form}\nendstream"
            )
            xobjects = f"/XObject << /Fm1 {form_id} 0 R >>"
            content += "\nq 1 0 0 1 0 0 cm /Fm1 Do Q"
        content_id = add(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")
        kids.append(
            add(
                f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << {fonts} >> {xobjects} >> /Contents {content_id} 0 R >>"
            )
        )
    objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>"
    objects[pages_obj - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
    )
    info = add(f"<< /Title ({_esc(title)}) >>") if title else None

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    trailer = f"<< /Size {len(objects) + 1} /Root {catalog} 0 R"
    if info:
        trailer += f" /Info {info} 0 R"
    out += f"trailer\n{trailer} >>\nstartxref\n{xref}\n%%EOF\n".encode()
    Path(path).write_bytes(bytes(out))
    return Path(path)


def tiny_book() -> list[PageSpec]:
    """A six-page book whose correct extraction is known exactly."""
    p0 = PageSpec().line(600, [("B", "A Tiny Book")], size=28)

    p1 = PageSpec()
    p1.line(650, [("B", "Chapter 1")], size=20)
    p1.line(610, [("B", "Getting Started")], size=24)
    p1.line(560, [("R", "This book is a small test of the whole pipeline. A variable is")])
    p1.line(546, [("R", "a name that refers to a value. The interpreter reads each line")])
    p1.line(532, [("R", "and runs it.")])
    p1.line(490, [("B", "1.1 Assignment")], size=14)
    p1.line(460, [("R", "Programmers write assign-")])
    p1.line(446, [("R", "ments all the time. A well-known idiom is shown below:")])
    p1.line(420, [("M", "def double(x):")])
    p1.line(408, [("M", "return 2 * x")], x=72 + 4 * 6)
    p1.line(380, [("R", "Call it with"), ("M", "double(21)"), ("R", "to get 42.")])

    p2 = PageSpec()
    p2.line(750, [("B", "2 Chapter 1. Getting Started")])
    p2.line(700, [("R", "An expression is a combination of values and operators. Each")])
    p2.line(686, [("R", "expression has a value, and the interpreter can evaluate it for")])
    p2.line(672, [("R", "you. A statement is called a unit of code that has an effect.")])
    p2.line(630, [("B", "1.2 Glossary")], size=14)
    p2.line(600, [("B", "variable:"), ("R", "A name that refers to a value.")])
    p2.figure.append(Run("R", 8, 100, 300, "fig label 42"))

    p3 = PageSpec()
    p3.line(750, [("B", "1.2. Glossary 3")])
    p3.line(650, [("B", "Chapter 2")], size=20)
    p3.line(610, [("B", "Next Steps")], size=24)
    p3.line(560, [("R", "This chapter introduces loops and functions, the two ideas")])
    p3.line(546, [("R", "that every later chapter depends on.")])
    p3.line(500, [("B", "2.1 Loops")], size=14)
    p3.line(
        470, [("R", "Use the"), ("M", "print"), ("R", "function inside a loop to show progress.")]
    )
    p3.line(456, [("R", "A loop that never ends is called an infinite loop.")])

    p4 = PageSpec()
    p4.line(750, [("B", "4 Chapter 2. Next Steps")])
    p4.line(700, [("R", "Loops can also be nested inside each other, which is common when")])
    p4.line(686, [("R", "processing tables of data.")])
    p4.line(640, [("B", "2.2 Functions")], size=14)
    p4.line(610, [("R", "A function is a named sequence of statements that performs a")])
    p4.line(596, [("R", "computation. Short functions are a well-")])
    p4.line(582, [("R", "known way to make programs easier to test.")])

    p5 = PageSpec()
    p5.line(750, [("B", "2.2. Functions 5")])
    p5.line(700, [("R", "A well-known rule: write small functions that each do one thing.")])
    return [p0, p1, p2, p3, p4, p5]
