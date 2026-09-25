"""HTTP surface: chat UI, /chat agent, /health, retrieve-only /ask."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from harborline.agent import run_agent
from harborline.answer import ask
from harborline.config import get_settings
from harborline.evaluate import run_eval
from harborline.retrieve import build_retriever

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Harborline People Desk", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_retriever = None

DEMOS = [
    {
        "id": "remote-emp-1008",
        "label": "Remote eligibility — EMP-1008",
        "query": "Am I eligible for fully remote work living in Tacoma?",
        "employee_id": "EMP-1008",
        "curl": (
            'curl -X POST http://127.0.0.1:8000/chat '
            '-H "Content-Type: application/json" '
            '-d "{\\"query\\":\\"Am I eligible for fully remote work living in Tacoma?\\",'
            '\\"employee_id\\":\\"EMP-1008\\"}"'
        ),
    },
    {
        "id": "pto-emp-1014",
        "label": "PTO guidance — EMP-1014",
        "query": "Can I take PTO next week?",
        "employee_id": "EMP-1014",
        "curl": (
            'curl -X POST http://127.0.0.1:8000/chat '
            '-H "Content-Type: application/json" '
            '-d "{\\"query\\":\\"Can I take PTO next week?\\",\\"employee_id\\":\\"EMP-1014\\"}"'
        ),
    },
]


def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = build_retriever(get_settings())
    return _retriever


class AskRequest(BaseModel):
    query: str = Field(min_length=2)
    employee_id: str | None = None
    kind: str | None = None
    source_format: str | None = None


class ChatRequest(BaseModel):
    query: str = Field(min_length=2)
    employee_id: str | None = None
    confirm: bool = False
    transport: str = "mcp-inproc"


def _mcp_status() -> dict:
    try:
        from harborline.mcp_client import open_mcp_bus

        bus = open_mcp_bus("mcp-inproc")
        try:
            return {
                "available": bool(bus.available),
                "transport": bus.transport,
                "discovered_tools": list(bus.discovered_tools or []),
                "tool_count": len(bus.discovered_tools or []),
            }
        finally:
            bus.close()
    except Exception as exc:  # noqa: BLE001 — health must stay up
        return {"available": False, "transport": None, "discovered_tools": [], "error": str(exc)}


def _chat_payload(result) -> dict:
    sources = result.sources or []
    citations = []
    snippets = []
    for i, src in enumerate(sources, start=1):
        citations.append(
            {
                "n": i,
                "title": src.get("title"),
                "section": src.get("section"),
                "source_path": src.get("source_path"),
                "kind": src.get("kind"),
                "score": src.get("score"),
            }
        )
        text = src.get("snippet") or src.get("text") or ""
        if text:
            snippets.append({"n": i, "snippet": text, "source_path": src.get("source_path")})
    payload = result.to_dict()
    payload["citations"] = citations
    payload["snippets"] = snippets
    payload["trace"] = payload.get("trace") or []
    return payload


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    mcp = _mcp_status()
    return {
        "status": "ok" if mcp.get("available") else "degraded",
        "app": "ok",
        "seed": settings.seed,
        "answer_mode": settings.answer_mode,
        "retrieve_backend": settings.retrieve_backend,
        "embedding_model": settings.embedding_model,
        "has_openai_key": bool(settings.openai_api_key),
        "mcp": mcp,
    }


@app.get("/demos")
def demos() -> dict:
    return {"demos": DEMOS}


@app.post("/chat")
def chat_endpoint(body: ChatRequest) -> dict:
    try:
        result = run_agent(
            body.query,
            employee_id=body.employee_id,
            confirm=body.confirm,
            transport=body.transport,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _chat_payload(result)


@app.post("/ask")
def ask_endpoint(body: AskRequest) -> dict:
    settings = get_settings()
    try:
        return ask(
            body.query,
            employee_id=body.employee_id,
            kind=body.kind,
            source_format=body.source_format,
            settings=settings,
            retriever=get_retriever(),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/eval")
def eval_endpoint() -> dict:
    return run_eval(settings=get_settings(), retriever=get_retriever())
