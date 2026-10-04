"""Course-scoped PostgreSQL full-text + exact pgvector search, weighted RRF."""
import math
import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import settings

NOT_FOUND = "I could not find this in the syllabus"
STOPWORDS = set("a an the is are was were be been being what which how when where why who does do did can could would should of to in on for from and or with about explain describe define give list me please course syllabus according tell it its this that find".split())
INJECTION = re.compile(
    r"ignore\s+(?:all\s+|the\s+)?(?:previous|prior|above|system)\s+(?:instructions|prompts|rules)|"
    r"(?:reveal|print|expose|disclose)\s+(?:the\s+)?(?:system\s+prompt|api\s+key|secret)|"
    r"(?:system|developer|assistant)\s*:|you\s+are\s+now|override\s+(?:the\s+)?(?:instructions|rules)|"
    r"<\|(?:im_start|system|assistant)|\[INST\]", re.IGNORECASE,
)


def clean_text(value: str, limit: int = 2000) -> str:
    normalized = unicodedata.normalize('NFKC', value)
    normalized = ''.join(char for char in normalized if not unicodedata.category(char).startswith('C') or char in '\n\t')
    normalized = re.sub(r'<[^>]*>', ' ', normalized)
    return normalized.replace('```', '').strip()[:limit]


def sanitize_chunk(value: str) -> str | None:
    # Detect against the WHOLE normalized source before truncation/removing tags.
    normalized = unicodedata.normalize('NFKC', value)
    normalized = ''.join(c for c in normalized if not unicodedata.category(c).startswith('C') or c in '\n\t')
    if INJECTION.search(normalized):
        return None
    return clean_text(normalized) or None


def keywords(query: str) -> set[str]:
    return {word for word in re.findall(r'[^\W\d_]{2,}', query.lower(), re.UNICODE) if word not in STOPWORDS}


def normalize_vector(values: list[float]) -> list[float]:
    if len(values) != 768 or any(not math.isfinite(x) for x in values):
        raise ValueError("Invalid embedding")
    norm = math.sqrt(sum(x*x for x in values))
    if not norm:
        raise ValueError("Empty embedding")
    return [x / norm for x in values]


@dataclass
class RetrievedChunk:
    id: str
    document_name: str
    content: str
    page_number: int | None
    section: str | None
    lexical_coverage: float = 0.0
    similarity: float = 0.0
    rrf_score: float = 0.0

    @property
    def confident(self):
        return (self.lexical_coverage >= settings.AI_MIN_LEXICAL_COVERAGE or
                self.similarity >= settings.AI_MIN_VECTOR_SIMILARITY)


SOURCE_JOIN = """
FROM document_chunks dc
JOIN knowledge_documents kd ON kd.id = dc.document_id
JOIN courses c ON c.id = kd.course_id
WHERE replace(upper(c.course_code), ' ', '') = :course
AND (dc.page_number IS NOT NULL OR length(trim(coalesce(dc.section, ''))) > 0)
"""
FIELDS = "dc.id, dc.content, dc.page_number, dc.section, kd.title AS document_name"


def fuse_rankings(lexical, vector, *, lexical_weight=None, vector_weight=None, rrf_k=None):
    lw = settings.AI_RRF_LEXICAL_WEIGHT if lexical_weight is None else lexical_weight
    vw = settings.AI_RRF_VECTOR_WEIGHT if vector_weight is None else vector_weight
    k = settings.AI_RRF_K if rrf_k is None else rrf_k
    merged: dict[str, RetrievedChunk] = {}
    for weight, rows in [(lw, lexical), (vw, vector)]:
        if not weight:
            continue
        for rank, row in enumerate(rows, 1):
            current = merged.setdefault(row.id, RetrievedChunk(**vars(row)))
            current.rrf_score += weight / (k + rank)
            current.similarity = max(current.similarity, row.similarity)
            current.lexical_coverage = max(current.lexical_coverage, row.lexical_coverage)
    return sorted(merged.values(), key=lambda chunk: (-chunk.rrf_score, chunk.id))


class AcademicRetriever:
    def __init__(self, db):
        self.db = db

    async def has_sources(self, course: str) -> bool:
        return bool(await self.db.scalar(text("SELECT EXISTS (SELECT 1 " + SOURCE_JOIN + ")"), {"course": course.replace(' ', '').upper()}))

    async def has_vectors(self, course: str) -> bool:
        return bool(await self.db.scalar(text("SELECT EXISTS (SELECT 1 " + SOURCE_JOIN +
            " AND dc.embedding IS NOT NULL AND dc.embedding_model = :model)"),
            {"course": course.replace(' ', '').upper(), "model": settings.GEMINI_EMBEDDING_MODEL}))

    async def retrieve(self, query: str, course: str, vector=None, **weights):
        terms = keywords(query)
        params = {"course": course.replace(' ', '').upper(), "terms": ' OR '.join(sorted(terms))}
        lexical_rows = []
        if terms:
            lexical_rows = (await self.db.execute(text(f"SELECT {FIELDS}, ts_rank_cd(dc.tsv_content, websearch_to_tsquery('english', :terms)) AS rank " + SOURCE_JOIN +
                " AND dc.tsv_content @@ websearch_to_tsquery('english', :terms) ORDER BY rank DESC, dc.id LIMIT 30"), params)).mappings().all()
        vector_rows = []
        if vector is not None:
            params.update(vector='[' + ','.join(str(x) for x in normalize_vector(vector)) + ']', model=settings.GEMINI_EMBEDDING_MODEL)
            vector_rows = (await self.db.execute(text(f"SELECT {FIELDS}, 1 - (dc.embedding <=> CAST(:vector AS vector)) AS similarity " + SOURCE_JOIN +
                " AND dc.embedding IS NOT NULL AND dc.embedding_model = :model ORDER BY dc.embedding <=> CAST(:vector AS vector), dc.id LIMIT 30"), params)).mappings().all()
        def rows_to_chunks(rows):
            chunks = []
            for row in rows:
                body = sanitize_chunk(row['content'])
                name = sanitize_chunk(row['document_name'])
                section = sanitize_chunk(row['section']) if row['section'] else None
                if not body or not name or not (row['page_number'] or section):
                    continue
                body_terms = keywords(body)
                coverage = len(terms & body_terms) / len(terms) if terms else 0
                # Single vague word matches cannot certify a whole answer.
                if len(terms & body_terms) < min(2, len(terms)):
                    coverage = 0
                chunks.append(RetrievedChunk(str(row['id']), clean_text(name, 255), body,
                    row['page_number'], clean_text(section, 255) if section else None,
                    coverage, max(0, float(row.get('similarity', 0) or 0))))
            return chunks
        return fuse_rankings(rows_to_chunks(lexical_rows), rows_to_chunks(vector_rows), **weights)[:settings.AI_RETRIEVAL_TOP_K]
