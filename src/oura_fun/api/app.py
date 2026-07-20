"""FastAPI app — JSON API for the Phase 9 dashboard."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import db
from . import access as ac
from .chat import router as chat_router
from .db import DBLockedError
from . import refresh as _refresh

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


def _date_window(start: str | None, end: str | None) -> tuple[str, str]:
    end_dt = date.fromisoformat(end) if end else date.today()
    start_dt = date.fromisoformat(start) if start else end_dt - timedelta(days=_DEFAULT_DAYS)
    return str(start_dt), str(end_dt)


@app.get("/api/people")
def list_people() -> dict[str, list[str]]:
    return {"people": db.list_people()}


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
