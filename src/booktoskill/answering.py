"""The model arm's question answering: skill-in-context vs RAG vs both.

Conditions, all answering the same definition questions with the glossary
held out of every context:

* ``closed_book`` - no context; measures what the model already knows.
* ``rag`` - the top-k BM25 chunks of the repaired book text.
* ``skill`` - the agent reads SKILL.md, names one reference file, then answers
  with that file in context (two calls, as a skill-using agent would).
* ``both`` - the chosen reference file plus the top-k chunks.

Answers are graded two ways: token F1 against the glossary definition (no
model) and a model judge that compares meaning with the definition.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from booktoskill.bm25 import BM25, tokenize
from booktoskill.chunking import Chunk
from booktoskill.llm import Client
from booktoskill.references import GoldItem
from booktoskill.skill import SkillPackage

CONDITIONS = ("closed_book", "rag", "skill", "both")

ANSWER_SYSTEM = (
    "You answer questions about a technical book. Answer in one or two sentences. "
    "If context is given, base the answer on it."
)
ROUTE_PROMPT = """{skill_md}

Question: {question}

Which reference file should be read to answer this question? Reply with the file
path exactly as written in the table, and nothing else."""
ANSWER_PROMPT = """{context}Question: {question}
Answer:"""
JUDGE_SYSTEM = "You grade answers against a reference definition. Reply with one word."
JUDGE_PROMPT = """Term: {term}
Reference definition: {definition}
Candidate answer: {answer}

Does the candidate answer state the same meaning as the reference definition?
It may use different words or add correct detail. Reply CORRECT or INCORRECT."""


def question(item: GoldItem) -> str:
    return f'In the book, what is meant by "{item.term}"?'


def route(client: Client, pkg: SkillPackage, item: GoldItem) -> tuple[str, bool]:
    """Ask the model which reference file to open. Returns (file, parsed_ok).

    An unparseable reply falls back to the first file, and is counted, so a
    routing failure costs the skill condition rather than being hidden.
    """
    reply = client.generate(ROUTE_PROMPT.format(skill_md=pkg.skill_md, question=question(item)))
    for fname in pkg.references:
        if fname in reply or fname.rsplit("/", 1)[-1] in reply:
            return fname, True
    return next(iter(pkg.references)), False


def rag_context(index: BM25, chunks: list[Chunk], item: GoldItem, k: int) -> str:
    hits = index.search(question(item), k=k)
    return "\n\n---\n\n".join(chunks[h.index].text for h in hits)


def answer(client: Client, context: str, item: GoldItem) -> str:
    block = f"Context:\n{context}\n\n" if context else ""
    return client.generate(
        ANSWER_PROMPT.format(context=block, question=question(item)), ANSWER_SYSTEM
    ).strip()


def judge(client: Client, item: GoldItem, reply: str) -> bool:
    verdict = client.generate(
        JUDGE_PROMPT.format(term=item.term, definition=item.definition, answer=reply),
        JUDGE_SYSTEM,
    )
    words = re.findall(r"[A-Z]+", verdict.upper())
    return bool(words) and words[0] == "CORRECT"


def token_f1(prediction: str, reference: str) -> float:
    p, r = Counter(tokenize(prediction)), Counter(tokenize(reference))
    overlap = sum((p & r).values())
    if not overlap:
        return 0.0
    precision, recall = overlap / sum(p.values()), overlap / sum(r.values())
    return 2 * precision * recall / (precision + recall)


@dataclass(frozen=True)
class Outcome:
    qid: str
    skill_variant: str
    condition: str
    answer: str
    correct: bool
    f1: float
    routed_file: str = ""
    routed_ok: bool = True
    routed_to_gold_chapter: bool = False
    correct_second_judge: bool | None = None  # None: no second judge was run


def run_item(
    client: Client,
    judge_client: Client,
    item: GoldItem,
    skills: dict[str, SkillPackage],
    index: BM25,
    chunks: list[Chunk],
    k: int = 5,
    second_judge: Client | None = None,
) -> list[Outcome]:
    """Every condition for one question. Closed-book and RAG do not depend on
    the skill, so they are run once and recorded under variant ``-``.

    ``second_judge``, a model from another family, grades every answer again so
    the agreement between the two judges can be reported.
    """
    out: list[Outcome] = []

    def grade(variant: str, condition: str, reply: str, routed: tuple[str, bool, bool]) -> None:
        correct = judge(judge_client, item, reply)
        second = judge(second_judge, item, reply) if second_judge is not None else None
        f1 = token_f1(reply, item.definition)
        out.append(Outcome(item.qid, variant, condition, reply, correct, f1, *routed, second))

    retrieved = rag_context(index, chunks, item, k)
    no_route = ("", True, False)
    grade("-", "closed_book", answer(client, "", item), no_route)
    grade("-", "rag", answer(client, retrieved, item), no_route)
    for variant, pkg in skills.items():
        fname, ok = route(client, pkg, item)
        routed = (fname, ok, fname == pkg.chapter_files.get(str(item.chapter), ""))
        ref = pkg.references[fname]
        grade(variant, "skill", answer(client, ref, item), routed)
        both = f"{ref}\n\n---\n\n{retrieved}"
        grade(variant, "both", answer(client, both, item), routed)
    return out


def calls_per_item(n_skills: int, judges: int = 1) -> dict[str, int]:
    """Model calls one question costs, for the dry-run estimate."""
    answers = 2 + 3 * n_skills  # closed, rag; per skill: route, skill, both
    judged = (2 + 2 * n_skills) * judges
    return {"answer_and_route": answers, "judge": judged, "total": answers + judged}
