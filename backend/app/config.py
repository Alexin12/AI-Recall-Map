"""Application settings, read from the environment with local-dev defaults."""

import os

from dotenv import load_dotenv

# Load backend/.env (gitignored) so local secrets reach os.environ.
load_dotenv()

# Local Supabase Postgres (see supabase/config.toml -> [db] port 54322).
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres",
)

# Base URL of the Supabase API gateway (Kong). Used to reach GoTrue's JWKS
# endpoint for verifying access-token signatures.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
