"""Real PostgreSQL migration lifecycle, independent of ORM create_all.

Opt in with MIGRATION_TEST_DATABASE_URL pointing to a disposable PostgreSQL 16
cluster with pgvector and a CREATEDB user. Each test owns random databases;
it never drops or migrates the database named in that URL.
"""
import asyncio
import os
from pathlib import Path
import sys
import uuid

import asyncpg
import pytest
from sqlalchemy.engine import make_url

ADMIN_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")
pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(not ADMIN_URL, reason="Requires disposable PostgreSQL migration cluster")]
BACKEND = Path(__file__).resolve().parents[1]
SCHEMA = BACKEND.parent / "database" / "schema.sql"
BASELINE = "20260911_0001"
HEAD = "20260918_0006"


async def alembic(url, *args, succeeds=True):
    env = {**os.environ, "DATABASE_URL": url, "ENVIRONMENT": "test"}
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "alembic", *args, cwd=BACKEND, env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = (stdout + stderr).decode()
    assert (proc.returncode == 0) == succeeds, output
    return output


async def catalog(conn):
    """Compare DB semantics, not SQL text or unstable OIDs/column ordering."""
    queries = {
        "columns": """
            SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod),
                   a.attnotnull, a.attidentity, a.attgenerated,
                   pg_get_expr(d.adbin, d.adrelid)
            FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
            WHERE n.nspname='public' AND c.relkind IN ('r','p')
              AND c.relname <> 'alembic_version' AND a.attnum>0 AND NOT a.attisdropped
            ORDER BY c.relname, a.attname
        """,
        "constraints": """
            SELECT c.relname, con.conname, con.contype, pg_get_constraintdef(con.oid)
            FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname <> 'alembic_version'
            ORDER BY c.relname, con.conname
        """,
        "indexes": """
            SELECT tablename, indexname, indexdef FROM pg_indexes
            WHERE schemaname='public' AND tablename <> 'alembic_version'
            ORDER BY tablename, indexname
        """,
        "enums": """
            SELECT t.typname, e.enumlabel FROM pg_enum e
            JOIN pg_type t ON t.oid=e.enumtypid
            JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public'
            ORDER BY t.typname, e.enumsortorder
        """,
        "sequences": """
            SELECT sequencename, data_type::text, start_value, min_value, max_value,
                   increment_by, cycle, cache_size FROM pg_sequences
            WHERE schemaname='public' ORDER BY sequencename
        """,
        "extensions": "SELECT extname, extversion FROM pg_extension ORDER BY extname",
    }
    return {name: [tuple(row) for row in await conn.fetch(sql)] for name, sql in queries.items()}


