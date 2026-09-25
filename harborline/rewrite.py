"""Deterministic query rewriting so short employee phrasing hits policy language."""

from __future__ import annotations

import re

# Expansions are applied as extra search terms, not replacements.
SYNONYMS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpto\b", re.I), "paid time off vacation POL-PTO-001 accrual"),
    (re.compile(r"\bvacation\b", re.I), "PTO paid time off"),
    (re.compile(r"\bhybrid\b|\bremote\b|\bwfh\b|\bwork from home\b", re.I),
     "hub office 50 miles POL-RMT-003"),
    (re.compile(r"\bholiday\b|\bthanksgiving\b", re.I),
     "company holiday floating POL-HOL-002"),
    (re.compile(r"\breceipt\b|\bexpense\b|\bhotel\b|\bper diem\b", re.I),
     "Voyage travel POL-EXP-004 meal cap"),
    (re.compile(r"\b401k\b|\b401\(k\)\b|\bmatch\b|\bvest", re.I),
     "retirement benefits POL-BEN-006"),
    (re.compile(r"\bparental\b|\bbonding\b|\bmaternity\b|\bpaternity\b", re.I),
     "POL-FAM-011 caregiver leave FMLA"),
    (re.compile(r"\bphishing\b|\bokta\b|\bmfa\b", re.I),
     "information security incident POL-SEC-005"),
    (re.compile(r"\bonboard", re.I), "new hire I-9 POL-ONB-007"),
]


def rewrite_query(query: str) -> str:
    extra: list[str] = []
    seen: set[str] = set()
    for pattern, expansion in SYNONYMS:
        if pattern.search(query) and expansion not in seen:
            extra.append(expansion)
            seen.add(expansion)
    if not extra:
        return query.strip()
    return f"{query.strip()} {' '.join(extra)}"
