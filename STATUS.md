# STATUS

**READY-FOR-MODEL-RUN** — everything that needs no model is built, measured and reproducible
from a clean clone; the answer-accuracy arm is built, tested with a fake client and queued.

## Self-score

| Points | Criterion | Score | Reason |
|---:|---|---:|---|
| 15 | Works from a clean clone | 15 | Fresh `git clone` + `uv sync` + `uv run pytest -q` (96 passed) + `uv run python demo.py` (10/10) + `ruff check` / `ruff format --check` all pass. Tests build their own PDFs; nothing reads `data/`, the network or a model. With `data/raw` copied in and verified against `data/MANIFEST.sha256`, `book-to-skill experiments` in the clone reproduces the committed `results/` byte for byte (see below). |
| 20 | Real data, real result | 16 | Three real books (two CC BY-NC LaTeX books with 289 questions, Pro Git as a non-LaTeX control), every README number in `results/`. Capped: the headline the brief asks for last (answer accuracy of skill vs RAG vs both) needs the model arm. |
| 15 | Finding quality | 12 | Controls and ablations: random sentences at the same word budget (5 seeds), the skill without its definitions section, every repair switched off one at a time, pypdf's own text, the PDF outline for structure, a third book from another toolchain. Paired bootstrap CIs over questions and chapters; threshold sensitivity; the 1.000 retention of book chunks traced to the question filter and labelled a construction check. Capped because the answer-accuracy comparison is not run, and because the question set is definitions only, which favours an extractive skill with a definitions section (stated). |
| 15 | Correctness | 14 | 96 tests on behaviour, edge cases and failure modes (known-geometry PDFs; CMap parsing; hyphenation prior on a ragged-right book; NBSP indentation; circled digits; corrupt, text-less, non-PDF and chapter-less inputs; the dry-run call estimate equals the calls a fake client receives). Known residual defects are listed below rather than fixed (`2 π`, in-line column alignment). |
| 10 | Usability | 9 | `convert / inspect / search / experiments / model-arm`, each with `--help`, sensible defaults and one-line errors (missing file, not a PDF, unreadable PDF, scanned PDF, no chapters, missing data, Ollama down or model not pulled). `experiments` takes about 12 minutes with one progress line per book. |
| 10 | README | 10 | House skeleton (centred title, thesis, nav, badges, mermaid + blockquote claim, findings table near the top, 6 real Input/Output samples, Quick start, Layout, Requirements, Tests, NOT-do, ten real problems hit, Keywords, License). British spelling. Inspiration credited in one line. |
| 10 | Code quality | 9 | ruff clean, typed, 15 small modules, one runtime dependency (pypdf), no dead code found on a final pass. `layout.build_blocks` is still the longest function (about 110 lines) even after extracting the paragraph-break rule. |
| 5 | Honesty | 5 | Every number in the README was checked against the results files after writing; wrong claims found on that pass were corrected (threshold sensitivity, sections lost without repair). Limitations and the untested toolchains are stated. |
| **100** | | **90** | Capped by the unrun model arm (−7) and small residual items (−3). |

## Done

- PDF reading from pypdf's content-stream visitor: positioned runs, rendered sizes, form
  XObject (figure) flag, widths read through each font's ToUnicode CMap, monospace decided
  from the widths of letters actually drawn with family inheritance.
- Layout repair, each switchable: figure text, running headers/footers and page numbers
  (page-offset + header band), geometric word spacing, code blocks with indentation and
  blank lines, paragraph reflow, de-hyphenation with a per-book prior, ligatures, kerning
  splits.
- Structure from font sizes, with "Chapter N" labels, labelled titles and numbering for books
  that print none; compared with the real TOC and the PDF outline.
- Chunking, BM25 from scratch, the extractive skill writer (SKILL.md with YAML frontmatter
  and a chapter index, per-chapter reference files with when-to-use topics, section
  summaries, key definitions and worked examples).
