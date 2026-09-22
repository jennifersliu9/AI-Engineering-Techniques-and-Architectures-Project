"""Deterministic document loading and chunking. No random splits."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from harborline.config import Settings, get_settings

CORPUS_SUFFIXES = {".md", ".txt", ".html", ".pdf"}
SKIP_NAMES = {"readme.md"}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_path: str
    source_name: str
    kind: str
    text: str
    order: int
    extra: dict


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _read_html(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def read_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".html":
        return _read_html(path)
    return path.read_text(encoding="utf-8")


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Fixed-window chunks. Order is stable for a given size/overlap."""
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and < size")
    text = normalize_whitespace(text)
    if not text:
        return []
    if len(text) <= size:
        return [text]
    step = size - overlap
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break
        start += step
    return chunks


def _corpus_chunks(settings: Settings) -> list[Chunk]:
    chunks: list[Chunk] = []
    paths = sorted(
        p
        for p in settings.corpus_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in CORPUS_SUFFIXES
        and p.name.lower() not in SKIP_NAMES
    )
    for path in paths:
        raw = read_file(path)
        parts = chunk_text(raw, settings.chunk_size, settings.chunk_overlap)
        for order, part in enumerate(parts):
            chunks.append(
                Chunk(
                    chunk_id=f"corpus:{path.name}:{order}",
                    source_path=str(path.relative_to(settings.root)),
                    source_name=path.name,
                    kind="policy",
                    text=part,
                    order=order,
                    extra={"policy_hint": path.stem},
                )
            )
    return chunks


def _record_text(record: dict) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, indent=2)


def _structured_chunks(settings: Settings) -> list[Chunk]:
    chunks: list[Chunk] = []
    paths = sorted(p for p in settings.data_dir.glob("*.json"))
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        dataset = payload.get("dataset", path.stem)
        for order, record in enumerate(payload.get("records", [])):
            employee_id = record.get("employee_id")
            office_id = record.get("office_id")
            ticket_id = record.get("ticket_id")
            label = employee_id or office_id or ticket_id or f"row-{order}"
            text = (
                f"Dataset: {dataset}\n"
                f"Record id: {label}\n"
                f"{_record_text(record)}"
            )
            chunks.append(
                Chunk(
                    chunk_id=f"data:{path.name}:{label}",
                    source_path=str(path.relative_to(settings.root)),
                    source_name=path.name,
                    kind="structured",
                    text=text,
                    order=order,
                    extra={
                        "dataset": dataset,
                        "employee_id": employee_id,
                        "office_id": office_id,
                        "ticket_id": ticket_id,
                    },
                )
            )
    return chunks


def load_chunks(settings: Settings | None = None) -> list[Chunk]:
    settings = settings or get_settings()
    chunks = _corpus_chunks(settings) + _structured_chunks(settings)
    chunks.sort(key=lambda c: (c.kind, c.source_name, c.order, c.chunk_id))
    return chunks


def write_index(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks(settings)
    out = settings.cache_dir / "chunks.json"
    payload = {
        "seed": settings.seed,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "count": len(chunks),
        "chunks": [asdict(c) for c in chunks],
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out
