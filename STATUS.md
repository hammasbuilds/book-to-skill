# STATUS

**READY-FOR-MODEL-RUN**: everything that needs no model is built, measured and reproducible
from a clean clone. The answer-accuracy arm is built, tested end to end with a fake
transport, and queued.

## Review round 1 (independent review: 77/100) and what changed

| # | Reviewer finding | Fix | Regression test |
|---|---|---|---|
| 1 | "No-definitions skill below random" was a budget artefact (random at the full skill's budget, seed 0 only) | Random control built at each variant's own budget, 20 seeds, mean/sd/min/max reported (`controls`). The ablation is at chance (21.8% vs 20.4%, sd 2.6); full-budget control is 27.3% (sd 2.4), not 29.8%. README claim rewritten, with a correction note | `test_random_control_uses_each_variants_own_budget`, `test_controls_and_counts_are_summarised_over_seeds` |
| 2 | Retrieval units not comparable (44-word "200-word" skill chunks; top-5 of 148-word vs 659-word units) | `chunk_markdown` packs across headings like book chunks (skill chunks now 163 words vs book 148). New metric: recall within the first N words read (N = 250/500/1000/2000, crossing unit truncated); headline is recall@1000 words | `test_chunk_markdown_packs_across_headings_like_book_chunks`, `test_chunk_markdown_keeps_fenced_code_whole`, `test_budget_hits_truncates_the_crossing_unit` |
| 3 | Definitions regex is a proxy for the bold gold rule | Reported: 38.8% of gold vs 4.8% of book sentences match (8x). Retention split by match: 93.8% matched; 26.0% unmatched vs random 25.6% (sd 2.5). README states plainly the regex partly reproduces the gold rule and the headline is "a definitions section finds definitions". A non-glossary question set was judged not feasible in this round and is listed as a weakness | `test_definition_rule_overlap_counts_regex_matches` |
| 4 | One stray numbered heading disabled chapter numbering (thesis → one-file skill, exit 0) | Numbering is trusted only if at least half of chapter-like headings (2+ sections) carry numbers and stray numbers don't outnumber them; otherwise the book is renumbered. `convert` exits 3 with an explanation when numbered chapters hold <20% of the text (`--allow-low-coverage` to override); `inspect` prints the coverage. The thesis PDF was not in the review folder, so a synthetic equivalent is used | `test_one_stray_number_does_not_disable_chapter_numbering`, `test_convert_writes_every_chapter_of_the_thesis` (both fail on the old code), `test_convert_without_chapters_explains` |
| 5 | UnicodeEncodeError on non-ASCII titles when piped on Windows | `stdout`/`stderr` reconfigured with `errors="replace"` | `test_non_ascii_title_on_a_legacy_console` |
| 6 | README samples silently trimmed | All six samples regenerated and pasted verbatim by a script; every cut is marked `[...]` and described | (checked by hand) |
| 7 | `examples/` not the evaluated skill; "references/" count included SKILL.md; ">100% kept" | Examples rebuilt with `--exclude-section Glossary` (reference words 13,400 / 9,679 = `books.json`); output now lists SKILL.md and references separately and prints a ratio, not "% kept" | `test_convert_reports_ratio_and_writes_licence` |
| 8 | `model_arm.run()`, `plan()`, `cmd_model_arm` untested | `tests/test_model_arm_run.py`: run() and plan() on a two-chapter PDF + LaTeX with a fake transport (every planned request is a call or a cache hit; a second run makes no calls), CLI dry run, CLI run with a faked Ollama, refusal when the model isn't pulled. The old "estimate equals calls" claim was wrong (identical prompts are cached) and is now stated as an upper bound | 5 tests |
| 9 | CLI: negative/zero `-k`, `inspect --exclude-section` no-op, directory = "no such file", junk metadata titles, model-arm help | `-k`/`--chunk-words` must be ≥ 1; `inspect` has no exclude option; directories reported as such; metadata titles that look like file names / "Untitled" / "Microsoft Word - x" fall back to the title page's heading; every model-arm option has help | `test_search_rejects_non_positive_k`, `test_inspect_has_no_exclude_option`, `test_directory_is_reported_as_directory`, `test_junk_metadata_titles` (7 cases), `test_junk_metadata_falls_back_to_title_page` |
| 10 | Licence of CC BY-NC extracts | `examples/NOTICE`, `results/NOTICE`; `convert --license` writes a `license:` frontmatter field and an attribution line in SKILL.md | `test_convert_reports_ratio_and_writes_licence` |
| — | `build_blocks` 119 lines; unused `stat` param | Split into `_leading`, `_Assembler` (classify / new-block / inline-code / flush) and `_text_repairs`; `build_blocks` is 14 lines. `stat` removed | existing layout tests |

## Self-score (after round 1)

| Points | Criterion | Score | Reason |
|---:|---|---:|---|
| 15 | Works from a clean clone | 15 | Fresh clone: `uv sync`, `uv run pytest -q` (122 passed), `uv run python demo.py` (10/10), `ruff check` and `ruff format --check` pass. Tests build their own PDFs and LaTeX; nothing reads `data/`, the network or a model. `experiments` reran on the final code in 13.5 minutes. |
| 20 | Real data, real result | 15 | Three real books, 289 questions, every README number in `results/`. Capped: the answer-accuracy headline needs the model arm; and the retention headline, once split by the regex, says the skill is at chance outside definition-shaped questions. |
| 15 | Finding quality | 11 | Budget-matched controls over 20 seeds with spread, ablations, equal-words retrieval, per-repair ablations, paired bootstrap CIs, threshold sensitivity, a third toolchain. Held back: the question set and the skill writer share a proxy (8x enrichment) and no independent question set exists; the model arm is unrun. |
| 15 | Correctness | 13 | 122 tests including regressions for every reviewer finding. The review found real bugs (stray-number structure failure, Unicode crash, budget-mismatched control, misleading chunk sizes), so structure detection on unseen toolchains should be assumed fragile; the coverage guard makes that failure loud instead of silent. |
| 10 | Usability | 9 | Five subcommands with help on every option, input validation, one-line errors, exit 3 on low coverage, progress lines. `experiments` takes ~14 minutes. |
| 10 | README | 9 | House skeleton, six verbatim samples with marked cuts, NOT-do, problems hit including the review's findings, correction note on the retracted claim. |
| 10 | Code quality | 9 | ruff clean, typed, `build_blocks` split, no unused parameters found. `experiments.py` is the largest module (~700 lines) and mixes experiments with result writing. |
| 5 | Honesty | 5 | Every README number re-checked against `results/` after the rerun; the earlier wrong claims are corrected in place and named as corrections. |
| **100** | | **86** | Capped by the unrun model arm and by the proxy overlap in the question set. |

## Done

- PDF reading from pypdf's content-stream visitor: positioned runs, rendered sizes, form
  XObject (figure) flag, widths read through each font's ToUnicode CMap, monospace decided
  from the widths of letters actually drawn, with family inheritance.
- Layout repair, each switchable: figure text, running headers/footers and page numbers,
  geometric word spacing, code blocks with indentation and blank lines, paragraph reflow,
  de-hyphenation with a per-book prior, ligatures, kerning splits.
- Structure from font sizes, "Chapter N" labels, numbering for books that print none and
  for books where stray numbers would mislead; coverage guard in `convert`.
- Chunking (book and skill packed the same way), BM25 from scratch, the extractive skill
  writer with an optional licence/attribution field.
- References: hevea and Asciidoctor HTML editions; the LaTeX glossary question set.
- Experiments: extraction F1 / defects / code recovery (3 books x 10 systems); structure
  (3 books x 3 methods); evidence retention and recall@{1,3,5,10} and recall@{250,500,1000,2000}
  words for 6 corpora x 2 query forms; budget-matched random controls (20 seeds) for the skill
  and its ablation; the definitions-regex overlap and split; threshold sensitivity.
- Model arm: Ollama client with atomic disk cache, fake client, model reference writer at
  the extractive word budget, routing, four conditions x two skills, judge, token F1,
  `scripts/run_models.sh` with RAM/VRAM/Ollama checks and `--dry-run`.

## Queued for the model run

`bash scripts/run_models.sh` (never executed). Dry run (an upper bound: identical prompts
are generated once and served from the cache):

| Book | Skill generation | Questions | QA requests | Requests |
|---|---:|---:|---:|---:|
| Think Python 2e | 21 | 184 | 2,576 | 2,597 |
| Think Stats 2e | 14 | 105 | 1,470 | 1,484 |
| **Total** | 35 | 289 | 4,046 | **4,081** |

Per question: 8 answer/route requests and 6 judge requests. At most about 6.8 hours at 6 s
per call; an interrupted run resumes. Writes `results/model_arm.json`,
`results/model_outcomes.jsonl` and the model-written skills to `out/skills/llm/`.

## Known weaknesses remaining

- **The model arm has not run**: no answer-accuracy number, no model-written-skill retention.
- **The question set shares a proxy with the skill writer** (bold terms vs a defining-phrase
  regex, 8x enrichment). The split is reported; a question set not derived from glossaries
  (e.g. exercises with published solutions) is not built.
- **The judge is the answering model** by default. Token F1 is reported alongside;
  `--judge-model` can point elsewhere.
- **Two of the three books share an author, template and pdflatex**; the structure fallback
  was only exercised on a synthetic thesis, not the reviewer's real one (not provided).
- **Residual extraction defects**: `2 π` spacing, column alignment inside one pypdf run of
  code, interleaved two-column index pages, tables and display maths.
- **`section_parent_accuracy` is 1.0 almost everywhere** and is not used as evidence.

## Reproduce every result

```bash
unset VIRTUAL_ENV
uv sync
bash scripts/fetch_data.sh             # data/raw/, verified against data/MANIFEST.sha256
uv run book-to-skill experiments       # results/*.json, results/questions.jsonl, results/NOTICE (~14 min)
uv run pytest -q
uv run python demo.py

# README Input/Output samples
uv run python scripts/before_after.py  # samples 2 and 3
uv run book-to-skill inspect data/raw/progit.pdf
uv run book-to-skill search data/raw/thinkpython2.pdf "What is an accumulator?" -k 3
LIC="Allen B. Downey, Green Tea Press, CC BY-NC 3.0 (https://creativecommons.org/licenses/by-nc/3.0/)"
uv run book-to-skill convert data/raw/thinkpython2.pdf --title "Think Python 2e" \
  --exclude-section Glossary --license "$LIC" --out examples
uv run book-to-skill convert data/raw/thinkstats2.pdf --title "Think Stats 2e" \
  --exclude-section Glossary --license "$LIC" --out examples

# model arm (GPU + Ollama with qwen2.5:14b-instruct)
bash scripts/run_models.sh --dry-run
bash scripts/run_models.sh
```
