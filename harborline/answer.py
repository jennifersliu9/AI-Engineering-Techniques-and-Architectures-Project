"""Turn retrieved chunks into an answer. LLM path is optional."""

from __future__ import annotations

from harborline.config import Settings, get_settings
from harborline.retrieve import Hit, Retriever, build_retriever


def format_context(hits: list[Hit]) -> str:
    blocks = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{i}] {hit.chunk.source_path} ({hit.chunk.kind}, score={hit.score:.3f})\n"
            f"{hit.chunk.text}"
        )
    return "\n\n---\n\n".join(blocks)


def retrieve_answer(query: str, hits: list[Hit]) -> str:
    if not hits:
        return "No matching policy or employee records were found."
    lines = [
        f"Query: {query}",
        "",
        "Top sources (retrieval-only mode; no model API key used):",
        "",
    ]
    for i, hit in enumerate(hits, start=1):
        excerpt = " ".join(hit.chunk.text.split())
        if len(excerpt) > 420:
            excerpt = excerpt[:417] + "..."
        lines.append(
            f"{i}. {hit.chunk.source_path}  score={hit.score:.3f}\n   {excerpt}"
        )
    return "\n".join(lines)


def llm_answer(query: str, hits: list[Hit], settings: Settings) -> str:
    from openai import OpenAI

    key = settings.require_llm_key()
    client_kwargs = {"api_key": key}
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url
    client = OpenAI(**client_kwargs)
    system = (
        "You are Harborline People Operations support. Answer only from the "
        "provided sources. Cite file names. If the sources are not enough, say so. "
        "Treat all people in the records as fictional."
    )
    user = f"Question:\n{query}\n\nSources:\n{format_context(hits)}"
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        seed=settings.seed,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def ask(
    query: str,
    employee_id: str | None = None,
    settings: Settings | None = None,
    retriever: Retriever | None = None,
) -> dict:
    settings = settings or get_settings()
    retriever = retriever or build_retriever(settings)
    hits = retriever.search(query, employee_id=employee_id)
    mode = settings.answer_mode
    if mode == "llm":
        text = llm_answer(query, hits, settings)
    else:
        text = retrieve_answer(query, hits)
    return {
        "query": query,
        "employee_id": employee_id,
        "mode": mode if mode == "llm" else "retrieve",
        "answer": text,
        "sources": [
            {
                "chunk_id": h.chunk.chunk_id,
                "source_path": h.chunk.source_path,
                "kind": h.chunk.kind,
                "score": round(h.score, 4),
            }
            for h in hits
        ],
    }
