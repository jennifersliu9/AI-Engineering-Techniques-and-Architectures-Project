"""Deterministic parse, clean, and chunk for markdown, HTML, PDF, TXT, and JSON."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from harborline.config import Settings, get_settings

CORPUS_SUFFIXES = {".md", ".txt", ".html", ".pdf"}
SKIP_NAMES = {"readme.md"}
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_path: str
    source_name: str
    source_format: str
    title: str
    section: str
    kind: str
    text: str
    snippet: str
    order: int
    extra: dict = field(default_factory=dict)


def make_snippet(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Character windows with overlap. Used when a section is longer than size."""
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


def split_markdown_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Heading-aware sections. Strategy: keep each ##/### block together, then window."""
    title = "Untitled"
    sections: list[tuple[str, str]] = []
    current = "Introduction"
    buf: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        match = HEADING_RE.match(line.strip())
        if match:
            if buf:
                body = normalize_whitespace("\n".join(buf))
                if body:
                    sections.append((current, body))
                buf = []
            current = match.group(2).strip()
            if match.group(1) == "#" and title == "Untitled":
                title = current
            buf.append(line.strip())
        else:
            buf.append(line)
    if buf:
        body = normalize_whitespace("\n".join(buf))
        if body:
            sections.append((current, body))
    if title == "Untitled" and sections:
        title = sections[0][0]
    return title, sections


def parse_markdown(path: Path) -> tuple[str, list[tuple[str, str]]]:
    return split_markdown_sections(path.read_text(encoding="utf-8"))


def parse_html(path: Path) -> tuple[str, list[tuple[str, str]]]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else path.stem
    sections: list[tuple[str, str]] = []
    current = title
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, current
        body = normalize_whitespace("\n".join(buf))
        if body:
            sections.append((current, body))
        buf = []

    root = soup.body or soup
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th"]):
        name = el.name or ""
        if name in {"h1", "h2", "h3", "h4"}:
            flush()
            current = el.get_text(" ", strip=True) or current
            buf.append(current)
            continue
        if el.find(["h1", "h2", "h3", "h4"]):
            continue
        text = el.get_text(" ", strip=True)
        if text:
            buf.append(text)
    flush()
    if not sections:
        fallback = normalize_whitespace(soup.get_text("\n", strip=True))
        if fallback:
            sections.append((title, fallback))
    return title, sections


def parse_pdf(path: Path) -> tuple[str, list[tuple[str, str]]]:
    reader = PdfReader(str(path))
    title = path.stem.replace("-", " ")
    if reader.metadata and reader.metadata.title:
        title = str(reader.metadata.title)
    sections: list[tuple[str, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        body = normalize_whitespace(page.extract_text() or "")
        if body:
            sections.append((f"Page {index}", body))
    return title, sections


def parse_txt(path: Path) -> tuple[str, list[tuple[str, str]]]:
    text = normalize_whitespace(path.read_text(encoding="utf-8"))
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    title = lines[0][:120] if lines else path.stem
    return title, [("Body", text)]


def parse_corpus_file(path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    suffix = path.suffix.lower()
    if suffix == ".md":
        title, sections = parse_markdown(path)
        return "md", title, sections
    if suffix == ".html":
        title, sections = parse_html(path)
        return "html", title, sections
    if suffix == ".pdf":
        title, sections = parse_pdf(path)
        return "pdf", title, sections
    title, sections = parse_txt(path)
    return "txt", title, sections


def _windows_for_section(section: str, body: str, size: int, overlap: int) -> list[tuple[str, str]]:
    parts = chunk_text(body, size, overlap)
    if len(parts) == 1:
        return [(section, parts[0])]
    return [(f"{section} (part {i + 1})", part) for i, part in enumerate(parts)]


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
        fmt, title, sections = parse_corpus_file(path)
        order = 0
        for section, body in sections:
            for sec_label, part in _windows_for_section(
                section, body, settings.chunk_size, settings.chunk_overlap
            ):
                chunks.append(
                    Chunk(
                        chunk_id=f"corpus:{path.name}:{order}",
                        source_path=str(path.relative_to(settings.root)).replace("\\", "/"),
                        source_name=path.name,
                        source_format=fmt,
                        title=title,
                        section=sec_label,
                        kind="policy",
                        text=part,
                        snippet=make_snippet(part),
                        order=order,
                        extra={"policy_hint": path.stem},
                    )
                )
                order += 1
    return chunks


def _record_text(record: dict) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, indent=2)


def _structured_chunks(settings: Settings) -> list[Chunk]:
    chunks: list[Chunk] = []
    paths = sorted(p for p in settings.data_dir.glob("*.json"))
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        dataset = payload.get("dataset", path.stem)
        title = f"HarborHub {dataset}"
        for order, record in enumerate(payload.get("records", [])):
            employee_id = record.get("employee_id")
            office_id = record.get("office_id")
            ticket_id = record.get("ticket_id")
            label = employee_id or office_id or ticket_id or f"row-{order}"
            section = f"{dataset}/{label}"
            text = f"Dataset: {dataset}\nRecord id: {label}\n{_record_text(record)}"
            chunks.append(
                Chunk(
                    chunk_id=f"data:{path.name}:{label}",
                    source_path=str(path.relative_to(settings.root)).replace("\\", "/"),
                    source_name=path.name,
                    source_format="json",
                    title=title,
                    section=section,
                    kind="structured",
                    text=text,
                    snippet=make_snippet(text),
                    order=order,
                    extra={
                        "dataset": dataset,
                        "employee_id": employee_id or "",
                        "office_id": office_id or "",
                        "ticket_id": ticket_id or "",
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
    """Write the JSON chunk cache (citations + debugging). Vector persist is separate."""
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
