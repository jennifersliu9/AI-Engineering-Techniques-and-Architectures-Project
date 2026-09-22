from harborline.ingest import chunk_text, load_chunks, split_markdown_sections


def test_chunking_is_deterministic():
    text = "Harborline PTO accrues each semi-monthly pay period. " * 80
    a = chunk_text(text, size=120, overlap=20)
    b = chunk_text(text, size=120, overlap=20)
    assert a == b
    assert a


def test_heading_aware_markdown_keeps_section_titles():
    md = """# Paid Time Off Policy

Intro paragraph.

## Accrual schedule

Employees earn 15 days in years 1-2.

### Part-time

Prorated on scheduled hours.

## Carryover

Maximum 40 hours.
"""
    title, sections = split_markdown_sections(md)
    names = [name for name, _ in sections]
    assert title == "Paid Time Off Policy"
    assert "Accrual schedule" in names
    assert "Carryover" in names
    accrual = next(body for name, body in sections if name == "Accrual schedule")
    assert "15 days" in accrual


def test_load_chunks_include_citation_metadata():
    chunks = load_chunks()
    policy = next(c for c in chunks if c.source_format == "md")
    html = next(c for c in chunks if c.source_format == "html")
    pdf = next(c for c in chunks if c.source_format == "pdf")
    txt = next(c for c in chunks if c.source_format == "txt")
    for item in (policy, html, pdf, txt):
        assert item.title
        assert item.section
        assert item.snippet
        assert item.source_path.startswith("corpus/")
    ids = [c.chunk_id for c in chunks]
    assert ids == [c.chunk_id for c in load_chunks()]
