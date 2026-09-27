"""Scoring: extraction fidelity, structure accuracy, evidence retrieval."""

from __future__ import annotations

import random
import re
import textwrap
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from booktoskill.layout import LIGATURES

# Typographic variants that differ between a PDF and an HTML rendering of the
# same source without either being an extraction error.
_RENDER_EQUIV = str.maketrans(
    {
        chr(0x2018): "'",
        chr(0x2019): "'",
        chr(0x201C): '"',
        chr(0x201D): '"',
        chr(0x2013): "-",
        chr(0x2014): "-",
        chr(0x2212): "-",
        chr(0x00A0): " ",
        chr(0x2022): " ",
    }
)
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def render_normalise(text: str) -> str:
    """Unify quote/dash rendering only. Ligatures are deliberately left alone:
    a ligature glyph in extracted text is an extraction error being measured."""
    return unicodedata.normalize("NFC", text).translate(_RENDER_EQUIV)


def tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(render_normalise(text))


@dataclass(frozen=True)
class Fidelity:
    precision: float
    recall: float
    f1: float
    ref_tokens: int
    out_tokens: int


def fidelity(extracted: str, reference: str) -> Fidelity:
    """Order-aware token overlap between extracted text and a reference text.

    Matched tokens are those in the longest common subsequence blocks found by
    difflib, so text that is present but scrambled or split does not count.
    """
    a, b = tokens(extracted), tokens(reference)
    if not a or not b:
        return Fidelity(0.0, 0.0, 0.0, len(b), len(a))
    matched = sum(m.size for m in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    p, r = matched / len(a), matched / len(b)
    f = 2 * p * r / (p + r) if p + r else 0.0
    return Fidelity(p, r, f, len(b), len(a))


def defect_counts(text: str, reference_vocab: set[str]) -> dict[str, int]:
    """Counts of the specific artefacts layout repair targets."""
    norm = render_normalise(text)
    words = re.findall(r"[A-Za-z]+", norm)
    lig = sum(norm.count(ch) for ch in LIGATURES)
    broken = 0
    for m in re.finditer(r"\b([A-Za-z]{2,})-\s+([a-z]{2,})\b", norm):
        if (m.group(1) + m.group(2)).lower() in reference_vocab:
            broken += 1
    glued = 0
    for w in words:
        lw = w.lower()
        if len(lw) < 7 or lw in reference_vocab:
            continue
        if any(
            lw[:i] in reference_vocab and lw[i:] in reference_vocab for i in range(3, len(lw) - 2)
        ):
            glued += 1
    return {"ligature_glyphs": lig, "broken_hyphenations": broken, "glued_words": glued}


def _code_lines(text: str) -> str:
    return "\n".join(line.rstrip() for line in render_normalise(text).splitlines())


def code_block_recovery(extracted: str, reference_blocks: Sequence[str]) -> dict[str, float]:
    """Share of the reference's multi-line code blocks found verbatim.

    Verbatim means every line, with its indentation relative to the block,
    in order and contiguous (a listing indented as a whole inside a list item
    is compared dedented). Reported separately for blocks with indentation
    inside them, which is what a plain text dump loses.
    """
    haystack = _code_lines(extracted)
    multi = [textwrap.dedent(b).strip("\n") for b in reference_blocks if b.strip().count("\n")]
    indented = [b for b in multi if any(ln.startswith(" ") for ln in b.splitlines()[1:])]

    def rate(blocks: Sequence[str]) -> float:
        if not blocks:
            return 0.0
        return sum(_code_lines(b) in haystack for b in blocks) / len(blocks)

    return {
        "blocks": len(multi),
        "indented_blocks": len(indented),
        "exact": round(rate(multi), 4),
        "exact_indented": round(rate(indented), 4),
    }


def vocabulary(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z]+", render_normalise(text))}


# ------------------------------------------------------------------ structure


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", render_normalise(title).lower())


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    predicted: int
    gold: int


def prf(predicted: Sequence[str], gold: Sequence[str]) -> PRF:
    """Set precision/recall over normalised titles (multiset-aware)."""
    remaining = list(gold)
    tp = 0
    for p in predicted:
        if p in remaining:
            remaining.remove(p)
            tp += 1
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PRF(precision, recall, f1, tp, len(predicted), len(gold))


# ------------------------------------------------------------------ retrieval


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def evidence_words(text: str) -> list[str]:
    """Lower-cased words with ligatures expanded, for evidence matching only."""
    for glyph, repl in LIGATURES.items():
        text = text.replace(glyph, repl)
    return re.findall(r"[a-z0-9]+", render_normalise(text).lower())


def evidence_coverage(unit: str, gold_sentence: str, n: int = 3) -> float:
    """Share of the gold sentence's word n-grams present in ``unit``."""
    g = evidence_words(gold_sentence)
    if len(g) < n:
        n = max(1, len(g))
    grams = _ngrams(g, n)
    if not grams:
        return 0.0
    return len(grams & _ngrams(evidence_words(unit), n)) / len(grams)


def contains_evidence(unit: str, gold_sentence: str, threshold: float = 0.6) -> bool:
    return evidence_coverage(unit, gold_sentence) >= threshold


def bootstrap_ci(
    values: Sequence[float], n_boot: int = 2000, seed: int = 0, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of ``values``."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    samples = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    lo = samples[int(alpha / 2 * n_boot)]
    hi = samples[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (lo, hi)


EVIDENCE_THRESHOLD = 0.6


def gram_set(text: str, n: int = 3) -> frozenset[tuple[str, ...]]:
    """The word n-grams of ``text`` after evidence normalisation."""
    return frozenset(_ngrams(evidence_words(text), n))


@dataclass(frozen=True)
class Evidence:
    """Gold evidence as precomputed trigram sets, one per acceptable sentence.

    A unit holds the evidence when it contains at least ``EVIDENCE_THRESHOLD``
    of the trigrams of any one gold sentence: the same rule as
    :func:`contains_evidence`, computed once per sentence instead of per call.
    Sentences shorter than three words have no trigrams and are ignored.
    """

    grams: tuple[frozenset[tuple[str, ...]], ...]

    @classmethod
    def of(cls, sentences: Sequence[str]) -> Evidence:
        return cls(tuple(g for s in sentences if (g := gram_set(s))))

    def coverage(self, unit: frozenset[tuple[str, ...]]) -> float:
        return max((len(g & unit) / len(g) for g in self.grams), default=0.0)

    def found(
        self, unit: frozenset[tuple[str, ...]], threshold: float = EVIDENCE_THRESHOLD
    ) -> bool:
        return any(len(g & unit) >= threshold * len(g) for g in self.grams)

    def found_in(self, text: str) -> bool:
        return self.found(gram_set(text))


def cluster_bootstrap_ci(
    values: Sequence[float],
    clusters: Sequence[str],
    n_boot: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Bootstrap interval for the mean, resampling whole clusters (e.g. chapters).

    Questions from one chapter share its skill file, so they are not
    independent; resampling chapters gives the honest, wider interval.
    """
    groups: dict[str, list[float]] = {}
    for v, c in zip(values, clusters, strict=True):
        groups.setdefault(c, []).append(v)
    if not groups:
        return (0.0, 0.0)
    keys = sorted(groups)
    rng = random.Random(seed)
    samples = []
    for _ in range(n_boot):
        picked = [groups[keys[rng.randrange(len(keys))]] for _ in keys]
        total = sum(sum(g) for g in picked)
        count = sum(len(g) for g in picked)
        samples.append(total / count)
    samples.sort()
    return samples[int(alpha / 2 * n_boot)], samples[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
