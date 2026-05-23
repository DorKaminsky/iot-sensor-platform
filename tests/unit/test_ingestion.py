"""Unit tests for IngestionService missing strategies and clipping."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from sensor_platform.domain.schema import Schema
from sensor_platform.services.ingestion import (
    _apply_missing_strategy,
    _clip_out_of_range,
)


def _make_df(rows: list[dict]) -> pd.DataFrame:  # type: ignore[type-arg]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def _row(minute: int, pressure: float | None = 8.0) -> dict:  # type: ignore[type-arg]
    return {
        "timestamp": datetime(2024, 1, 1, 0, minute, tzinfo=UTC),
        "station_id": "s1",
        "device_id": "dev-A",
        "discharge_pressure": pressure,
        "air_flow_rate": 100.0,
        "power_consumption": 50.0,
        "motor_speed": 1500,
        "discharge_temp": 60.0,
    }


class TestMissingStrategyDrop:
    def test_removes_null_rows(self) -> None:
        df = _make_df([_row(0, None), _row(1, 8.0), _row(2, None)])
        result = _apply_missing_strategy(df, "drop")
        assert len(result) == 1
        assert result["discharge_pressure"].iloc[0] == pytest.approx(8.0)

    def test_clean_data_unchanged(self) -> None:
        df = _make_df([_row(i) for i in range(5)])
        result = _apply_missing_strategy(df, "drop")
        assert len(result) == 5


class TestMissingStrategyFill:
    def test_fills_nulls_with_zero(self) -> None:
        df = _make_df([_row(0, None), _row(1, 8.0)])
        result = _apply_missing_strategy(df, "fill")
        assert result["discharge_pressure"].iloc[0] == pytest.approx(0.0)
        assert len(result) == 2

    def test_does_not_modify_original(self) -> None:
        df = _make_df([_row(0, None)])
        _apply_missing_strategy(df, "fill")
        assert pd.isna(df["discharge_pressure"].iloc[0])


class TestMissingStrategyFfill:
    def test_forward_fills_from_last_valid(self) -> None:
        df = _make_df([_row(0, 7.0), _row(1, None), _row(2, None)])
        result = _apply_missing_strategy(df, "ffill")
        assert result["discharge_pressure"].tolist() == pytest.approx([7.0, 7.0, 7.0])

    def test_leading_null_stays_null(self) -> None:
        # ffill cannot fill a null that has no preceding value
        df = _make_df([_row(0, None), _row(1, 8.0)])
        result = _apply_missing_strategy(df, "ffill")
        assert pd.isna(result["discharge_pressure"].iloc[0])
        assert result["discharge_pressure"].iloc[1] == pytest.approx(8.0)


class TestMissingStrategyInterpolate:
    def test_interpolates_between_valid_values(self) -> None:
        df = _make_df([_row(0, 6.0), _row(1, None), _row(2, 8.0)])
        result = _apply_missing_strategy(df, "interpolate")
        assert result["discharge_pressure"].iloc[1] == pytest.approx(7.0)

    def test_timestamp_column_preserved(self) -> None:
        df = _make_df([_row(0, 6.0), _row(1, None), _row(2, 8.0)])
        result = _apply_missing_strategy(df, "interpolate")
        assert "timestamp" in result.columns
        assert len(result) == 3


class TestClipOutOfRange:
    def test_clips_over_max_to_nan(self, schema: Schema) -> None:
        df = _make_df([_row(0, 99.0)])  # valid max is 16.0
        result = _clip_out_of_range(df, schema)
        assert pd.isna(result["discharge_pressure"].iloc[0])

    def test_clips_under_min_to_nan(self, schema: Schema) -> None:
        df = _make_df([_row(0, -1.0)])  # valid min is 0.0
        result = _clip_out_of_range(df, schema)
        assert pd.isna(result["discharge_pressure"].iloc[0])

    def test_valid_value_unchanged(self, schema: Schema) -> None:
        df = _make_df([_row(0, 8.0)])
        result = _clip_out_of_range(df, schema)
        assert result["discharge_pressure"].iloc[0] == pytest.approx(8.0)

    def test_other_columns_preserved_when_one_clipped(self, schema: Schema) -> None:
        # Clipping one sensor should not affect other sensor columns in the same row
        df = _make_df([_row(0, 99.0)])  # bad pressure, good everything else
        result = _clip_out_of_range(df, schema)
        assert pd.isna(result["discharge_pressure"].iloc[0])
        assert result["air_flow_rate"].iloc[0] == pytest.approx(100.0)
        assert result["motor_speed"].iloc[0] == 1500
