from harborline.config import get_settings
from harborline.evaluate import run_eval, sample_questions
from harborline.ingest import load_chunks
from harborline.retrieve import TfidfRetriever


def test_sampling_uses_seed():
    items = [{"id": str(i)} for i in range(20)]
    a = [q["id"] for q in sample_questions(items, 5, 42)]
    b = [q["id"] for q in sample_questions(items, 5, 42)]
    c = [q["id"] for q in sample_questions(items, 5, 7)]
    assert a == b
    assert a != c


def test_eval_runs_on_gold_set():
    settings = get_settings()
    retriever = TfidfRetriever(load_chunks(settings), settings)
    report = run_eval(settings=settings, retriever=retriever)
    assert report["seed"] == 42
    assert report["n"] >= 10
    assert 0.0 <= report["recall_at_k"] <= 1.0
    assert report["passed"] >= 8
