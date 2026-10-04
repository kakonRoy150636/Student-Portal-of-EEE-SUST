import json

import pytest

from evals.retrieval_eval import DEFAULT_CASES, seed_fixture, evaluate

pytestmark = pytest.mark.asyncio


async def test_25_case_eval_runs_actual_postgres_retrieval(database, monkeypatch):
    from app.core.config import settings
    data = json.loads(DEFAULT_CASES.read_text())
    assert len(data['cases']) == 25
    assert all(case.get('expected_answer') for case in data['cases'])
    async with database.sessions() as db, db.begin():
        await seed_fixture(db, data)
    monkeypatch.setattr(settings, 'GEMINI_EMBEDDING_MODEL', settings.GEMINI_EMBEDDING_MODEL)
    monkeypatch.setattr(settings, 'AI_RETRIEVAL_TOP_K', settings.AI_RETRIEVAL_TOP_K)
    report = await evaluate(database.sessions, data, mode='fixture-hybrid', lexical_weight=1, vector_weight=1, top_k=5)
    assert report['cases'] == 25 and report['answerable_cases'] == 20
    assert report['retrieval_hit_rate'] >= 0.8
    assert report['unanswerable_abstention_rate'] == 1
    assert report['vector_note'].startswith('Synthetic')
    assert report['results'][0]['retrieved'][0]['document_name'] == 'Academic Example Corpus'
