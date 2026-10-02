"""The academic assistant: retrieval, grounding and honest failure.

The behaviour under test is that the endpoint never presents invented content
as an answer. Three cases: a real retrieval hit with a configured model, a
retrieval hit with no model (extractive, labelled), and nothing retrieved
(explicit no-context message). The old implementation returned a canned
sentence in all three.
"""
import uuid

import pytest

from app.models.academic import Course
from app.models.ai_knowledge import DocumentChunk, KnowledgeDocument
from app.services import ai_rag_service as ai_module
from app.services.ai_rag_service import split_into_chunks
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def _seed_document(
    db,
    content=(
        "Slip is the difference between the synchronous speed of the stator field "
        "and the actual rotor speed, usually expressed as a percentage."
    ),
):
    course = Course(course_code="EEE 311", title="Electrical Machines II", credit_hours=3.0, type="theory")
    db.add(course)
    await db.flush()
    document = KnowledgeDocument(course_id=course.id, title="Machines II handout", file_path="kb/1.pdf")
    db.add(document)
    await db.flush()
    db.add(DocumentChunk(document_id=document.id, content=content))
    await db.commit()
    return document


async def test_query_requires_authentication(client):
    response = await client.post("/api/v1/ai/query", json={"prompt": "What is slip?"})
    assert response.status_code == 401


async def test_empty_knowledge_base_says_so_instead_of_inventing(client, db):
    user = await make_user(db)
    response = await client.post(
        "/api/v1/ai/query",
        json={"prompt": "Explain armature reaction in detail"},
        headers=auth_header(user),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["grounded"] is False
    assert body["mode"] == "no-context"
    assert body["citations"] == []
    # The point: no fabricated engineering content.
    assert "armature" not in body["answer"].lower()
    assert "library" in body["answer"].lower()


async def test_retrieved_passage_is_cited_and_quoted_without_a_model(client, db, monkeypatch):
    user = await make_user(db)
    await _seed_document(db)

    async def no_embedding(_text):
        return None

    async def no_generation(_prompt, system=None):
        return None

    monkeypatch.setattr(ai_module.gemini_client, "embed_text", no_embedding)
    monkeypatch.setattr(ai_module.gemini_client, "generate_text", no_generation)

    response = await client.post(
        "/api/v1/ai/query",
        json={"prompt": "synchronous speed", "course_code": "EEE 311"},
        headers=auth_header(user),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "extractive"
    assert body["grounded"] is False
    assert body["citations"][0]["document_title"] == "Machines II handout"
    assert body["citations"][0]["course_code"] == "EEE 311"
    # The answer quotes the indexed passage rather than paraphrasing it.
    assert "synchronous speed" in body["answer"]


async def test_model_answer_is_marked_grounded_and_persisted(client, db, monkeypatch):
    user = await make_user(db)
    await _seed_document(db)

    async def no_embedding(_text):
        return None

    async def fake_generation(prompt, system=None):
        assert "Machines II handout" in prompt  # context really was supplied
        return "Slip is the difference between synchronous and rotor speed [1]."

    monkeypatch.setattr(ai_module.gemini_client, "embed_text", no_embedding)
    monkeypatch.setattr(ai_module.gemini_client, "generate_text", fake_generation)

    response = await client.post(
        "/api/v1/ai/query",
        json={"prompt": "What is slip?", "course_code": "EEE 311"},
        headers=auth_header(user),
    )
    body = response.json()
    assert body["grounded"] is True
    assert body["mode"] == "gemini"
    assert body["session_id"]

    history = await client.get("/api/v1/ai/history", headers=auth_header(user))
    assert history.status_code == 200
    roles = [row["role"] for row in history.json()]
    assert roles == ["student", "assistant"]
    assert "Slip is the difference" in history.json()[1]["content"]


async def test_history_is_per_student(client, db, monkeypatch):
    student = await make_user(db)
    other = await make_user(db, identifier="2023000003", email="other3@sust.edu")

    async def no_embedding(_text):
        return None

    monkeypatch.setattr(ai_module.gemini_client, "embed_text", no_embedding)
    await client.post(
        "/api/v1/ai/query", json={"prompt": "anything"}, headers=auth_header(student)
    )

    other_history = await client.get("/api/v1/ai/history", headers=auth_header(other))
    assert other_history.json() == []


async def test_prompt_length_is_bounded(client, db):
    user = await make_user(db)
    response = await client.post(
        "/api/v1/ai/query",
        json={"prompt": "x" * 2000},
        headers=auth_header(user),
    )
    assert response.status_code == 422
