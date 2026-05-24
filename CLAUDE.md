# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync --extra dev          # install all dependencies

uv run pytest                # all tests + coverage (requires sensor_data.db)
uv run pytest tests/unit     # unit tests only — no DB, fast
uv run pytest tests/integration
uv run pytest tests/e2e
uv run pytest tests/unit/test_metrics.py::TestUptimePct  # single test class

uv run ruff check src tests  # lint
uv run ruff format --check src tests
uv run mypy src              # type check

uv run sensor-api            # start API server at http://localhost:8000
```

## Architecture

Hexagonal (Ports & Adapters). Dependencies point inward only:

```
API  →  Services  →  Ports  ←  Adapters
                 →  Domain  ←  Adapters
```

**`src/sensor_platform/`**
- `domain/` — pure Python, no I/O: `models.py` (dataclasses), `schema.py` (loads `sensor_schema.json`), `quality.py` (null/OOB/flatline detection), `metrics.py` (5 compute functions + `METRIC_REGISTRY`), `prompts.py` (LLM prompt builders), `exceptions.py`
- `ports/` — Protocol interfaces: `DataSource`, `MetricsStore`, `QualityReportStore`, `LLMClient`, `EventTransport`
- `adapters/` — concrete implementations: `SQLiteDataSource` (reads `sensor_data.db`), `SQLiteMetricsStore` + `SQLiteQualityReportStore` (write to `metrics.db`), `ClaudeAdapter`, `OllamaAdapter`, `QueueTransport`
- `services/` — orchestration: `IngestionService` (fetch→quality→clean→resample), `MetricsService` (ingest→compute→store), `LLMService` (prompt→generate→strip)
- `api/` — thin FastAPI wrapper: `app.py`, `dependencies.py` (all services wired with `@lru_cache`), `schemas.py` (Pydantic models), `routes/`

## Key Design Points

**Two databases:** `sensor_data.db` is read-only source data. `metrics.db` is the derived store (computed metrics + quality reports). Never write to `sensor_data.db`.

**Swap point:** `api/dependencies.py:get_data_source()` is the single line to change for BigQuery. Same pattern for LLM provider: `LLM_PROVIDER=ollama` in `.env` swaps Claude for Ollama.

**`@lru_cache` on all dependency functions** — each service/store is constructed once per process. Tests override with `app.dependency_overrides[get_metrics_service] = lambda: mock`.

**Quality report is computed on raw data before cleaning** — intentional. Post-clean report would show 0 nulls after dropping them, which is misleading.

**`resample_freq` is required with no default** — the right granularity is use-case specific; a silent default would produce silently wrong results.

## Adding a New Metric

1. Write `compute_my_metric(df: pd.DataFrame) -> float` in `domain/metrics.py`
2. Add it to `METRIC_REGISTRY`
3. Done — `MetricsService` picks it up by name automatically

If the metric needs `freq_minutes` (like `total_flow_volume`), add a branch in `_compute()` instead.

## Environment

Copy `.env.example` to `.env` for LLM features:
```
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```
`.env` is gitignored — never commit it.

## Test Layout

- `tests/unit/` — synthetic DataFrames, no DB, millisecond speed
- `tests/integration/` — real `sensor_data.db`, tests full ingestion pipeline
- `tests/e2e/` — `TestClient` + `dependency_overrides`, tests full HTTP stack
