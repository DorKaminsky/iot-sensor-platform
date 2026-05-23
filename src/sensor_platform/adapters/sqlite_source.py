"""SQLite implementation of DataSource."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from sensor_platform.domain.models import Station


class SQLiteDataSource:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    def read_readings(
        self,
        station_id: str | None = None,
        device_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> pd.DataFrame:
        conditions: list[str] = []
        params: list[Any] = []

        if station_id:
            conditions.append("station_id = ?")
            params.append(station_id)
        if device_id:
            conditions.append("device_id = ?")
            params.append(device_id)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM sensor_readings {where} ORDER BY timestamp ASC"

        with sqlite3.connect(self._db_path) as conn:
            df = pd.read_sql_query(sql, conn, params=params)

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        return df

    def read_stations(self) -> list[Station]:
        sql = (
            "SELECT station_id, station_name, location, commissioned_date, num_compressors"
            " FROM station_metadata"
        )
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(sql).fetchall()
        return [
            Station(
                station_id=r[0],
                station_name=r[1],
                location=r[2],
                commissioned_date=r[3],
                num_compressors=r[4],
            )
            for r in rows
        ]
