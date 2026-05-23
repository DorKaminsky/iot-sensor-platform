"""IngestionService — validates, applies missing strategy, resamples sensor data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from sensor_platform.domain.models import SENSOR_COLUMNS, MissingStrategy, QualityReport
from sensor_platform.domain.quality import build_quality_report
from sensor_platform.domain.schema import Schema
from sensor_platform.ports.data_source import DataSource


class IngestionService:
    def __init__(self, data_source: DataSource, schema: Schema) -> None:
        self._source = data_source
        self._schema = schema

    def ingest(
        self,
        resample_freq: str | pd.Timedelta,
        station_id: str | None = None,
        device_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        missing_strategy: MissingStrategy = "drop",
    ) -> tuple[pd.DataFrame, QualityReport]:
        """Return (resampled_df, quality_report).

        Quality report is computed on raw data before any strategy is applied
        so callers see the true data quality, not the cleaned picture.
        """
        df = self._source.read_readings(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
        )

        report = build_quality_report(df, self._schema)

        df = _apply_missing_strategy(df, missing_strategy)
        df = _clip_out_of_range(df, self._schema)
        df = _resample(df, resample_freq)

        return df, report


def _apply_missing_strategy(df: pd.DataFrame, strategy: MissingStrategy) -> pd.DataFrame:
    sensor_cols = [c for c in SENSOR_COLUMNS if c in df.columns]
    if strategy == "drop":
        return df.dropna(subset=sensor_cols)
    if strategy == "fill":
        df = df.copy()
        df[sensor_cols] = df[sensor_cols].fillna(0.0)
        return df
    if strategy == "ffill":
        df = df.copy()
        df[sensor_cols] = df[sensor_cols].ffill()
        return df
    if strategy == "interpolate":
        df = df.copy()
        df = df.set_index("timestamp")
        df[sensor_cols] = df[sensor_cols].interpolate(method="time")
        df = df.reset_index()
        return df
    return df


def _clip_out_of_range(df: pd.DataFrame, schema: Schema) -> pd.DataFrame:
    """Replace out-of-range values with NaN so they don't skew metrics."""
    df = df.copy()
    for col, spec in schema.columns.items():
        if col not in df.columns or spec.valid_range is None:
            continue
        vr = spec.valid_range
        mask = df[col].notna() & ((df[col] < vr.min) | (df[col] > vr.max))
        df.loc[mask, col] = float("nan")
    return df


def _resample(df: pd.DataFrame, freq: str | pd.Timedelta) -> pd.DataFrame:
    """Resample to freq, aggregating per (station_id, device_id) window."""
    if df.empty:
        return df

    sensor_cols = [c for c in SENSOR_COLUMNS if c in df.columns]
    df = df.set_index("timestamp").sort_index()

    agg: dict[str, Any] = {col: "mean" for col in sensor_cols}
    # motor_speed is an integer sensor; keep mean but round later
    for pass_col in ("station_id", "device_id"):
        if pass_col in df.columns:
            agg[pass_col] = "first"

    groups = []
    for _, group in df.groupby(["station_id", "device_id"]):
        resampled = group.resample(freq).agg(agg)  # type: ignore[arg-type]
        groups.append(resampled)

    if not groups:
        return df.reset_index()

    result = pd.concat(groups).reset_index()
    if "motor_speed" in result.columns:
        result["motor_speed"] = result["motor_speed"].round().astype("Int64")
    return result
