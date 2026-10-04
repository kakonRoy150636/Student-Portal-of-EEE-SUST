# Grounded academic assistant

`POST /api/v1/ai/query` requires authentication and accepts `prompt` (2–1000 characters) and `course_code`. The frontend `/ai` screen calls the endpoint and displays the returned source locations and quota errors.

## Retrieval and sources

- PostgreSQL joins chunks to their course's knowledge documents. Sources from other courses, sources without a page/section, and detected instruction-bearing sources are excluded.
- Full-text candidate search uses English stemming and a query-term OR search. Exact 768-dimensional cosine search only compares embeddings stamped with the configured model. Legacy unstamped embeddings are never mixed with new vectors.
- Weighted reciprocal rank fusion merges up to 30 candidates per branch: `lexical_weight/(k+rank) + vector_weight/(k+rank)`. Defaults are 1:1, `k=60`, top 5.
- Confidence is separate from rank. A source needs query-keyword coverage of at least 0.6 (two matching keywords where available), or cosine similarity at least 0.8. Only confident sources reach generation. These are starting thresholds, requiring calibration against your actual syllabus.
- Gemini receives source IDs (`S1`, etc.), authentic document titles and page/section labels. Returned citations are resolved server-side against those IDs; the model cannot supply fabricated source metadata. Nonempty source IDs and matching inline markers are mandatory. Invalid citations, low confidence, empty corpus or provider abstention return exactly **"I could not find this in the syllabus"**, with no invented citations.
- A source-ID check proves provenance, not semantic correctness of each generated sentence. The prompt requires every factual statement to be supported; faculty-reviewed live evaluations are still needed.

## Injection boundary

Retrieved text, titles, section labels and user questions are explicitly untrusted data in a separate Gemini system instruction. Context is JSON-encoded, with no tools or external-URL execution. Chunk sanitation normalizes Unicode, removes control characters/HTML/role delimiters, bounds source length and rejects common instruction/secret-exfiltration patterns before truncation. This is defense in depth; pattern matching cannot identify every possible injection. Sensitive credentials never enter source context or response logs.

## Configuration and spending

Run `alembic upgrade head` first. Set the backend `GEMINI_API_KEY`; the supported REST adapter uses `gemini-2.5-flash-lite` and `gemini-embedding-001` with thinking disabled. No API key is sent to the browser. See root `.env.example` for all options.

| Setting | Default |
| --- | --- |
| `AI_DAILY_USER_QUOTA` | 20 accepted questions per user |
| `AI_GLOBAL_DAILY_CAP_MICRO_USD` | 1,000,000 = USD 1.00 |
| `AI_INPUT_MICRO_USD_PER_MILLION` | 1,000,000 |
| `AI_OUTPUT_MICRO_USD_PER_MILLION` | 5,000,000 |
| `AI_EMBED_MICRO_USD_PER_MILLION` | 150,000 |
| `AI_MAX_OUTPUT_TOKENS` | 768 |

These token rates are conservative **price ceilings**, not Google's published pricing. Review them against your provider billing tier; a cost cap is valid only when ceilings cover the billed rates. Model changes require reviewing the adapter's prices, input/output bounds and thinking behavior.

Redis Lua atomically admits requests and reserves maximum possible cost **before any provider call** across API replicas. Generation settles against usage metadata; missing metadata is charged at its full bound. Embeddings use conservative UTF-8-length token bounds. Known no-generation retrieval paths release unused money but still count the question. Timeouts, interrupted requests, malformed responses or ambiguous provider failures retain their reservation; they are not automatically retried. Settlement is idempotent. No request is admitted when spent + reserved + proposed cost exceeds the cap.

Quota and cap windows reset at **midnight Asia/Dhaka**. Redis keys use a common cluster hash slot and persist for an extra day for late settlement. HTTP 429 includes `Retry-After`; Redis failures fail closed with HTTP 503 in every environment. Trusted ingestion/evaluation shares the global cost cap, but not student daily quotas. The separate existing ten-per-minute AI request throttle remains active.

