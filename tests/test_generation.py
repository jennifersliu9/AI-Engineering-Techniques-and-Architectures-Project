from harborline.guardrails import apply_guardrails, is_out_of_scope
from harborline.rerank import lexical_overlap, rerank_hits
from harborline.retrieve import Hit
from harborline.ingest import Chunk
from harborline.rewrite import rewrite_query


def _hit(name: str, text: str, score: float) -> Hit:
    chunk = Chunk(
        chunk_id=name,
        source_path=f"corpus/{name}",
        source_name=name,
        source_format="md",
        title=name,
        section="body",
        kind="policy",
        text=text,
        snippet=text[:80],
        order=0,
        extra={},
    )
    return Hit(score=score, chunk=chunk)


def test_rewrite_expands_pto():
    out = rewrite_query("How much PTO do I get?")
    assert "POL-PTO-001" in out
    assert "paid time off" in out.lower()


def test_guardrail_blocks_out_of_corpus():
    assert is_out_of_scope("Should I buy bitcoin with my bonus?")
    ok, message = apply_guardrails("Should I buy bitcoin with my bonus?", [], 0.22)
    assert ok is False
    assert "outside the corpus" in message


def test_guardrail_blocks_weak_scores():
    hits = [_hit("noise.md", "office snacks", 0.05)]
    ok, message = apply_guardrails("obscure unrelated query xyz", hits, 0.22)
    assert ok is False
    assert "weakly related" in message


def test_rerank_prefers_diverse_sources():
    hits = [
        _hit("a.md", "PTO accrual 15 days", 0.9),
        _hit("a.md", "PTO carryover 40 hours", 0.89),
        _hit("b.md", "Thanksgiving company holiday 2026", 0.4),
    ]
    ranked = rerank_hits("PTO Thanksgiving holiday", hits, top_k=2)
    names = {h.chunk.source_name for h in ranked}
    assert names == {"a.md", "b.md"}
    assert lexical_overlap("PTO holiday", "PTO Thanksgiving company holiday") > 0
