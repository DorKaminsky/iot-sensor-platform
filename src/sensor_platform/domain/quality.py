"""Data quality detection — pure functions operating on DataFrames."""

from __future__ import annotations

from datetime import UTC

import pandas as pd

from sensor_platform.domain.models import SENSOR_COLUMNS, FlatlineSegment, QualityReport
from sensor_platform.domain.schema import Schema


def build_quality_report(df: pd.DataFrame, schema: Schema) -> QualityReport:
    """Compute a full quality report on raw (pre-strategy) sensor data."""
    sensor_cols = [c for c in SENSOR_COLUMNS if c in df.columns]

    null_counts = {col: int(df[col].isna().sum()) for col in sensor_cols}
    out_of_range = _count_out_of_range(df, schema, sensor_cols)
    flatlines = _detect_flatlines(df, schema, sensor_cols)
    type_errors = _count_type_errors(df, schema, sensor_cols)

    return QualityReport(
        total_rows=len(df),
        null_counts=null_counts,
        out_of_range_counts=out_of_range,
        flatline_segments=flatlines,
        type_errors=type_errors,
    )


def _count_out_of_range(df: pd.DataFrame, schema: Schema, cols: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for col in cols:
        spec = schema.columns.get(col)
        if spec and spec.valid_range:
            vr = spec.valid_range
            mask = df[col].notna() & ((df[col] < vr.min) | (df[col] > vr.max))
            result[col] = int(mask.sum())
        else:
            result[col] = 0
    return result


def _detect_flatlines(df: pd.DataFrame, schema: Schema, cols: list[str]) -> list[FlatlineSegment]:
    """Detect runs of identical consecutive values exceeding the flatline threshold."""
    segments: list[FlatlineSegment] = []
    if df.empty or "device_id" not in df.columns or "timestamp" not in df.columns:
        return segments

    ts_col = pd.to_datetime(df["timestamp"], utc=True)

    for device_id, group in df.groupby("device_id"):
        group = group.copy()
        group["_ts"] = ts_col.loc[group.index]
        group = group.sort_values("_ts")

        for col in cols:
            spec = schema.sensor_specs.get(col)
            if spec is None:
                continue
            threshold_min = spec.flatline_threshold_minutes
            series = group[col].dropna()
            if series.empty:
                continue

            # Walk runs of equal consecutive values
            prev_val = series.iloc[0]
            run_start_idx: int | None = series.index[0]
            prev_idx: int = series.index[0]
            for idx in series.index[1:]:
                val = series[idx]
                if val == prev_val:
                    pass  # continue extending the run
                else:
                    if run_start_idx is not None:
                        _maybe_add_segment(
                            segments,
                            group,
                            run_start_idx,
                            prev_idx,
                            str(device_id),
                            col,
                            float(prev_val),
                            threshold_min,
                        )
                    run_start_idx = idx
                    prev_val = val
                prev_idx = idx

            # Close open run at end of series
            if run_start_idx is not None and prev_val is not None:
                last_idx = series.index[-1]
                _maybe_add_segment(
                    segments,
                    group,
                    run_start_idx,
                    last_idx,
                    str(device_id),
                    col,
                    float(prev_val),
                    threshold_min,
                )

    return segments


def _maybe_add_segment(
    segments: list[FlatlineSegment],
    group: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    device_id: str,
    col: str,
    value: float,
    threshold_min: int,
) -> None:
    t_start = pd.Timestamp(group.loc[start_idx, "_ts"])  # type: ignore[arg-type]
    t_end = pd.Timestamp(group.loc[end_idx, "_ts"])  # type: ignore[arg-type]
    duration = (t_end - t_start).total_seconds() / 60
    if duration >= threshold_min:
        segments.append(
            FlatlineSegment(
                device_id=device_id,
                sensor=col,
                start_time=t_start.to_pydatetime().replace(tzinfo=UTC),
                end_time=t_end.to_pydatetime().replace(tzinfo=UTC),
                duration_minutes=round(duration, 1),
                value=value,
            )
        )


def _count_type_errors(df: pd.DataFrame, schema: Schema, cols: list[str]) -> dict[str, int]:
    """Count non-null values that cannot be coerced to the schema-declared type."""
    result: dict[str, int] = {}
    for col in cols:
        spec = schema.columns.get(col)
        if spec is None:
            result[col] = 0
            continue
        non_null = df[col].dropna()
        if spec.type == "integer":
            # A value is a type error if it has a non-zero fractional part
            errors = int((non_null % 1 != 0).sum())
        elif spec.type == "float":
            try:
                pd.to_numeric(non_null, errors="raise")
                errors = 0
            except (ValueError, TypeError):
                errors = int(pd.to_numeric(non_null, errors="coerce").isna().sum())
        else:
            errors = 0
        result[col] = errors
    return result
