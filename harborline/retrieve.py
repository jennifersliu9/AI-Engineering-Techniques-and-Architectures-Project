"""TF-IDF retrieval over policy chunks and structured records."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from harborline.config import Settings, get_settings
from harborline.ingest import Chunk, load_chunks


@dataclass(frozen=True)
class Hit:
    score: float
    chunk: Chunk


class Retriever:
    def __init__(self, chunks: list[Chunk], settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
            # Fixed token pattern; no hashed features, so results are stable.
        )
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
        # Stable tie-break: score desc, then chunk_id asc.
        ranked = sorted(
            range(len(self.chunks)),
            key=lambda i: (-float(scores[i]), self.chunks[i].chunk_id),
        )
        hits: list[Hit] = []
        for i in ranked:
            if employee_id:
                extra_id = self.chunks[i].extra.get("employee_id")
                if self.chunks[i].kind == "structured" and extra_id not in {
                    employee_id,
                    None,
                }:
                    # Keep other employees out of the structured slice.
                    continue
            hits.append(Hit(score=float(scores[i]), chunk=self.chunks[i]))
            if len(hits) >= k:
                break
        return hits


def build_retriever(settings: Settings | None = None) -> Retriever:
    settings = settings or get_settings()
    return Retriever(load_chunks(settings), settings)