- References: hevea and Asciidoctor HTML editions; the LaTeX glossary question set (289
  questions, `results/questions.jsonl`).
- Experiments: extraction F1, defect counts and code-listing recovery vs the HTML editions
  for 3 books x 10 systems; structure P/R for 3 books x 3 methods; evidence retention and
  recall@{1,3,5,10} for 6 corpora x 2 query forms with bootstrap CIs and paired differences;
  random-budget control over 5 seeds; threshold sensitivity; code retention in the skill.
- Model arm: Ollama client with atomic disk cache, fake client, model reference writer at
  the extractive word budget, routing, four answering conditions x two skills, judge,
  token F1, summaries with paired differences vs RAG, `scripts/run_models.sh` with
  RAM/VRAM/Ollama checks and `--dry-run`.

## Queued for the model run

`bash scripts/run_models.sh` (never executed). Dry run:

| Book | Skill generation | Questions | QA calls | Calls |
|---|---:|---:|---:|---:|
| Think Python 2e | 21 | 184 | 2,576 | 2,597 |
| Think Stats 2e | 14 | 105 | 1,470 | 1,484 |
| **Total** | 35 | 289 | 4,046 | **4,081** |

Per question: 8 answer/route calls (closed book, RAG, and per skill: route, skill, both)
and 6 judge calls. About 6.8 hours at 6 s per call; cached calls are free, so an interrupted
run resumes. Writes `results/model_arm.json`, `results/model_outcomes.jsonl` and the
model-written skills to `out/skills/llm/`.

## Known weaknesses remaining

- **The model arm has not run**: no answer-accuracy number, no model-written-skill retention.
- **The judge is the answering model** (`qwen2.5:14b-instruct` grading itself). Token F1
  against the glossary definition is reported alongside as a model-free check;
  `--judge-model` can point at another model.
- **Definition questions only.** Easiest case for an extractive skill with a definitions
  section; the "without definitions" ablation (22%, below random 30%) suggests other
  question types would fare worse, but that is not measured.
- **Two of the three books share an author, a template and pdflatex.** Pro Git is the only
  other toolchain; Word/InDesign/Sphinx PDFs are untested.
- **Residual extraction defects**: a math-font glyph after a digit gets a space (`2 π`);
  column alignment inside one pypdf run of code is lost; two-column index pages interleave;
  display maths and tables lose structure.
- **`section_parent_accuracy` is 1.0 everywhere** (0.95 for Pro Git without repairs). It is
  near-automatic for books whose sections follow their chapters in order, so it is reported
  in `structure.json` but not used as evidence of anything.
- **Units differ in size between corpora** (200-word chunks, ~45-word skill chunks, whole
  chapter files). Evidence retention is size-independent and is the primary comparison;
  recall@k is reported for all three granularities.

## Reproduce every result

```bash
unset VIRTUAL_ENV
uv sync
bash scripts/fetch_data.sh             # data/raw/, verified against data/MANIFEST.sha256
uv run book-to-skill experiments       # results/{extraction,structure,retrieval,retrieval_pooled,books}.json
                                       # and results/questions.jsonl (about 12 minutes)
uv run pytest -q
uv run python demo.py

# README Input/Output samples
uv run python scripts/before_after.py  # samples 2 and 3
uv run book-to-skill inspect data/raw/progit.pdf
uv run book-to-skill inspect data/raw/thinkstats2.pdf --title "Think Stats 2e" --sections
uv run book-to-skill search data/raw/thinkpython2.pdf "What is an accumulator?" -k 3
uv run book-to-skill convert data/raw/thinkpython2.pdf --title "Think Python 2e" --out examples
uv run book-to-skill convert data/raw/thinkstats2.pdf --title "Think Stats 2e" --out examples

# model arm (GPU + Ollama with qwen2.5:14b-instruct)
bash scripts/run_models.sh --dry-run
bash scripts/run_models.sh
```
