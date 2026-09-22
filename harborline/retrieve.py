"""Retrieval: FAISS vector search by default, TF-IDF as a no-download fallback."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from harborline.config import Settings, get_settings
from harborline.ingest import Chunk, load_chunks
from harborline.store import collection_count, load_index, metadata_to_chunk, persist_chunks


@dataclass(frozen=True)
class Hit:
    score: float
    chunk: Chunk


def _keep_hit(chunk: Chunk, employee_id: str | None) -> bool:
    if not employee_id:
        return True
    extra_id = chunk.extra.get("employee_id") or ""
    if chunk.kind == "structured" and extra_id and extra_id != employee_id:
        return False
    return True


class TfidfRetriever:
    def __init__(self, chunks: list[Chunk], settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1)
        texts = [c.text for c in chunks]
        if not texts:
            raise ValueError("No chunks to index. Check corpus/ and data/.")
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        employee_id: str | None = None,
    ) -> list[Hit]:
        k = top_k or self.settings.top_k
        q = query.strip()
        if employee_id:
            q = f"{q} employee_id {employee_id}"
        vec = self.vectorizer.transform([q])
        scores = cosine_similarity(vec, self.matrix).ravel()
        ranked = sorted(
            range(len(self.chunks)),
            key=lambda i: (-float(scores[i]), self.chunks[i].chunk_id),
        )
        hits: list[Hit] = []
        for i in ranked:
            chunk = self.chunks[i]
            if not _keep_hit(chunk, employee_id):
                continue
            hits.append(Hit(score=float(scores[i]), chunk=chunk))
            if len(hits) >= k:
                break
        return hits


class VectorRetriever:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if collection_count(self.settings) == 0:
            persist_chunks(load_chunks(self.settings), self.settings)
        self.index, self.records = load_index(self.settings)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        employee_id: str | None = None,
    ) -> list[Hit]:
        from harborline.store import embed_texts

        k = top_k or self.settings.top_k
        fetch = min(max(k * 4, k), len(self.records) or 1)
        q = query.strip()
        if employee_id:
            q = f"{q} employee_id {employee_id}"
        qvec = embed_texts([q], self.settings)
        scores, indices = self.index.search(qvec, fetch)
        hits: list[Hit] = []
        for score, row in zip(scores[0], indices[0]):
            if int(row) < 0:
                continue
            chunk = metadata_to_chunk(self.records[int(row)])
            if not _keep_hit(chunk, employee_id):
                continue
            hits.append(Hit(score=float(score), chunk=chunk))
            if len(hits) >= k:
                break
        return hits


def build_retriever(settings: Settings | None = None):
    settings = settings or get_settings()
    if settings.retrieve_backend == "tfidf":
        return TfidfRetriever(load_chunks(settings), settings)
    return VectorRetriever(settings)


# Back-compat alias used in older tests/docs
Retriever = TfidfRetriever
