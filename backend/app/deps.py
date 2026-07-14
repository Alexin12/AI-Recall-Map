"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from app.auth import current_user_id
from app.db import connection_for_user


async def user_conn(
    user_id: Annotated[str, Depends(current_user_id)],
) -> AsyncConnection:
    """Request-scoped DB transaction with RLS bound to the current user."""
    async for conn in connection_for_user(user_id):
        yield conn


UserConn = Annotated[AsyncConnection, Depends(user_conn)]
