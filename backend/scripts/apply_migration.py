"""Apply one migration SQL file to the local Supabase Postgres.

The Supabase CLI is not available in this sandbox, so run:
    uv run python scripts/apply_migration.py ../supabase/migrations/<file>.sql
"""

import asyncio
import sys

import asyncpg

from app.config import DATABASE_URL


async def main(path: str) -> None:
    with open(path) as f:
        sql = f.read()
    conn = await asyncpg.connect(DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        await conn.execute(sql)
    finally:
        await conn.close()
    print(f"applied {path}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
