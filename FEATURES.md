# Feature Breakdown

Derived from `todo.md`. Each feature is scoped to be pickable by a single agent:
self-contained, with explicit dependencies and a done-condition. Build order
follows the todo: Phase 0-3 are required and sequential-ish, Phase 4-8 are
optional and only start once Phase 3 is stable.

Legend: **Depends on** lists blocking features by ID. Features with no shared
dependency chain can run in parallel.

---

## Phase 0 — Setup

### F0.1 Project scaffolding & credentials
- Initialize `uv` project, `pyproject.toml`, directory layout (`src/`, `scripts/`, `tests/`).
- `.env.example` documenting `OURA_TOKEN_<PERSON>` convention.
- `.gitignore`: `.env`, `*.duckdb`, `__pycache__/`, etc.
- Env loader (`pydantic-settings` or `python-dotenv`) that reads one token per person.
- Script/command to hit `GET /v2/usercollection/personal_info` and confirm each configured token authenticates.
- **Depends on:** nothing. **Blocks:** everything else.
- **Needs from user:** Oura personal access token(s).

---

## Phase 1 — API client

### F1.1 HTTP client core
- `httpx`-based client: bearer auth injection, retry policy, 429 backoff (respect `Retry-After` if present).
- Cursor pagination helper (loops on `next_token`).
- Date-range chunking helper (splits `start_date`/`end_date` into ≤30-day windows where the endpoint requires it).
- Unit tests against mocked responses (pagination, backoff, chunking).
- **Depends on:** F0.1.

### F1.2 Endpoint wrappers — daily metrics
- `daily_sleep`, `daily_readiness`, `daily_activity`, `daily_stress`, `daily_spo2`, `sleep_time`.
- Pydantic response models per endpoint.
- **Depends on:** F1.1.

### F1.3 Endpoint wrappers — detailed/time-series
- `sleep` (per-period detail), `heartrate` (uses `start_datetime`/`end_datetime`, 5-min granularity — different pagination shape than the daily ones).
- Pydantic response models.
- **Depends on:** F1.1.

### F1.4 Endpoint wrappers — events & metadata
- `workout`, `session`, `enhanced_tag`, `personal_info`.
- Pydantic response models.
- **Depends on:** F1.1.

*(F1.2/F1.3/F1.4 can run in parallel — they only share F1.1's client, no cross-dependency.)*

---

## Phase 2 — Ingestion

### F2.1 DuckDB raw schema
- One raw table per endpoint: `(person_id, natural_key, day, payload JSON, fetched_at)`.
- Schema migration/init script.
- **Depends on:** F0.1.

### F2.2 Derived views
- `v_sleep_nightly`, `v_readiness_daily`, `v_activity_daily` (and siblings as needed) — dedup to latest `fetched_at` per `(person_id, natural_key)`, flatten JSON on read.
- **Depends on:** F2.1.

### F2.3 Backfill script
- Pull full history per configured token, write raw rows via F2.1 schema.
- **Depends on:** F1.2, F1.3, F1.4, F2.1.

### F2.4 Incremental script
- Re-pull last 14 days daily (catches Oura's backfills/revisions) — same write path as F2.3.
- **Depends on:** F2.3.

### F2.5 Scheduling
- Cron entry or GitHub Action running F2.4, tokens from secrets.
- **Depends on:** F2.4.

### F2.6 Sanity checks
- No gaps in date sequence, no impossible sleep durations, log row counts per run.
- Runs after backfill/incremental as a validation pass.
- **Depends on:** F2.2.

---

## Phase 3 — MCP server

### F3.1 MCP server scaffold + core query tools
- Server via official Python MCP SDK, reads DuckDB views only (no live API calls).
- Tools: `query_sleep(person, start, end)`, `query_readiness(person, start, end)`, `query_activity(person, start, end)`.
- **Depends on:** F2.2.

### F3.2 Comparative/statistical tools
- `compare_people(metric, people, start, end)`, `baseline(person, metric, window)` (mean/stdev for z-scoring).
- **Depends on:** F3.1.

### F3.3 Read-only SQL escape hatch
- `run_sql(query)` against the views, enforce read-only (reject non-SELECT).
- **Depends on:** F3.1.

### F3.4 Data dictionary resource
- MCP resource describing every field (e.g. what `contributors.timing` means) so the model doesn't guess.
- **Depends on:** F2.2 (needs final view shapes).

### F3.5 Claude Desktop integration
- Wire server into Claude Desktop config, conversational smoke test ("why has my HRV been low this week").
- **Depends on:** F3.1, F3.2, F3.3, F3.4.

---

## Phase 4 — Household sleep study *(optional, post-Phase 3)*

### F4.1 Shared timeline alignment
- Align both people's sleep periods onto one timeline.
- **Depends on:** F2.2 (2+ person data present).

### F4.2 Sleep onset convergence analysis
- Is the bedtime delta between the two shrinking over time?
- **Depends on:** F4.1.

### F4.3 Cross-correlation analysis
- Restlessness/HRV cross-correlation between people at lags -3..+3 days.
- Control for weekday, alcohol tags, travel, illness (temp deviation).
- Explicitly address the shared-shock confound (same house/noise/dinner) — the interesting question is lead/lag, not raw correlation.
- **Depends on:** F4.1.

### F4.4 Write-up
- **Depends on:** F4.2, F4.3.

---

## Phase 5 — Sleep League *(optional)*

### F5.1 Friend token onboarding
- Collect tokens with explicit data-retention disclosure.
- **Depends on:** F0.1.

### F5.2 Relative scoring
- Z-score vs. each person's own 90-day baseline.
- **Depends on:** F3.2 (reuses `baseline`), F5.1.

### F5.3 Weekly standings job
- **Depends on:** F5.2.

### F5.4 Post to WhatsApp/Slack
- Commentary generated from actual numbers.
- **Depends on:** F5.3.

### F5.5 Opt-out / deletion
- Real deletion, not a hide flag.
- **Depends on:** F5.1.

---

## Phase 6 — Calendar join *(optional)*

### F6.1 Google Calendar ingestion
- Pull events into a comparable per-day table.
- **Depends on:** F0.1.

### F6.2 Calendar features
- Meeting count, total meeting hours, longest back-to-back run, latest meeting end, meetings before 9am.
- **Depends on:** F6.1.

### F6.3 Next-day readiness/HRV model
- Model against F6.2 features; note reverse-causality risk (bad sleep → reschedule) in the writeup.
- **Depends on:** F6.2, F2.2.

---

## Phase 7 — N-of-1 experiments *(optional)*

### F7.1 Experiment harness
- Nightly coin-flip randomization for one intervention (e.g. caffeine cutoff), logged as an Oura enhanced_tag.
- Predefined outcome metric + analysis plan before data collection starts.
- **Depends on:** F1.4 (enhanced_tag support), F2.2.

### F7.2 Analysis
- Run only after the preregistered night count is reached; report effect size + CI, not just p-value.
- **Depends on:** F7.1.

---

## Phase 8 — Poster *(optional)*

### F8.1 Year-in-nights SVG render
- One vertical band per night, hypnogram as color, restlessness as texture, both people layered, print-resolution export.
- **Depends on:** F2.2.

---

## Open questions (unresolved — affect scoping above, don't block starting)

- Local-only DuckDB file vs. syncing it somewhere the MCP server can reach remotely.
- Single DB with `person_id` column vs. one DB per person (affects F2.1, F5.5 deletion story).
- Whether friends (Phase 5) see each other's raw data or only standings (affects F5.2/F5.4 scope).
