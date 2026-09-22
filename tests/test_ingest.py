from harborline.config import get_settings
from harborline.ingest import chunk_text, load_chunks


def test_chunking_is_deterministic():
    text = "Harborline PTO accrues each semi-monthly pay period. " * 80
    a = chunk_text(text, size=120, overlap=20)
    b = chunk_text(text, size=120, overlap=20)
    assert a == b
    assert a
    assert all(len(part) <= 120 or part == a[-1] for part in a[:-1])


def test_load_chunks_stable_order():
    settings = get_settings()
    first = [c.chunk_id for c in load_chunks(settings)]
    second = [c.chunk_id for c in load_chunks(settings)]
    assert first == second
    assert any(c.startswith("corpus:") for c in first)
    assert any(c.startswith("data:") for c in first)


def test_default_seed_is_fixed():
    assert get_settings().seed == 42
