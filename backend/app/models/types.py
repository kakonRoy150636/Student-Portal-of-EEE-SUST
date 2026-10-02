"""Custom column types shared by the ORM models.

``Vector`` exists because pgvector's own Python package is not a dependency:
the only thing needed here is a column that renders as ``vector(N)`` on
Postgres, round-trips ``list[float]`` values, and degrades to a text column on
SQLite (which accepts any declared type name) so the test suite can create the
same schema without the extension.

The previous state of the world was worse than having no type at all:
``document_chunks.embedding`` was declared ``vector(768) NOT NULL`` in
schema.sql but not mapped in the ORM, so the ingestion task could not write a
chunk and a ``SELECT *`` returned a column the mapper did not know about.
"""

from __future__ import annotations

from sqlalchemy import ARRAY, JSON, String
from sqlalchemy.types import TypeDecorator, UserDefinedType


class Vector(UserDefinedType):
    """A fixed-width pgvector column that also works on SQLite."""

    cache_ok = True

    def __init__(self, dim: int = 768) -> None:
        self.dim = dim

    def get_col_spec(self, **kw) -> str:  # noqa: D102 - SQLAlchemy hook
        return f"vector({self.dim})"

    def bind_processor(self, dialect):
        """Serialise a Python list to the literal pgvector accepts."""

        def process(value):
            if value is None or isinstance(value, str):
                return value
            return "[" + ",".join(f"{float(item):.8f}" for item in value) + "]"

        return process

    def result_processor(self, dialect, coltype):
        """Parse the textual form pgvector returns us (asyncpg has no codec)."""

        def process(value):
            if value is None or isinstance(value, list):
                return value
            text = str(value).strip()
            if not text or text == "[]":
                return []
            try:
                return [float(item) for item in text.strip("[]").split(",")]
            except ValueError:
                return None

        return process


class StringArray(TypeDecorator):
    """A ``list[str]`` column that is TEXT[] on Postgres and JSON elsewhere.

    SQLAlchemy's ``postgresql.ARRAY`` cannot bind on SQLite at all (sqlite3
    rejects a Python list), so any test that touches a row with an array column
    failed before it could assert anything -- which is why the career and
    faculty-profile tables had no coverage. The Postgres column type is
    unchanged (``TEXT[]``), because ``load_dialect_impl`` still selects ARRAY
    for that dialect.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String(200)))
        return dialect.type_descriptor(JSON())
