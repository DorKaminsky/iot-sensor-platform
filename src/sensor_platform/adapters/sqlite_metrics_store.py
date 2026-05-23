"""SQLite implementation of MetricsStore."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sensor_platform.domain.models import MetricResult

_DDL = """
CREATE TABLE IF NOT EXISTS computed_metrics (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name       TEXT    NOT NULL,
    station_id        TEXT    NOT NULL,
    device_id         TEXT    NOT NULL,
    value             REAL    NOT NULL,
    start_time        TEXT    NOT NULL,
    end_time          TEXT    NOT NULL,
    resample_freq     TEXT    NOT NULL,
    missing_strategy  TEXT    NOT NULL,
    computed_at       TEXT    NOT NULL,
    UNIQUE(metric_name, station_id, device_id, start_time, end_time,
           resample_freq, missing_strategy)
);
CREATE INDEX IF NOT EXISTS idx_metrics_lookup
    ON computed_metrics(station_id, device_id, metric_name, start_time);
"""


class SQLiteMetricsStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_DDL)

    def save(self, results: list[MetricResult]) -> None:
        sql = """
            INSERT INTO computed_metrics
                (metric_name, station_id, device_id, value, start_time, end_time,
                 resample_freq, missing_strategy, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(metric_name, station_id, device_id, start_time, end_time,
                        resample_freq, missing_strategy)
            DO UPDATE SET value=excluded.value, computed_at=excluded.computed_at
        """
        rows = [
            (
                r.metric_name,
                r.station_id,
                r.device_id,
                r.value,
                r.start_time.isoformat(),
                r.end_time.isoformat(),
                r.resample_freq,
                r.missing_strategy,
                datetime.now(UTC).isoformat(),
            )
            for r in results
        ]
        with sqlite3.connect(self._db_path) as conn:
            conn.executemany(sql, rows)

    def query(
        self,
        station_id: str | None = None,
        device_id: str | None = None,
        metric_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[MetricResult]:
        conditions: list[str] = []
        params: list[object] = []

        if station_id:
            conditions.append("station_id = ?")
            params.append(station_id)
        if device_id:
            conditions.append("device_id = ?")
            params.append(device_id)
        if metric_name:
            conditions.append("metric_name = ?")
            params.append(metric_name)
        if start_time:
            conditions.append("start_time >= ?")
            params.append(start_time.isoformat())
        if end_time:
            conditions.append("end_time <= ?")
            params.append(end_time.isoformat())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = (
            "SELECT metric_name, station_id, device_id, value, start_time, end_time,"
            " resample_freq, missing_strategy"
            f" FROM computed_metrics {where} ORDER BY start_time ASC"
        )

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            MetricResult(
                metric_name=r[0],
                station_id=r[1],
                device_id=r[2],
                value=r[3],
                start_time=datetime.fromisoformat(r[4]).replace(tzinfo=UTC),
                end_time=datetime.fromisoformat(r[5]).replace(tzinfo=UTC),
                resample_freq=r[6],
                missing_strategy=r[7],
            )
            for r in rows
        ]
