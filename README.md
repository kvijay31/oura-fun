# oura-fun

Personal Oura Ring data pipeline: ingest → store → analyze/visualize/chat, all running locally.

Built as three layers, in this order:

1. **API client** (`src/oura_fun/`) — a typed `httpx` wrapper around the Oura v2 API
   (`client.py`), with response models and endpoint wrappers split by shape
   (`daily.py`, `timeseries.py`, `events.py`, `models.py`).
2. **Storage** — DuckDB, single file (`oura.duckdb`, gitignored). Raw JSON is kept
   forever per fetch (`db.py`, `raw_*` tables); derived views (`views.py`,
   `v_*`) dedupe to the latest fetch per day and flatten JSON into typed
   columns. Views are the only thing downstream consumers read.
3. **Consumers** — a FastAPI JSON layer (`src/oura_fun/api/`) backing the
   dashboard + chat UI (`frontend/`, Next.js), and an MCP server
   (`mcp_server.py`) exposing the same views as tools for Claude Desktop.

See `todo.md` for the original build plan and `FEATURES.md` for the full
feature breakdown with dependencies.

## Setup

```bash
uv sync
cp .env.example .env
# edit .env: one line per person, OURA_TOKEN_<NAME>=<token from
# cloud.ouraring.com/personal-access-tokens>
uv run python scripts/check_auth.py   # confirms every configured token works
```

## Ingest your data

```bash
uv run python scripts/init_schema.py       # creates raw tables + views in oura.duckdb
uv run python scripts/backfill.py          # full history, all configured people
uv run python scripts/incremental.py       # last 14 days (re-run periodically — Oura revises past days)
uv run python scripts/sanity_check.py --db-path oura.duckdb   # gap/anomaly checks, exits 1 on failure
```

`backfill.py` and `incremental.py` are idempotent (`ON CONFLICT DO NOTHING`) — safe to re-run.

## Run the dashboard + chat

```bash
uv run uvicorn src.oura_fun.api.app:app --port 8000   # backend
cd frontend && npm install && npm run dev              # frontend, http://localhost:3000
```

Pages: Overview, Sleep, Readiness, Activity, Compare, Chat. All read from the
DuckDB views above — no live Oura API calls happen here.

## Use it from Claude Desktop

```bash
uv run python -m oura_fun.mcp_server
```

Wire it into Claude Desktop's MCP config (see F3.5 in `FEATURES.md`) to ask
things like "why has my HRV been low this week" directly in conversation.
Tools: `query_sleep`, `query_readiness`, `query_activity`, `compare_people`,
`baseline`, `run_sql` (read-only). Resource: `oura://data-dictionary` explains
every field, including the Oura contributor sub-scores.

## Tests

```bash
uv run pytest
```

All client/parsing/API logic is covered with mocked HTTP responses. DB and
view logic is tested against real DuckDB (not mocked).

## Multi-person

Add more people by adding another `OURA_TOKEN_<NAME>` line to `.env`, then
running `backfill.py` again — it backfills every configured token. By default
everyone with a token in `.env` has full access to their own data; the
`OURA_OWNERS` env var (comma-separated person IDs) controls who friends
outside the household see full biometrics for vs. scores-only
(`src/oura_fun/api/access.py`).
