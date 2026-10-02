"""Chunking helpers (pure functions, no database)."""
from app.services import ai_rag_service as ai_module
from app.services.ai_rag_service import split_into_chunks


def test_chunking_overlaps_and_bounds_size():
    text = "\n\n".join(f"Paragraph {index} " + "word " * 80 for index in range(30))
    chunks = split_into_chunks(text)
    assert len(chunks) > 1
    assert all(len(chunk) <= ai_module.CHUNK_SIZE for chunk in chunks)
    # Overlap: consecutive chunks share content so a definition on a boundary
    # is still retrievable from one of them.
    assert chunks[0][-50:] in chunks[1] or chunks[1][:50] in chunks[0]


def test_chunking_handles_empty_input():
    assert split_into_chunks("   \n\n  ") == []
    assert split_into_chunks("short") == ["short"]
