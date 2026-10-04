"""25-case retrieval eval, no answer synthesis or silent production seeding.

Example fixture mode requires a disposable pgvector cluster with CREATEDB.
Live mode queries the operator's existing, migrated and reviewed corpus.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.ai_budget import reserve_ai
from app.integrations.gemini_client import GeminiClient, embedding_cost
from app.services.ai_retrieval import AcademicRetriever, keywords, normalize_vector

DEFAULT_CASES = Path(__file__).with_name('academic_questions.json')


def fixture_embedding(value):
    """Deterministic bag-of-words TEST vector, NOT a Gemini semantic embedding."""
    vector = [0.0] * 768
    for term in keywords(value):
        bucket = int.from_bytes(hashlib.sha256(term.encode()).digest()[:4], 'big') % 768
        vector[bucket] += 1
    return normalize_vector(vector) if any(vector) else [1.0] + [0.0]*767


async def seed_fixture(db, dataset):
    course = await db.scalar(text("INSERT INTO courses(course_code,title,credit_hours,type) VALUES ('EVAL 311','Synthetic evaluation only',3,'theory') RETURNING id"))
    doc = await db.scalar(text("INSERT INTO knowledge_documents(course_id,title,file_path) VALUES (:course,:title,'backend/evals/academic_questions.json') RETURNING id"),
                          {'course': course, 'title': dataset['document_name']})
    for case in dataset['cases']:
        if not case.get('source_text'):
            continue
        await db.execute(text("INSERT INTO document_chunks(id,document_id,content,section,embedding,embedding_model) VALUES (:id,:doc,:content,:section,CAST(:vector AS vector),'eval-hash-768')"),
            {'id': uuid.uuid5(uuid.NAMESPACE_URL, 'portal-eval:' + case['id']),
             'doc': doc, 'content': case['source_text'], 'section': case['section'],
             'vector': '[' + ','.join(str(x) for x in fixture_embedding(case['source_text'])) + ']'})


async def evaluate(sessions, dataset, *, mode, lexical_weight, vector_weight, top_k):
    if mode == 'fixture-hybrid':
        settings.GEMINI_EMBEDDING_MODEL = 'eval-hash-768'
    settings.AI_RETRIEVAL_TOP_K = top_k
    results = []
    provider = GeminiClient()
    for case in dataset['cases']:
        vector = None
        if mode == 'fixture-hybrid':
            vector = fixture_embedding(case['question'])
        elif mode == 'live':
            reservation = await reserve_ai('retrieval-evaluation', embedding_cost(case['question']), enforce_user_quota=False)
            vector = await provider.embed(case['question'])
            await reservation.settle(embedding_cost(case['question']))
        async with sessions() as db:
            chunks = await AcademicRetriever(db).retrieve(case['question'], case['course_code'], vector,
                lexical_weight=lexical_weight, vector_weight=0 if mode == 'lexical' else vector_weight)
        expected = case['expected_sections']
        expected_pages = case.get('expected_pages', [])
        expected_document = case.get('expected_document_name', dataset['document_name'])
        rank = next((i for i, chunk in enumerate(chunks, 1)
                     if (chunk.section in expected or chunk.page_number in expected_pages) and chunk.document_name == expected_document), None)
        confident = any(chunk.confident for chunk in chunks)
        results.append({'id': case['id'], 'question': case['question'], 'expected_answer': case['expected_answer'],
                        'expected_sections': expected, 'expected_pages': expected_pages,
                        'hit': rank is not None if expected or expected_pages else None,
                        'expected_rank': rank, 'would_abstain': not confident,
                        'retrieved': [{'document_name': c.document_name, 'section': c.section,
                                       'page_number': c.page_number, 'rrf_score': c.rrf_score,
                                       'lexical_coverage': c.lexical_coverage, 'similarity': c.similarity} for c in chunks]})
    positive = [result for result in results if result['expected_sections'] or result['expected_pages']]
    negative = [result for result in results if not result['expected_sections'] and not result['expected_pages']]
    hits = sum(result['hit'] for result in positive)
    grounded_hits = sum(result['hit'] and not result['would_abstain'] for result in positive)
    return {'dataset_description': dataset['description'], 'mode': mode,
            'vector_note': 'Synthetic hashed test vectors; NOT Gemini quality calibration' if mode == 'fixture-hybrid'
                else 'Vector weighting disabled' if mode == 'lexical' else 'Live Gemini query embeddings',
            'weights': {'lexical': lexical_weight, 'vector': 0 if mode == 'lexical' else vector_weight, 'rrf_k': settings.AI_RRF_K},
            'top_k': top_k, 'cases': len(results), 'answerable_cases': len(positive), 'hits': hits,
            'retrieval_hit_rate': hits / len(positive) if positive else None,
            'answerable_confidence_acceptance_rate': grounded_hits / len(positive) if positive else None,
            'mean_reciprocal_rank': sum(1 / r['expected_rank'] if r['expected_rank'] else 0 for r in positive) / len(positive) if positive else None,
            'unanswerable_cases': len(negative), 'unanswerable_abstention_rate': sum(r['would_abstain'] for r in negative) / len(negative) if negative else None,
            'results': results}


async def run(args):
    dataset = json.loads(Path(args.cases).read_text())
    database_url = args.database_url or os.environ.get('DATABASE_URL', settings.DATABASE_URL)
    url = make_url(database_url).set(drivername='postgresql+asyncpg')
    admin = None
    name = None
    try:
        if args.fixture:
            admin_url = url.set(drivername='postgresql')
            admin = await asyncpg.connect(admin_url.render_as_string(hide_password=False))
            name = 'portal_eval_' + uuid.uuid4().hex
            await admin.execute(f'CREATE DATABASE "{name}"')
            url = url.set(database=name)
            proc = await asyncio.create_subprocess_exec(sys.executable, '-m', 'alembic', 'upgrade', 'head',
                env={**os.environ, 'DATABASE_URL': url.render_as_string(hide_password=False), 'ENVIRONMENT': 'test'},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            if proc.returncode:
                raise RuntimeError((stdout + stderr).decode())
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            if args.fixture:
                async with sessions() as db, db.begin():
                    await seed_fixture(db, dataset)
            report = await evaluate(sessions, dataset, mode=args.mode, lexical_weight=args.lexical_weight,
                                    vector_weight=args.vector_weight, top_k=args.top_k)
        finally:
            await engine.dispose()
    finally:
        if admin is not None:
            if name:
                await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
            await admin.close()
    output = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'results'}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', default=str(DEFAULT_CASES))
    parser.add_argument('--database-url', help='Prefer DATABASE_URL environment variable rather than putting credentials in argv')
    parser.add_argument('--fixture', action='store_true', help='Create/migrate/seed/drop a NEW random disposable database')
    parser.add_argument('--mode', choices=['lexical', 'fixture-hybrid', 'live'], default='lexical')
    parser.add_argument('--lexical-weight', type=float, default=settings.AI_RRF_LEXICAL_WEIGHT)
    parser.add_argument('--vector-weight', type=float, default=settings.AI_RRF_VECTOR_WEIGHT)
    parser.add_argument('--top-k', type=int, default=settings.AI_RETRIEVAL_TOP_K)
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.mode == 'fixture-hybrid' and not args.fixture:
        parser.error('Synthetic vector mode requires --fixture; never compare hashed vectors with a real corpus')
    if args.mode == 'live' and args.fixture:
        parser.error('Live embeddings must be evaluated against an existing real Gemini-indexed corpus')
    if not 1 <= args.top_k <= 8 or min(args.lexical_weight, args.vector_weight) < 0 or not (args.lexical_weight or args.vector_weight):
        parser.error('Use nonnegative, nonzero weights and top-k between 1 and 8')
    asyncio.run(run(args))


if __name__ == '__main__':
    main()
