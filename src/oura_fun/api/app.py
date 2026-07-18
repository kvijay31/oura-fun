"""FastAPI application for the F9.2 backend API layer."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import get_db_path, init_db
from .routers import activity, people, readiness, sleep

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ready, reason = init_db()
    if ready:
        logger.info("DB initialised")
    else:
        logger.warning("DB not ready: %s — data endpoints will return 503", reason)
    yield


app = FastAPI(
    title="Oura Fun API",
    description="FastAPI backend for the oura-fun dashboard, reading DuckDB views.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

api = FastAPI(title="Oura Fun API v1")
api.include_router(sleep.router)
api.include_router(readiness.router)
api.include_router(activity.router)
api.include_router(people.router)

app.mount("/api/v1", api)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    db_path = get_db_path()
    return {"status": "ok", "db": str(db_path), "db_exists": db_path.exists()}
