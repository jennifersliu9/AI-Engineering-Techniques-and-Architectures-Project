"""Refuse out-of-corpus questions and keep answers inside retrieved policy."""

from __future__ import annotations

import re

from harborline.retrieve import Hit

OUT_OF_SCOPE = re.compile(
    r"\b(stock tip|buy bitcoin|crypto|medical diagnos|prescribe|other employer|"
    r"acme corp|google's pto|apple's|lawsuit against harborline|who should I vote|"
    r"write my performance review for me)\b",
    re.I,
)

REFUSAL = (
    "I can only answer from Harborline's published policies and HarborHub records "
    "in this project. That question is outside the corpus. Try a topic such as PTO, "
    "holidays, remote work, expenses, security, benefits, onboarding, equipment, "
    "leave, or workplace conduct, or ask People Operations at hr@harborline.example."
)

WEAK_MATCH = (
    "The retrieved policies are too weakly related to answer this from the corpus. "
    "I will not guess. Rephrase using Harborline terms (PTO, hub, Voyage, FMLA) "
    "or name a policy ID such as POL-PTO-001."
)


def is_out_of_scope(query: str) -> bool:
    return bool(OUT_OF_SCOPE.search(query))


def max_score(hits: list[Hit]) -> float:
    return max((h.score for h in hits), default=0.0)


def apply_guardrails(
    query: str,
    hits: list[Hit],
    min_score: float,
) -> tuple[bool, str | None]:
    """Return (ok, refusal_message)."""
    if is_out_of_scope(query):
        return False, REFUSAL
    if not hits:
        return False, WEAK_MATCH
    if max_score(hits) < min_score:
        return False, WEAK_MATCH
    return True, None
