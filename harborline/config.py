"""Load settings from environment variables. Secrets never live in source."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("FASTEMBED_CACHE_PATH", str(ROOT / ".cache" / "fastembed"))


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw is None or raw == "" else int(raw)


def _str(name: str, default: str) -> str:
    raw = os.getenv(name)
    return default if raw is None or raw == "" else raw


@dataclass(frozen=True)
class Settings:
    seed: int
    chunk_size: int
    chunk_overlap: int
    top_k: int
    answer_mode: str
    retrieve_backend: str
    embedding_model: str
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None
    root: Path
    corpus_dir: Path
    data_dir: Path
    eval_path: Path
    cache_dir: Path
    vector_dir: Path

    def apply_seeds(self) -> None:
        """Fix process-wide RNGs used for evaluation sampling."""
        random.seed(self.seed)
        np.random.seed(self.seed)
        os.environ["PYTHONHASHSEED"] = str(self.seed)

    def require_llm_key(self) -> str:
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env "
                "or export the variable. Do not commit real keys."
            )
        return self.openai_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    key = os.getenv("OPENAI_API_KEY") or None
    return Settings(
        seed=_int("HARBORLINE_SEED", 42),
        chunk_size=_int("HARBORLINE_CHUNK_SIZE", 900),
        chunk_overlap=_int("HARBORLINE_CHUNK_OVERLAP", 120),
        top_k=_int("HARBORLINE_TOP_K", 5),
        answer_mode=_str("HARBORLINE_ANSWER_MODE", "retrieve").lower(),
        retrieve_backend=_str("HARBORLINE_RETRIEVE_BACKEND", "faiss").lower(),
        embedding_model=_str(
            "HARBORLINE_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        openai_api_key=key,
        openai_model=_str("OPENAI_MODEL", "gpt-4o-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
        root=ROOT,
        corpus_dir=ROOT / "corpus",
        data_dir=ROOT / "data",
        eval_path=ROOT / "eval" / "gold_questions.json",
        cache_dir=ROOT / ".cache",
        vector_dir=ROOT / ".cache" / "faiss",
    )
