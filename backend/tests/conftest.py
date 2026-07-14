"""Test fixtures: an ASGI client, real Supabase-authenticated users, and a
per-test cleanup that leaves the demo table and test users empty afterwards.

Tests exercise the real stack — real GoTrue access tokens, real JWKS
verification, real RLS — rather than faking any of it.
"""

import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

import httpx
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import SUPABASE_URL  # noqa: F401  (imports load the .env)
from app.db import engine
from app.main import app

ANON_KEY = os.environ["SUPABASE_ANON_KEY"]


@pytest_asyncio.fixture
async def created_users() -> AsyncIterator[list[str]]:
    """Track users made during a test; drop them and their rows afterwards."""
    ids: list[str] = []
    yield ids
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE skeleton_ping"))
        if ids:
            await conn.execute(
                text("DELETE FROM auth.users WHERE id = ANY(:ids)"), {"ids": ids}
            )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """ASGI client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def make_user(
    created_users: list[str],
) -> Callable[[], Awaitable[tuple[str, dict[str, str]]]]:
    """Sign a new user up via GoTrue; return (user_id, bearer auth header)."""

    async def _make() -> tuple[str, dict[str, str]]:
        email = f"u{uuid.uuid4().hex}@test.dev"
        async with httpx.AsyncClient(base_url=SUPABASE_URL) as gotrue:
            resp = await gotrue.post(
                "/auth/v1/signup",
                headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
                json={"email": email, "password": "password123"},
            )
        resp.raise_for_status()
        data = resp.json()
        created_users.append(data["user"]["id"])
        return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}

    return _make
