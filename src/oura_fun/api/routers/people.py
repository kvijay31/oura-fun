from __future__ import annotations

import duckdb
from fastapi import APIRouter, Depends

from ..db import get_db
from ..models import PeopleResponse

router = APIRouter(prefix="/people", tags=["people"])

_QUERY = """\
SELECT DISTINCT person_id FROM v_sleep_nightly
UNION
SELECT DISTINCT person_id FROM v_readiness_daily
UNION
SELECT DISTINCT person_id FROM v_activity_daily
ORDER BY 1
"""


@router.get("", response_model=PeopleResponse)
def list_people(conn: duckdb.DuckDBPyConnection = Depends(get_db)) -> PeopleResponse:
    rows = conn.execute(_QUERY).fetchall()
    return PeopleResponse(people=[r[0] for r in rows])
