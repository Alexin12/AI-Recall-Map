#!/bin/sh
# Test step for the no-mistakes gate (M3 e2e): backend pytest + frontend
# Playwright e2e. Assumes Supabase is already running (`supabase start`),
# left up separately per the e2e design — this script does not start or
# stop it.
set -eu

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

echo "==> Backend: pytest"
(cd backend && UV_CACHE_DIR="${TMPDIR:-/tmp}/uv-cache" uv run pytest)

echo "==> Frontend: Playwright e2e"
(cd frontend && pnpm test:e2e)