Both Compose stacks persist Redis with AOF, `appendfsync always` and `noeviction` to protect accounting. Keep host clocks synchronized and Redis data intact; deleting/restoring old accounting keys resets usage and undermines the cap. In-flight requests are attributed to their admission date. Provider billing dashboards remain the authority for actual charges.

## Ingest real material

This repository contains no official SUST syllabus corpus. Create a `knowledge_documents` record referencing the correct course, title and file path through trusted administration/import tooling. Split real source text into chunks of at most 1800 UTF-8 bytes, preserving authentic page numbers or section labels. The worker task is:

```python
from app.tasks.ai_ingestion import ingest_document_chunk
ingest_document_chunk.delay(str(document_id), source_text, page_number=7, section="Circuit laws")
```

It validates metadata/text, reserves embedding cost, obtains a normalized 768-dimensional retrieval-document vector and persists its model provenance. A repeated already-ingested chunk returns its ID. Do not repeatedly retry uncertain paid attempts. Existing source text needs authentic locations and re-embedding before the vector branch can use it; no guessed locations or arbitrary vector-model stamps are migrated onto old rows. Lexical-only chunks are supported with nullable embeddings.

## 25-question retrieval evaluation

`backend/evals/academic_questions.json` contains 20 answerable and 5 unsupported question/expected-answer pairs plus a **synthetic example corpus**. It is not an official curriculum or an answer-generation benchmark. The script reports hit@k, mean reciprocal rank, confidence acceptance, unsupported abstention and each retrieved source/score.

From `backend`, point `DATABASE_URL` at a disposable PostgreSQL+pgvector cluster whose user has CREATEDB. `--fixture` creates, migrates, seeds and drops a new random database; it never seeds your existing database:

```bash
python -m evals.retrieval_eval --fixture --mode lexical --output lexical-report.json
python -m evals.retrieval_eval --fixture --mode fixture-hybrid --lexical-weight 1 --vector-weight 1 --output hybrid-report.json
```

Fixture-hybrid uses deterministic hashed keyword vectors to exercise both PostgreSQL branches and RRF. These vectors **do not measure Gemini semantic retrieval quality**. To tune real weights, replace the cases with faculty-reviewed questions, expected answers and authentic source locations; set `expected_document_name` per case if needed, `expected_sections` and/or `expected_pages`. Use the existing migrated corpus, matching Gemini-indexed chunks, API key and Redis:

```bash
python -m evals.retrieval_eval --cases real-reviewed-cases.json --mode live --lexical-weight 2 --vector-weight 1 --output live-report.json
```

Live mode incurs budgeted query-embedding costs, never generates answers and never writes corpus rows. Compare runs at fixed top-k and `AI_RRF_K`; inspect misses, confidence false positives and MRR as well as aggregate hit-rate. CI publishes its fixture evaluation as a backend-test artifact.

## Recorded checks (2026-10-04)

- Full backend: **228 passed, 1 skipped, 4 expected failures**. Skip requires MinIO; existing expected failures concern lab benches/prerequisites/credit limits.
- New AI checks: real pgvector/FTS retrieval, source ownership/course scope, injection exclusion, citations, low-confidence abstention, ingestion provenance, Redis concurrent quotas/caps, Dhaka rollover, fail-closed store errors and provider accounting/transport.
- Frontend: **19 unit tests and 4 browser checks**; browser APIs are explicitly mocked. Lint, typecheck and production build pass.
- 25-case synthetic evaluation (stable fixture IDs): lexical **20/20 hit@5**, MRR **0.975**; hybrid **20/20 hit@5**, MRR **1.000**; both abstain on **5/5** unsupported questions. Saved reports: `AI_EVAL_LEXICAL.json` and `AI_EVAL_HYBRID.json`.
- Both Docker builds pass; Trivy reports **0 HIGH/CRITICAL** in both images, npm audit reports **0 vulnerabilities**, and pip-audit reports **no known vulnerabilities**. Both Compose configurations and actionlint pass.
- Live Gemini answer/embedding quality and real syllabus hit-rate have **not** been verified: they require configured credentials and a reviewed production corpus. HTTP transport tests use deterministic provider responses.
