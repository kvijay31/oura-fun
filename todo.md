# Oura Passion Project

Build order: ingestion first, then the MCP server, then analyses on top.
Everything below Phase 3 is optional and can be picked up in any order.

## Stack (proposed, change if you disagree)

- Python 3.12, `uv` for deps
- `httpx` for the API client
- DuckDB for storage (single file, zero ops, good enough for years of nightly data)
- `pydantic` for response models
- MCP server via the official Python SDK
- Analysis in marimo or Jupyter, plots with plotly

## Phase 0: Setup

- [ ] Generate a personal access token at cloud.ouraring.com/personal-access-tokens
- [ ] Store tokens in `.env`, one per person (`OURA_TOKEN_KARTIK`, `OURA_TOKEN_PARTNER`, ...)
- [ ] Add `.env` and `*.duckdb` to `.gitignore` before the first commit
- [ ] Confirm auth works: `GET /v2/usercollection/personal_info` with `Authorization: Bearer <token>`

## Phase 1: API client

Base URL: `https://api.ouraring.com/v2/usercollection/`

- [ ] Thin client wrapping GET with bearer auth, retries, and rate limit handling (429 backoff)
- [ ] Handle cursor pagination (`next_token` in the response, pass back as `next_token` param)
- [ ] Date range params are `start_date` / `end_date` (inclusive, YYYY-MM-DD), max 30 days per request for some endpoints, so chunk the range
- [ ] Endpoints to cover:
  - [ ] `daily_sleep` (the score and contributors)
  - [ ] `sleep` (per sleep period: stages, HRV, latency, efficiency, restlessness)
  - [ ] `daily_readiness`
  - [ ] `daily_activity`
  - [ ] `daily_stress`
  - [ ] `daily_spo2`
  - [ ] `heartrate` (5 min granularity, uses `start_datetime` / `end_datetime`, not dates)
  - [ ] `workout`
  - [ ] `session`
  - [ ] `enhanced_tag`
  - [ ] `sleep_time`
  - [ ] `personal_info`

## Phase 2: Ingestion

- [ ] DuckDB schema: one raw table per endpoint, columns `(person_id, natural_key, day, payload JSON, fetched_at)`
- [ ] Store raw JSON, do not flatten on write. Oura backfills and revises past days, so keep every fetch and derive views on read
- [ ] Views on top: `v_sleep_nightly`, `v_readiness_daily`, `v_activity_daily`, deduped to the latest `fetched_at` per `(person_id, natural_key)`
- [ ] Backfill script: pull full history for each token
- [ ] Incremental script: last 14 days daily, to catch revisions
- [ ] Schedule it (cron, or a GitHub Action with tokens in secrets)
- [ ] Sanity checks: no gaps in the date sequence, no nights with impossible durations, log counts per run

## Phase 3: MCP server

- [ ] MCP server exposing the DuckDB layer, not the live API (fast, offline, no rate limits)
- [ ] Tools:
  - [ ] `query_sleep(person, start, end)` returning tidy records
  - [ ] `query_readiness(person, start, end)`
  - [ ] `query_activity(person, start, end)`
  - [ ] `compare_people(metric, people, start, end)`
  - [ ] `baseline(person, metric, window)` returning mean and stdev for z-scoring
  - [ ] `run_sql(query)` read-only escape hatch against the views
- [ ] Resource: a data dictionary describing every field, so the model does not have to guess what `contributors.timing` means
- [ ] Test conversationally: "why has my HRV been low this week", "compare my sleep to last month"
- [ ] Wire into Claude Desktop config and use it for a week before adding anything else

## Phase 4: Household sleep study

- [ ] Align both people's sleep periods onto a shared timeline
- [ ] Sleep onset convergence: is the delta between bedtimes shrinking over time?
- [ ] Cross-correlation of restlessness and HRV between the two of you at lags -3 to +3 days
- [ ] Control for the obvious confounders: weekday, alcohol tags, travel, illness (temperature deviation)
- [ ] Watch out for the shared-shock problem. Same house, same noise, same dinner means correlation is nearly guaranteed. The interesting question is whether one person leads the other
- [ ] Write up whatever you find, even if it is nothing

## Phase 5: Sleep League (optional)

- [ ] Collect tokens from friends with an explicit note on what is stored and for how long
- [ ] Scoring relative to each person's own 90 day baseline (z-score), not absolute values
- [ ] Weekly job computing standings
- [ ] Post to WhatsApp or Slack with commentary generated from the actual numbers
- [ ] Opt-out that deletes their data properly, not just hides it

## Phase 6: Calendar join (optional)

- [ ] Pull Google Calendar events
- [ ] Features per day: meeting count, total meeting hours, longest back-to-back run, latest meeting end time, number of meetings before 9am
- [ ] Model next-day readiness and HRV against those features
- [ ] Beware reverse causality: bad sleep may cause you to reschedule, not the other way around

## Phase 7: N-of-1 experiments (optional)

- [ ] Pick one intervention (caffeine cutoff time is a good first one)
- [ ] Randomize nightly with a coin flip, log the assignment as an Oura tag
- [ ] Predefine the outcome metric and the analysis before collecting data
- [ ] Run for a preregistered number of nights, then analyze once
- [ ] Report the effect size and the confidence interval, not just a p value

## Phase 8: Poster (optional)

- [ ] Render a year of nights as a single SVG, both people layered
- [ ] Each night as a vertical band, hypnogram as color, restlessness as texture
- [ ] Export at print resolution

## Open questions

- [ ] Local DuckDB file, or sync to something so the MCP server can run from anywhere?
- [ ] One database with a `person_id` column, or one per person for cleaner deletion?
- [ ] Do friends see each other's raw data, or only standings?
