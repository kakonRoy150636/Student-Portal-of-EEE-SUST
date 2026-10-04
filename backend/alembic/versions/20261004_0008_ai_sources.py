"""Citable RAG chunk locations, embedding provenance and retrieval indexes."""
from alembic import op

revision = "20261004_0008"
down_revision = "20261003_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE document_chunks ADD COLUMN page_number INTEGER, ADD COLUMN section VARCHAR(255), ADD COLUMN embedding_model VARCHAR(100)")
    op.execute("ALTER TABLE document_chunks ADD CONSTRAINT ck_document_chunk_page CHECK (page_number IS NULL OR page_number > 0)")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding DROP NOT NULL")
    op.execute("CREATE INDEX ix_document_chunks_tsv ON document_chunks USING GIN (tsv_content)")
    op.execute("CREATE INDEX ix_document_chunks_document ON document_chunks (document_id)")
    op.execute("CREATE INDEX ix_knowledge_documents_course ON knowledge_documents (course_id)")
    # The corpus is small: exact cosine search avoids approximate/filter recall
    # failures until a measured production workload justifies an ANN index.


def downgrade():
    op.execute("DROP INDEX ix_knowledge_documents_course")
    op.execute("DROP INDEX ix_document_chunks_document")
    op.execute("DROP INDEX ix_document_chunks_tsv")
    # Refuse a lossy downgrade if lexical-only chunks have since been ingested.
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding SET NOT NULL")
    op.execute("ALTER TABLE document_chunks DROP CONSTRAINT ck_document_chunk_page")
    op.execute("ALTER TABLE document_chunks DROP COLUMN embedding_model, DROP COLUMN section, DROP COLUMN page_number")
