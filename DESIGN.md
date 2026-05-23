# Design Document

## Challenge 1 — Part 4

### 1. Versioning and distributing the library across 25+ services in a monorepo

The library lives in `src/sensor_platform/` as an installable Python package. In a monorepo with 25+ services, the recommended approach is **uv workspaces** (or Poetry workspaces): each service declares `sensor-platform` as a dependency, and the workspace resolver ensures all services pin to the same lockfile.

**Version strategy:** Semantic versioning (`MAJOR.MINOR.PATCH`) enforced in `pyproject.toml`. The Git tag (`git tag v1.2.0`) triggers a CI job that publishes to the internal package registry (e.g. Artifactory, GCP Artifact Registry, or a private PyPI).

**For consumers:** services pin `sensor-platform>=1.2,<2.0` — accepting minor upgrades automatically but requiring an explicit bump to adopt breaking changes.

**For breaking changes:** we use a deprecation cycle — mark the old API with a `DeprecationWarning` for one minor version, publish a migration guide, then remove in the next major. A CI job that installs the library into each dependent service's test environment (`uv run --package <service> pytest`) catches breakage before merge.

**Trade-off considered:** Copying the library source into each service (vendor) was rejected — it eliminates the single source of truth and makes cross-cutting fixes expensive.

---

### 2. Schema evolution — new sensor types, renamed columns, different units

The schema is loaded at runtime from `sensor_schema.json`, not baked into the code. This means adding a new sensor type (e.g. `vibration_hz`) requires only a JSON update, with no library code change.

**For additive changes** (new sensor type, new column): the library's `SENSOR_COLUMNS` list drives which columns are processed. Unknown columns are passed through transparently. Consumers that don't care about the new sensor see no change.

**For breaking changes** (column rename, unit change):

- **Rename:** Add an alias mapping in `Schema` — the library normalises `rpm` → `motor_speed` internally. Consumers are never exposed to the old name.
- **Unit change:** Embed the unit in the schema (`"unit": "bar"`) and add a conversion layer in `SQLiteDataSource` — so the library always emits SI units regardless of what the database stores.
- **New schema version:** The schema file carries a `"version"` field. The library validates that it can handle the loaded version and raises a clear `SchemaVersionError` if not, rather than silently processing with wrong assumptions.

**Trade-off considered:** Encoding unit conversion in the library vs. leaving it to the data warehouse layer. We chose the library because it keeps unit semantics in one place, preventing the class of bug where two consumers interpret the same column differently.

---

### 3. CI/CD pipeline

```
Push / PR
│
├── Lint & Format    ruff check src tests && ruff format --check src tests
├── Type Check       mypy src
├── Unit Tests       pytest tests/unit -q
├── Integration      pytest tests/integration -q          (requires sensor_data.db)
└── Coverage Gate    coverage ≥ 85% required to merge

Merge to main
│
├── Build            docker build -t sensor-platform:$SHA .
├── Push             docker push registry/sensor-platform:$SHA
├── Deploy Staging   helm upgrade --set image.tag=$SHA (staging namespace)
├── Smoke Test       curl /health && curl /stations (basic sanity)
└── Deploy Prod      Manual approval gate → same helm upgrade (prod namespace)
```

**Key decisions:**

- Unit and integration tests run in parallel in GitHub Actions; integration tests use the real `sensor_data.db` mounted as a CI artifact so they test realistic data shapes.
- The Docker image is built once and promoted through environments — the same image that passed staging goes to prod (no rebuild).
- The service is stateless (all state in SQLite/external DB); rolling deploys with zero downtime are safe.
- For a production system, SQLite would be replaced by Cloud SQL or BigQuery — the `DataSource` and `MetricsStore` protocols mean the service code is unchanged; only the adapter and the Kubernetes `ConfigMap` pointing to the database URL changes.

---

### Tooling choices

**Task runner: `make`**

`make` is pre-installed on every Unix/macOS machine — a reviewer can clone and type `make test` with zero additional setup. Alternatives considered:

- **`just`**: cleaner syntax, but requires `brew install just` — an extra step with no benefit for the 5 targets this project needs.
- **`taskfile` (Task)**: modern, cross-platform YAML format, genuinely better for complex dependency graphs between tasks. Rejected here because the tasks are all independent (`lint`, `typecheck`, `test`) and the added install friction outweighs the ergonomic gain for a project of this size.

The decision would reverse in a larger team project where Windows developers are involved — `make` behaves differently on Windows and `taskfile` would be the right call there.
