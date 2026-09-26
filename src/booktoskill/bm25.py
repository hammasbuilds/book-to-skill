"""Okapi BM25, from scratch, over any list of text units."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

_STOPWORD_TEXT = """
a about above after again against all am an and any are as at be because been before
being below between both but by can could did do does doing down during each few for
from further had has have having he her here hers herself him himself his how i if in
into is it its itself just me more most my myself no nor not now of off on once only or
other our ours ourselves out over own same she should so some such than that the their
theirs them themselves then there these they this those through to too under until up
very was we were what when where which while who whom why will with would you your yours
yourself yourselves
"""
STOPWORDS = frozenset(_STOPWORD_TEXT.split())
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """A deliberately light suffix stripper: plurals and a few verb endings."""
    for suffix, repl in (("ies", "y"), ("sses", "ss"), ("es", "e"), ("s", "")):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            if suffix == "s" and word.endswith(("ss", "us", "is")):
                break
            return word[: len(word) - len(suffix)] + repl
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


@dataclass(frozen=True)
class Hit:
    index: int
    score: float


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        if not docs:
            raise ValueError("BM25 needs at least one document")
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lengths = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = (sum(self.lengths) / len(docs)) or 1.0
        df: Counter[str] = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def score(self, query: str) -> list[float]:
        terms = [t for t in tokenize(query) if t in self.idf]
        out = []
        for tf, length in zip(self.tfs, self.lengths, strict=True):
            s = 0.0
            norm = self.k1 * (1 - self.b + self.b * length / self.avgdl)
            for t in terms:
                f = tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out

    def search(self, query: str, k: int = 10) -> list[Hit]:
        scores = self.score(query)
        # Ties break by position so results are deterministic.
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        return [Hit(i, scores[i]) for i in order[:k] if scores[i] > 0]
