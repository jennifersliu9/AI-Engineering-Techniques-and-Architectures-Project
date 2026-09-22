"""Local MiniLM embeddings stored in a persistent FAISS index."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from harborline.config import Settings, get_settings
from harborline.ingest import Chunk, load_chunks

_embedder = None


def _meta_value(value: object) -> str | int | float | bool:
    if isinstance(value, bool | int | float):
        return value
    if value is None:
        return ""
    return str(value)


def chunk_to_metadata(chunk: Chunk) -> dict:
    meta = {
        "chunk_id": chunk.chunk_id,
        "source_path": chunk.source_path,
        "source_name": chunk.source_name,
        "source_format": chunk.source_format,
        "title": chunk.title,
        "section": chunk.section,
        "kind": chunk.kind,
        "snippet": chunk.snippet,
        "order": chunk.order,
        "text": chunk.text,
    }
    for key, value in chunk.extra.items():
        meta[key] = _meta_value(value)
    return meta


def metadata_to_chunk(meta: dict) -> Chunk:
    extra = {
        k: meta.get(k, "")
        for k in ("dataset", "employee_id", "office_id", "ticket_id", "policy_hint")
        if k in meta
    }
    text = str(meta.get("text", ""))
    return Chunk(
        chunk_id=str(meta.get("chunk_id", "")),
        source_path=str(meta.get("source_path", "")),
        source_name=str(meta.get("source_name", "")),
        source_format=str(meta.get("source_format", "")),
        title=str(meta.get("title", "")),
        section=str(meta.get("section", "")),
        kind=str(meta.get("kind", "policy")),
        text=text,
        snippet=str(meta.get("snippet") or text[:240]),
        order=int(meta.get("order") or 0),
        extra=extra,
    )


def embedder(settings: Settings | None = None):
    """Free local MiniLM via FastEmbed (ONNX). No API key."""
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding

        settings = settings or get_settings()
        _embedder = TextEmbedding(model_name=settings.embedding_model)
    return _embedder


def embed_texts(texts: list[str], settings: Settings | None = None) -> np.ndarray:
    import faiss

    model = embedder(settings)
    vectors = np.array(list(model.embed(texts)), dtype="float32")
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    faiss.normalize_L2(vectors)
    return vectors


def _index_path(settings: Settings) -> Path:
    return settings.vector_dir / "index.faiss"


def _meta_path(settings: Settings) -> Path:
    return settings.vector_dir / "metadatas.json"


def persist_chunks(chunks: list[Chunk] | None = None, settings: Settings | None = None) -> int:
    import faiss

    settings = settings or get_settings()
    chunks = chunks if chunks is not None else load_chunks(settings)
    settings.vector_dir.mkdir(parents=True, exist_ok=True)
    vectors = embed_texts([c.text for c in chunks], settings)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, str(_index_path(settings)))
    payload = {
        "embedding_model": settings.embedding_model,
        "count": len(chunks),
        "records": [chunk_to_metadata(c) for c in chunks],
    }
    _meta_path(settings).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(chunks)


def load_index(settings: Settings | None = None):
    import faiss

    settings = settings or get_settings()
    index = faiss.read_index(str(_index_path(settings)))
    payload = json.loads(_meta_path(settings).read_text(encoding="utf-8"))
    return index, payload["records"]


def collection_count(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    if not _index_path(settings).exists() or not _meta_path(settings).exists():
        return 0
    payload = json.loads(_meta_path(settings).read_text(encoding="utf-8"))
    return int(payload.get("count") or 0)
