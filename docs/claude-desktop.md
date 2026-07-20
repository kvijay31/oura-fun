# Claude Desktop Integration

Wire the `oura-fun` MCP server into Claude Desktop so you can ask questions about
your Oura Ring data in plain English.

---

## Prerequisites

- `uv` installed and on `PATH` (`brew install uv` or see [uv docs](https://docs.astral.sh/uv/))
- oura-fun repo cloned locally (e.g. `~/projects/oura-fun`)
- DuckDB file populated via the backfill script (`uv run python scripts/backfill.py`)
- Claude Desktop installed (desktop.claude.ai)

---

## Configuration

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(create the file if it does not exist):

```json
{
  "mcpServers": {
    "oura-fun": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/you/projects/oura-fun",
        "run",
        "oura-mcp"
      ],
      "env": {
        "OURA_DB_PATH": "/Users/you/projects/oura-fun/oura.duckdb"
      }
    }
  }
}
```

Replace the two paths:

| Placeholder | Replace with |
|-------------|--------------|
| `/Users/you/projects/oura-fun` | Absolute path to this repo |
| `/Users/you/projects/oura-fun/oura.duckdb` | Absolute path to the DuckDB file |

> **Note:** `OURA_DB_PATH` defaults to `oura.duckdb` in the current working
> directory if omitted. Setting it explicitly avoids surprises when Claude
> Desktop starts the server from a different working directory.

After saving, **quit and relaunch Claude Desktop**. The oura-fun tools should
appear under the MCP tools icon (hammer) in a new conversation.

---

## Available tools

| Tool | What it does |
|------|--------------|
| `query_sleep(person, start, end)` | Nightly sleep scores, stages, HRV, heart rate |
| `query_readiness(person, start, end)` | Daily readiness score and recovery contributors |
| `query_activity(person, start, end)` | Steps, calories, activity time breakdown |
| `compare_people(metric, people, start, end)` | Side-by-side metric comparison across people |
| `baseline(person, metric, window)` | 90-day (or custom) mean and stdev for z-scoring |
| `run_sql(query)` | Read-only SQL escape hatch against the DuckDB views |

Resource: **`oura://data-dictionary`** — read this once to understand every field
before writing queries (Claude does this automatically via the server's
instructions).

---

## Smoke test

Open a new conversation in Claude Desktop and verify each capability below.
Replace `kartik` with whatever `person_id` you used during ingestion.

### 1. Basic retrieval

> "What were my sleep scores for the last 7 days?"

Expected: Claude calls `query_sleep("kartik", "<last-week>", "<today>")` and
returns a table with nightly scores and stage breakdowns.

### 2. HRV trend question (the Phase 3 target)

> "Why has my HRV been low this week?"

Expected: Claude calls `query_sleep` and `query_readiness` to pull HRV and
readiness contributors, then offers a narrative explanation referencing
`c_hrv_balance`, temperature deviation, and any stress/activity context.

### 3. Baseline comparison

> "How does my HRV this week compare to my 90-day average?"

Expected: Claude calls `baseline("kartik", "average_hrv", 90)` and
`query_sleep` for the current week, then computes and explains the z-score.

### 4. Activity context

> "Was I more active on the days I slept well?"

Expected: Claude calls `query_sleep` and `query_activity` for a meaningful
window and identifies any correlation pattern.

### 5. Multi-person (if you have a second person's data)

> "Compare my sleep score to [partner] for the last two weeks."

Expected: Claude calls `compare_people("sleep_score", "kartik,partner", ...)` and
returns a side-by-side view.

### 6. SQL escape hatch

> "What was my average readiness score per day-of-week over the last 3 months?"

Expected: Claude calls `run_sql` with a query grouping on
`strftime('%A', day)` against `v_readiness_daily`.

---

## Troubleshooting

**Server doesn't appear in Claude Desktop**

- Check that `uv` is on `PATH` in your shell profile (`.zshrc` / `.bash_profile`).
  Claude Desktop inherits a limited environment — run
  `which uv` in Terminal to confirm the path, then hard-code it in `"command"`
  if needed.
- Confirm the `--directory` path exists and contains `pyproject.toml`.
- Check Claude Desktop logs: **Help → Open Logs Folder** → `mcp-server-oura-fun.log`.

**Tools appear but return empty results**

- The DuckDB file may not exist at `OURA_DB_PATH`. Run
  `uv run python scripts/backfill.py` to populate it.
- Confirm the `person_id` you're using matches what was ingested
  (`SELECT DISTINCT person_id FROM v_sleep_nightly`).

**`uv` not found error in logs**

Add the full path to `uv` in the config:
```json
"command": "/Users/you/.local/bin/uv"
```
