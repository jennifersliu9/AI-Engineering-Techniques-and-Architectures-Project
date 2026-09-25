"""Prompt templates that inject retrieved chunks and citation metadata."""

from __future__ import annotations

from harborline.retrieve import Hit

SYSTEM_PROMPT = """You are Harborline People Operations support for a fictional company.
Answer only from the numbered sources. If a fact is not in the sources, say it is not in the corpus.

Output rules:
1. Start with a short **Policy fact** section. Every factual claim must cite sources like [1] or [1][3] using the source numbers.
2. Include a **Citations** list: number, document title, section, and a short supporting snippet from that source.
3. Add a **Not a recommendation** line when the user asks what they "should" do personally. Policy states rules; it does not give legal, medical, or career advice.
4. If sources conflict, state both and name the dedicated policy as controlling (handbook vs dedicated policy).
5. Do not invent dollar amounts, dates, or weeks that are not in the sources.
6. Treat named employees as fictional HarborHub records.
"""


def format_source_block(hits: list[Hit]) -> str:
    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{i}] id={hit.chunk.chunk_id}\n"
            f"title={hit.chunk.title}\n"
            f"section={hit.chunk.section}\n"
            f"path={hit.chunk.source_path}\n"
            f"score={hit.score:.3f}\n"
            f"snippet={hit.chunk.snippet}\n"
            f"text=\n{hit.chunk.text}"
        )
    return "\n\n---\n\n".join(blocks)


def user_prompt(query: str, hits: list[Hit], employee_id: str | None = None) -> str:
    who = f"\nEmployee context id: {employee_id}" if employee_id else ""
    return (
        f"Question:{who}\n{query}\n\n"
        "Sources (use these numbers in citations):\n\n"
        f"{format_source_block(hits)}"
    )
