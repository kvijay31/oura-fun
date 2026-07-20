"""FastAPI app — JSON API for the Phase 9 dashboard."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import db
from . import access as ac
from .chat import router as chat_router
from .db import DBLockedError
from . import refresh as _refresh

log = logging.getLogger(__name__)

app = FastAPI(title="oura-fun API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.exception_handler(DBLockedError)
def _db_locked_handler(request: Request, exc: DBLockedError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "db_locked",
            "message": "Database is locked — a data refresh is in progress. Retry in a few minutes.",
            "refresh_running": _refresh.any_running(),
        },
    )

_DEFAULT_DAYS = 30
_PERSONAL_INFO_URL = "https://api.ouraring.com/v2/usercollection/personal_info"


def _date_window(start: str | None, end: str | None) -> tuple[str, str]:
    end_dt = date.fromisoformat(end) if end else date.today()
    start_dt = date.fromisoformat(start) if start else end_dt - timedelta(days=_DEFAULT_DAYS)
    return str(start_dt), str(end_dt)


def _validate_token(token: str) -> dict[str, Any]:
    """Hit Oura personal_info to verify token. Returns the JSON payload on success."""
    try:
        resp = httpx.get(
            _PERSONAL_INFO_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Oura API: {exc}")
    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Token is invalid or expired (Oura API returned 401)")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Oura API returned {resp.status_code}")
    return resp.json()


def _run_backfill(person_id: str, token: str) -> None:
    """Fire off a full backfill for one person (runs in a FastAPI background task)."""
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent.parent.parent
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from oura_fun import db as dbmod
    from scripts.backfill import backfill_person  # type: ignore[import]

    start = date(2020, 1, 1)
    today = date.today()
    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)

    conn = dbmod.connect()
    dbmod.init_db(conn)
    log.info("Starting backfill for %s", person_id)
    try:
        backfill_person(person_id, token, conn, start, today, fetched_at)
        log.info("Backfill complete for %s", person_id)
    except Exception as exc:
        log.error("Backfill failed for %s: %s", person_id, exc)
    finally:
        conn.close()


@app.get("/api/people")
def list_people() -> dict[str, list[str]]:
    return {"people": db.list_people()}


class AddPersonRequest(BaseModel):
    person_id: str
    token: str


@app.post("/api/people", status_code=201)
def add_person(body: AddPersonRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Validate an Oura token, persist it in the people registry, and kick off an initial backfill."""
    person_id = body.person_id.strip().lower()
    if not person_id:
        raise HTTPException(status_code=422, detail="person_id must not be empty")
    token = body.token.strip()
    if not token:
        raise HTTPException(status_code=422, detail="token must not be empty")

    # Live validation against Oura API
    personal_info = _validate_token(token)

    # Persist to people registry
    import oura_fun.db as dbmod
    conn = dbmod.connect()
    dbmod.init_schema(conn)
    dbmod.upsert_person(conn, person_id, token)
    conn.close()

    # Trigger backfill in background — returns immediately to the browser
    background_tasks.add_task(_run_backfill, person_id, token)

    return {
        "person_id": person_id,
        "email": personal_info.get("email"),
        "age": personal_info.get("age"),
        "backfill": "started",
    }


@app.get("/api/sleep/{person_id}")
def get_sleep(
    person_id: str,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    viewer_id: str | None = Query(default=None),
) -> dict[str, Any]:
    s, e = _date_window(start, end)
    role = ac.get_role(viewer_id, person_id)
    records = ac.filter_records(db.get_sleep(person_id, s, e), role)
    return {"person_id": person_id, "start": s, "end": e, "viewer_role": role, "records": records}


@app.get("/api/readiness/{person_id}")
def get_readiness(
    person_id: str,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    viewer_id: str | None = Query(default=None),
) -> dict[str, Any]:
    s, e = _date_window(start, end)
    role = ac.get_role(viewer_id, person_id)
    records = ac.filter_records(db.get_readiness(person_id, s, e), role)
    return {"person_id": person_id, "start": s, "end": e, "viewer_role": role, "records": records}


@app.get("/api/activity/{person_id}")
def get_activity(
    person_id: str,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    viewer_id: str | None = Query(default=None),
) -> dict[str, Any]:
    s, e = _date_window(start, end)
    role = ac.get_role(viewer_id, person_id)
    records = ac.filter_records(db.get_activity(person_id, s, e), role)
    return {"person_id": person_id, "start": s, "end": e, "viewer_role": role, "records": records}


@app.get("/api/compare")
def compare(
    metric: str = Query(..., description="sleep | readiness | activity"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    viewer_id: str | None = Query(default=None),
) -> dict[str, Any]:
    s, e = _date_window(start, end)
    people = db.list_people()
    fetch = {"sleep": db.get_sleep, "readiness": db.get_readiness, "activity": db.get_activity}.get(metric)
    if fetch is None:
        return {"error": f"unknown metric {metric!r}"}
    result = {
        p: ac.filter_records(fetch(p, s, e), ac.get_role(viewer_id, p))
        for p in people
    }
    return {"metric": metric, "start": s, "end": e, "people": result}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/refresh")
def refresh_all() -> dict[str, Any]:
    """Trigger incremental refresh for all configured people (non-blocking)."""
    return {"status": _refresh.start_refresh()}


@app.post("/api/refresh/{person_id}")
def refresh_person(person_id: str) -> dict[str, Any]:
    """Trigger incremental refresh for a specific person (non-blocking)."""
    return {"status": _refresh.start_refresh(person_id)}


@app.get("/api/refresh/status")
def refresh_status() -> dict[str, Any]:
    """Get current refresh state — running flag and last_refresh per person."""
    return {"refresh": _refresh.get_status(), "any_running": _refresh.any_running()}
