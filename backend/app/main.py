"""AI Recall Map backend — FastAPI application entry point."""

from datetime import datetime

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from app.deps import UserConn
from app.extraction import router as extraction_router
from app.goals import router as goals_router
from app.materials import router as materials_router
from app.topics import router as topics_router

app = FastAPI(title="AI Recall Map API")
app.include_router(extraction_router)
app.include_router(goals_router)
app.include_router(materials_router)
app.include_router(topics_router)

# Allow the local Next.js dev server to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PingCreate(BaseModel):
    """Request body for creating a ping."""

    message: str


class Ping(BaseModel):
    """A single ping row owned by the authenticated user."""

    id: str
    message: str
    created_at: datetime


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe: proves the API is up."""
    return {"status": "ok"}


@app.get("/pings", response_model=list[Ping])
async def list_pings(conn: UserConn) -> list[Ping]:
    """Return the current user's pings (RLS hides everyone else's)."""
    result = await conn.execute(
        text("SELECT id, message, created_at FROM skeleton_ping ORDER BY created_at")
    )
    return [
        Ping(id=str(r.id), message=r.message, created_at=r.created_at)
        for r in result
    ]


@app.post("/pings", response_model=Ping, status_code=status.HTTP_201_CREATED)
async def create_ping(body: PingCreate, conn: UserConn) -> Ping:
    """Insert a ping owned by the current user (user_id defaults to auth.uid())."""
    result = await conn.execute(
        text(
            "INSERT INTO skeleton_ping (message) VALUES (:message) "
            "RETURNING id, message, created_at"
        ),
        {"message": body.message},
    )
    r = result.one()
    return Ping(id=str(r.id), message=r.message, created_at=r.created_at)
