"""Print Input/Output samples 2 and 3 of the README: pypdf text vs book-to-skill.

uv run python scripts/before_after.py
"""

from booktoskill.pipeline import convert, plain_page_texts

tp = "data/raw/thinkpython2.pdf"
plain = plain_page_texts(tp)
print("=== pypdf extract_text(), Think Python PDF page 34 (index 33), first 12 lines")
print("\n".join(plain[33].splitlines()[:12]))
conv = convert(tp, title="Think Python 2e")
print("=== book-to-skill, same page, first blocks")
for b in [b for b in conv.blocks if b.page == 33][:4]:
    print(f"[{b.kind}] {b.text}")

ts = "data/raw/thinkstats2.pdf"
plain = plain_page_texts(ts)
page = next(i for i, t in enumerate(plain) if "def MakePregMap" in t)
lines = plain[page].splitlines()
k = next(i for i, ln in enumerate(lines) if "def MakePregMap" in ln)
print(f"=== pypdf extract_text(), Think Stats PDF page {page + 1}")
print("\n".join(lines[k : k + 5]))
conv = convert(ts, title="Think Stats 2e")
print("=== book-to-skill, same listing")
print(next(b.text for b in conv.blocks if b.kind == "code" and "def MakePregMap" in b.text))
