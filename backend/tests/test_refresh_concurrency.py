import asyncio
import os
import uuid

import asyncpg
import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.exceptions import UnauthorizedException
from app.models.auth import RefreshToken
from app.services.auth_service import AuthService
from tests.test_migrations_postgres import alembic


@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("MIGRATION_TEST_DATABASE_URL"), reason="Requires disposable PostgreSQL")
async def test_concurrent_family_replay_cannot_leave_active_descendants():
    admin_url = make_url(os.environ["MIGRATION_TEST_DATABASE_URL"]).set(drivername="postgresql")
    admin = await asyncpg.connect(admin_url.render_as_string(hide_password=False))
    name = "refresh_test_" + uuid.uuid4().hex
    engine = None
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        url = admin_url.set(drivername="postgresql+asyncpg", database=name).render_as_string(hide_password=False)
        await alembic(url, "upgrade", "head")
        engine = create_async_engine(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        from sqlalchemy import text
        async with factory() as db:
            user = await db.scalar(text("""INSERT INTO users(identifier,email,password_hash,full_name)
                VALUES ('test','test@example.test','not-a-password','Test') RETURNING id"""))
            first = await AuthService(db)._issue_refresh_token(user)
            independent = await AuthService(db)._issue_refresh_token(user)
            await db.commit()
            _, current = await AuthService(db).refresh_access_token(first)

        async def rotate(token):
            async with factory() as db:
                try:
                    return await AuthService(db).refresh_access_token(token)
                except UnauthorizedException:
                    return None

        await asyncio.wait_for(asyncio.gather(rotate(first), rotate(current)), timeout=10)
        assert await rotate(current) is None
        async with factory() as db:
            live = list((await db.scalars(select(RefreshToken).where(RefreshToken.is_revoked.is_(False)))).all())
            assert len(live) == 1  # independent device family survives
        assert await rotate(independent) is not None

        # Two simultaneous requests with the SAME token also kill the family
        # once the second request observes the committed rotation.
        async with factory() as db:
            shared = await AuthService(db)._issue_refresh_token(user)
            await db.commit()
        results = await asyncio.wait_for(asyncio.gather(rotate(shared), rotate(shared)), timeout=10)
        assert sum(item is not None for item in results) == 1
        successor = next(item[1] for item in results if item is not None)
        assert await rotate(successor) is None
    finally:
        if engine is not None:
            await engine.dispose()
        await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.close()
