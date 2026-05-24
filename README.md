# Sensor Platform

Industrial IoT sensor data ingestion library and metrics service for compressed air systems.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

```bash
git clone <repo>
cd iot-sensor-platform
uv sync --extra dev
```

That's it — uv creates `.venv` and installs all dependencies.

## Running tasks

```bash
uv run pytest                          # all tests + coverage
uv run pytest tests/unit               # unit tests only (no DB required)
uv run pytest tests/integration        # integration tests (uses sensor_data.db)
uv run pytest tests/e2e                # full API tests
uv run ruff check src tests            # lint
uv run ruff format --check src tests   # format check
uv run mypy src                        # type check
```

## Running the API

```bash
uv run sensor-api
# → http://localhost:8000
# → http://localhost:8000/docs  (interactive API docs)
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/stations/` | List all stations |
| `POST` | `/stations/{id}/process` | Ingest data, compute and store metrics |
| `GET` | `/stations/{id}/metrics` | Query stored metrics |
| `POST` | `/stations/{id}/summarize` | LLM health summary (requires `/process` first) |
| `POST` | `/stations/{id}/quality-report` | LLM quality report summary (requires `/process` first) |
| `POST` | `/stations/{id}/query` | Free-text question answering over stored metrics |

### Process a station (example)

```bash
curl -X POST http://localhost:8000/stations/d43f07f0-0170-5663-a459-04597edb38b6/process \
  -H "Content-Type: application/json" \
  -d '{
    "resample_freq": "5min",
    "start_time": "2024-02-01T00:00:00Z",
    "end_time": "2024-02-02T00:00:00Z",
    "missing_strategy": "drop"
  }'
```

**`resample_freq`** is required — no default, because the right granularity is use-case specific (alerting needs 1-min; dashboards need 5-min; reports need 1-hour).

**`missing_strategy`** options: `drop` (default), `fill`, `interpolate`, `ffill`.

### Query stored metrics

```bash
curl "http://localhost:8000/stations/d43f07f0-0170-5663-a459-04597edb38b6/metrics?metric_name=uptime_pct"
```

### LLM endpoints (optional)

Requires a `.env` file in the repo root:

```
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

```bash
# Health summary
curl -X POST http://localhost:8000/stations/d43f07f0-0170-5663-a459-04597edb38b6/summarize

# Quality report summary
curl -X POST http://localhost:8000/stations/d43f07f0-0170-5663-a459-04597edb38b6/quality-report

# Free-text question
curl -X POST http://localhost:8000/stations/d43f07f0-0170-5663-a459-04597edb38b6/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Which device has the highest average pressure?"}'
```

To use a local Ollama model instead: set `LLM_PROVIDER=ollama` (no API key needed).

## Computed metrics

| Metric | Definition |
|--------|-----------|
| `uptime_pct` | % of resampled windows where `motor_speed > 0` |
| `avg_pressure` | Mean `discharge_pressure` (bar) |
| `peak_pressure` | Maximum `discharge_pressure` observed |
| `specific_power` | Mean `power_consumption / air_flow_rate` (kW per m³/h) — idle windows excluded |
| `cycle_count` | Number of on/off transitions detected via `motor_speed` crossing zero |

## Architecture

```
sensor_platform/
├── domain/       Pure business logic — metrics, quality detection, schema, prompts. No I/O.
├── ports/        Protocols (interfaces) for DataSource, MetricsStore, LLMClient, QualityReportStore, EventTransport.
├── adapters/     Concrete implementations — SQLite, Claude, Ollama, queue.Queue.
├── services/     IngestionService, MetricsService, LLMService — orchestration only.
└── api/          FastAPI thin wrapper over services.
```

**Key design decision:** The library (`sensor_platform`) is framework-agnostic — it can be imported by any Python service without pulling in FastAPI. Backing stores are swappable via the `DataSource` and `MetricsStore` protocols; changing from SQLite to BigQuery requires only a new adapter class. The same pattern applies to LLM providers — `LLM_PROVIDER=ollama` swaps Claude for a local Ollama instance with no code change.

See `DESIGN.md` for answers to library versioning, schema evolution, and CI/CD questions.

## Package manager comparison

| Tool | Pros | Cons |
|------|------|------|
| **uv** | 10–100× faster than pip; single tool for venv + deps + lock file; native workspace support; Astral-backed (ruff creators) | Newer ecosystem, less familiar to some teams |
| **Poetry** | Mature, widely adopted; good lock file; familiar to most teams | Slower than uv; two-step install (poetry then deps) |
| **pip + pip-tools** | No magic, everyone knows pip; minimal abstraction | Manual venv setup; no workspace support; `pip-compile` is a separate tool |

We chose **uv** because it represents the current direction of the Python packaging ecosystem and gives the best developer experience for `uv sync && uv run pytest`.
