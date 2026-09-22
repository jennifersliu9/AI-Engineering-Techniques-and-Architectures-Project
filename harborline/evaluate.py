"""Seeded retrieval evaluation against a fixed gold set."""

from __future__ import annotations

import json
import random
from pathlib import Path

from harborline.config import Settings, get_settings
from harborline.retrieve import Retriever, build_retriever


def load_gold(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload["questions"])


def sample_questions(questions: list[dict], limit: int | None, seed: int) -> list[dict]:
    if limit is None or limit >= len(questions):
        return questions
    rng = random.Random(seed)
    return rng.sample(questions, limit)


def _hit_matches(hit_source: str, expected_sources: list[str]) -> bool:
    name = Path(hit_source).name.lower()
    path = hit_source.lower().replace("\\", "/")
    for expected in expected_sources:
        exp = expected.lower().replace("\\", "/")
        if exp in path or Path(exp).name.lower() == name:
            return True
    return False


def evaluate_question(item: dict, retriever: Retriever, top_k: int) -> dict:
    hits = retriever.search(
        item["question"],
        top_k=top_k,
        employee_id=item.get("employee_id"),
    )
    sources = [h.chunk.source_path for h in hits]
    expected = item.get("expected_sources", [])
    retrieved = any(_hit_matches(src, expected) for src in sources)
    expected_ids = set(item.get("expected_employee_ids") or [])
    got_ids = {
        h.chunk.extra.get("employee_id")
        for h in hits
        if h.chunk.extra.get("employee_id")
    }
    employee_ok = True if not expected_ids else bool(expected_ids & got_ids)
    return {
        "id": item["id"],
        "question": item["question"],
        "retrieved_expected_source": retrieved,
        "retrieved_expected_employee": employee_ok,
        "pass": retrieved and employee_ok,
        "sources": sources,
    }


def run_eval(
    settings: Settings | None = None,
    limit: int | None = None,
    retriever: Retriever | None = None,
) -> dict:
    settings = settings or get_settings()
    settings.apply_seeds()
    questions = load_gold(settings.eval_path)
    chosen = sample_questions(questions, limit, settings.seed)
    retriever = retriever or build_retriever(settings)
    rows = [evaluate_question(q, retriever, settings.top_k) for q in chosen]
    passed = sum(1 for r in rows if r["pass"])
    return {
        "seed": settings.seed,
        "top_k": settings.top_k,
        "n": len(rows),
        "passed": passed,
        "recall_at_k": round(passed / len(rows), 4) if rows else 0.0,
        "results": rows,
    }