async def test_baseline_upgrade_adoption_and_downgrade():
    admin_url = make_url(ADMIN_URL).set(drivername="postgresql")
    admin = await asyncpg.connect(admin_url.render_as_string(hide_password=False))
    databases = []
    connections = []
    try:
        for _ in range(2):
            name = "portal_migration_" + uuid.uuid4().hex
            await admin.execute(f'CREATE DATABASE "{name}"')
            databases.append(name)
            conn = await asyncpg.connect(admin_url.set(database=name).render_as_string(hide_password=False))
            connections.append(conn)
        migrated, reference = connections
        url = admin_url.set(drivername="postgresql+asyncpg", database=databases[0]).render_as_string(hide_password=False)
        legacy_url = admin_url.set(drivername="postgresql+asyncpg", database=databases[1]).render_as_string(hide_password=False)

        offline_sql = await alembic(url, "upgrade", "head", "--sql")
        assert 'CREATE EXTENSION IF NOT EXISTS "vector"' in offline_sql
        assert "EXCLUDE USING gist" in offline_sql
        assert "USING GIN (search_tsv)" in offline_sql
        await reference.execute(SCHEMA.read_text())
        # Even two first deployments must not race CREATE alembic_version.
        await asyncio.gather(alembic(url, "upgrade", BASELINE), alembic(url, "upgrade", BASELINE))
        baseline_catalog = await catalog(reference)
        assert await catalog(migrated) == baseline_catalog
        assert await migrated.fetchval("SELECT count(*) FROM users") == 0
        assert await migrated.fetchval("SELECT count(*) FROM courses") == 0
        assert await migrated.fetchval("SELECT count(*) FROM rooms") == 0

        # Exercise the GiST constraint and generated full-text column on the
        # actual baseline, rather than the SQLite test suite's substitutions.
        async with migrated.transaction():
            user = await migrated.fetchval("""INSERT INTO users
                (identifier,email,password_hash,full_name) VALUES
                ('migration-test','migration@example.test','not-a-login-hash','Migration test') RETURNING id""")
            room = await migrated.fetchval("INSERT INTO rooms (room_number,capacity) VALUES ('migration-test',10) RETURNING id")
            insert = """INSERT INTO room_reservations(room_id,reserved_by,purpose,slot_range)
                        VALUES ($1,$2,'migration test',tstzrange('2026-10-02 09:00Z','2026-10-02 10:00Z','[)'))"""
            await migrated.execute(insert, room, user)
            with pytest.raises(asyncpg.ExclusionViolationError):
                async with migrated.transaction():
                    await migrated.execute(insert, room, user)
            event = await migrated.fetchval("""INSERT INTO events
                (created_by,title,description,venue,starts_at,ends_at)
                VALUES ($1,'Test','Test','Test',now(),now()+interval '1 hour') RETURNING id""", user)
            # A different user claiming the same event seat must be excluded.
            other = await migrated.fetchval("""INSERT INTO users
                (identifier,email,password_hash,full_name) VALUES
                ('other-test','other@example.test','not-a-login-hash','Other test') RETURNING id""")
            seat = "INSERT INTO event_rsvps(event_id,user_id,slot_range) VALUES ($1,$2,int4range(1,2,'[)'))"
            await migrated.execute(seat, event, user)
            with pytest.raises(asyncpg.ExclusionViolationError):
                async with migrated.transaction():
                    await migrated.execute(seat, event, other)
            course = await migrated.fetchval("INSERT INTO courses(course_code,title,credit_hours,type) VALUES ('TEST','Test',3,'theory') RETURNING id")
            await migrated.execute("""INSERT INTO academic_resources
                (title,category,course_id,uploader_id,file_key,file_name,file_size_bytes,mime_type)
                VALUES ('Electrical machines','notes',$1,$2,'test','test.pdf',1,'application/pdf')""", course, user)
            assert await migrated.fetchval("SELECT count(*) FROM academic_resources WHERE tsv_search @@ plainto_tsquery('english','machines')") == 1

        await alembic(url, "upgrade", "head")
        assert await migrated.fetchval("SELECT version_num FROM alembic_version") == HEAD
        head_catalog = await catalog(migrated)
        for kind in baseline_catalog:
            if kind != "indexes":
                assert head_catalog[kind] == baseline_catalog[kind]
        assert set(head_catalog["indexes"]) - set(baseline_catalog["indexes"]) == {
            ("notifications", "ix_notifications_recipient_read",
             "CREATE INDEX ix_notifications_recipient_read ON public.notifications USING btree (recipient_id, is_read)")
        }
        # Every future deployment may run this again, including concurrently.
        await asyncio.gather(alembic(url, "upgrade", "head"), alembic(url, "upgrade", "head"))
        assert await catalog(migrated) == head_catalog
        assert await migrated.fetchval("SELECT count(*) FROM users") == 2

        # Adopt a schema.sql-created database explicitly, preserving its rows.
        await reference.execute("INSERT INTO rooms(room_number,capacity) VALUES ('legacy-sentinel',20)")
        output = await alembic(legacy_url, "upgrade", "head", succeeds=False)
        assert "Unversioned, non-empty database" in output
        await alembic(legacy_url, "stamp", BASELINE)
        await alembic(legacy_url, "upgrade", "head")
        assert await reference.fetchval("SELECT capacity FROM rooms WHERE room_number='legacy-sentinel'") == 20
        assert await catalog(reference) == head_catalog

        await alembic(url, "downgrade", "-1")
        await alembic(url, "upgrade", "head")
        # Legacy revision 0006 re-adds the unique as deferrable on this path.
        assert await migrated.fetchval("SELECT version_num FROM alembic_version") == HEAD
        await alembic(url, "downgrade", "base")
        assert await migrated.fetchval("SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'") == 0
        await alembic(url, "upgrade", "head")
        assert await catalog(migrated) == head_catalog
    finally:
        for conn in connections:
            await conn.close()
        for name in databases:
            await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        await admin.close()
