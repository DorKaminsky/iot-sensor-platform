"""SQLite implementation of QualityReportStore."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sensor_platform.domain.models import FlatlineSegment, QualityReport

_DDL = """
CREATE TABLE IF NOT EXISTS quality_reports (
    station_id   TEXT PRIMARY KEY,
    total_rows   INTEGER NOT NULL,
    null_counts  TEXT    NOT NULL,
    oob_counts   TEXT    NOT NULL,
    flatlines    TEXT    NOT NULL,
    computed_at  TEXT    NOT NULL
);
"""


class SQLiteQualityReportStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_DDL)

    def save(self, station_id: str, report: QualityReport) -> None:
        flatlines = [
            {
                "device_id": s.device_id,
                "sensor": s.sensor,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "duration_minutes": s.duration_minutes,
                "value": s.value,
            }
            for s in report.flatline_segments
        ]
        sql = """
            INSERT INTO quality_reports
                (station_id, total_rows, null_counts, oob_counts, flatlines, computed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(station_id)
            DO UPDATE SET
                total_rows=excluded.total_rows,
                null_counts=excluded.null_counts,
                oob_counts=excluded.oob_counts,
                flatlines=excluded.flatlines,
                computed_at=excluded.computed_at
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                sql,
                (
                    station_id,
                    report.total_rows,
                    json.dumps(report.null_counts),
                    json.dumps(report.out_of_range_counts),
                    json.dumps(flatlines),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get(self, station_id: str) -> QualityReport | None:
        sql = (
            "SELECT total_rows, null_counts, oob_counts, flatlines"
            " FROM quality_reports WHERE station_id = ?"
        )
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(sql, (station_id,)).fetchone()
        if row is None:
            return None
        flatline_segments = [
            FlatlineSegment(
                device_id=s["device_id"],
                sensor=s["sensor"],
                start_time=datetime.fromisoformat(s["start_time"]).replace(tzinfo=UTC),
                end_time=datetime.fromisoformat(s["end_time"]).replace(tzinfo=UTC),
                duration_minutes=s["duration_minutes"],
                value=s["value"],
            )
            for s in json.loads(row[3])
        ]
        return QualityReport(
            total_rows=row[0],
            null_counts=json.loads(row[1]),
            out_of_range_counts=json.loads(row[2]),
            flatline_segments=flatline_segments,
        )
