from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

import duckdb
from fastapi import APIRouter, Depends, Query

from ..db import get_db
from ..models import ActivityRecord, ActivityResponse

router = APIRouter(prefix="/activity", tags=["activity"])

_QUERY = """\
SELECT *
FROM v_activity_daily
WHERE person_id = ?
  AND day >= ?
  AND day <= ?
ORDER BY day
"""


def _rows(result: duckdb.DuckDBPyRelation) -> list[dict]:
    cols = [d[0] for d in result.description]
    return [dict(zip(cols, row)) for row in result.fetchall()]


@router.get("", response_model=ActivityResponse)
def query_activity(
    person_id: Annotated[str, Query(description="Person identifier")],
    start: Annotated[Optional[date], Query(description="Start date (inclusive), ISO 8601")] = None,
    end: Annotated[Optional[date], Query(description="End date (inclusive), ISO 8601")] = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_db),
) -> ActivityResponse:
    start_date = start or date.fromordinal(date.today().toordinal() - 30)
    end_date = end or date.today()
    result = conn.execute(_QUERY, [person_id, start_date, end_date])
    records = [ActivityRecord.from_row(r) for r in _rows(result)]
    return ActivityResponse(person_id=person_id, records=records)
