"""Optional HTTP surface for local run and container deploy."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from harborline.answer import ask
from harborline.config import get_settings
from harborline.evaluate import run_eval
from harborline.retrieve import Retriever, build_retriever

app = FastAPI(title="Harborline Q&A", version="0.1.0")
_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = build_retriever(get_settings())
    return _retriever


class AskRequest(BaseModel):
    query: str = Field(min_length=2)
    employee_id: str | None = None


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "seed": settings.seed,
        "answer_mode": settings.answer_mode,
        "has_openai_key": bool(settings.openai_api_key),
    }


@app.post("/ask")
def ask_endpoint(body: AskRequest) -> dict:
    settings = get_settings()
    try:
        return ask(
            body.query,
            employee_id=body.employee_id,
            settings=settings,
            retriever=get_retriever(),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/eval")
def eval_endpoint() -> dict:
    return run_eval(settings=get_settings(), retriever=get_retriever())
