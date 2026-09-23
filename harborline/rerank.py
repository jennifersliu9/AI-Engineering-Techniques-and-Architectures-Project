"""Rerank a candidate pool: lexical overlap plus source diversity."""

from __future__ import annotations

import re

from harborline.retrieve import Hit

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if len(t) > 2}


def lexical_overlap(query: str, chunk_text: str) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    d = _tokens(chunk_text)
    return len(q & d) / len(q)


def rerank_hits(query: str, hits: list[Hit], top_k: int) -> list[Hit]:
    """Blend vector score with term overlap, then prefer distinct source files."""
    if not hits:
        return []
    scored: list[tuple[float, Hit]] = []
    for hit in hits:
        lex = lexical_overlap(query, f"{hit.chunk.title} {hit.chunk.section} {hit.chunk.text}")
        blend = 0.65 * max(hit.score, 0.0) + 0.35 * lex
        scored.append((blend, hit))
    scored.sort(key=lambda pair: (-pair[0], pair[1].chunk.chunk_id))

    picked: list[Hit] = []
    used_sources: set[str] = set()
    leftover: list[Hit] = []
    for blend, hit in scored:
        reranked = Hit(score=blend, chunk=hit.chunk)
        src = hit.chunk.source_name
        if src not in used_sources:
            picked.append(reranked)
            used_sources.add(src)
        else:
            leftover.append(reranked)
        if len(picked) >= top_k:
            break
    for hit in leftover:
        if len(picked) >= top_k:
            break
        picked.append(hit)
    return picked[:top_k]
