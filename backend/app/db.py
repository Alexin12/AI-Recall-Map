"""Async database engine and a request-scoped connection that enforces RLS.

Every request runs its queries as the Postgres ``authenticated`` role with the
user's id injected into ``request.jwt.claims``, so Supabase Row Level Security
policies using ``auth.uid()`` apply exactly as they would through PostgREST.
"""

import json
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL)


async def connection_for_user(user_id: str) -> AsyncIterator[AsyncConnection]:
    """Yield a transaction scoped to ``user_id`` with RLS enforced.

    Opens a transaction, switches to the non-superuser ``authenticated`` role
    (superusers bypass RLS), and sets the JWT claims that ``auth.uid()`` reads.
    """
    claims = json.dumps({"sub": user_id, "role": "authenticated"})
    async with engine.connect() as conn:
        async with conn.begin():
            await conn.execute(text("SET LOCAL ROLE authenticated"))#Get ride of super user proof
            await conn.execute(
                text("SELECT set_config('request.jwt.claims', :claims, true)"),
                {"claims": claims},#Put a normal user identity 
            )
            yield conn
