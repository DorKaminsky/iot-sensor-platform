"""Unit tests for data quality detection."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from sensor_platform.domain.models import SENSOR_COLUMNS
from sensor_platform.domain.quality import build_quality_report


def _ts(minute: int) -> pd.Timestamp:
    return pd.Timestamp(datetime(2024, 2, 1, 0, minute, tzinfo=UTC))


def _base_row(minute: int, device: str = "dev-A") -> dict:  # type: ignore[type-arg]
    return {
        "timestamp": _ts(minute),
        "station_id": "s1",
        "device_id": device,
        "discharge_pressure": 8.0,
        "air_flow_rate": 100.0,
        "power_consumption": 50.0,
        "motor_speed": 1500,
        "discharge_temp": 60.0,
    }


class TestNullCounts:
    def test_no_nulls(self, schema) -> None:  # type: ignore[no-untyped-def]
        df = pd.DataFrame([_base_row(i) for i in range(5)])
        report = build_quality_report(df, schema)
        assert all(v == 0 for v in report.null_counts.values())

    def test_counts_nulls(self, schema) -> None:  # type: ignore[no-untyped-def]
        rows = [_base_row(i) for i in range(5)]
        rows[0]["discharge_pressure"] = None
        rows[1]["discharge_pressure"] = None
        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        assert report.null_counts["discharge_pressure"] == 2
        assert report.null_pct["discharge_pressure"] == pytest.approx(40.0)

    def test_empty_dataframe(self, schema) -> None:  # type: ignore[no-untyped-def]
        cols = ["timestamp", "station_id", "device_id"] + SENSOR_COLUMNS
        report = build_quality_report(pd.DataFrame(columns=cols), schema)
        assert report.total_rows == 0
        assert report.quality_score == 0.0


class TestOutOfRange:
    def test_detects_over_range(self, schema) -> None:  # type: ignore[no-untyped-def]
        rows = [_base_row(i) for i in range(3)]
        rows[0]["discharge_pressure"] = 99.0  # valid max is 16.0
        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        assert report.out_of_range_counts["discharge_pressure"] == 1

    def test_detects_under_range(self, schema) -> None:  # type: ignore[no-untyped-def]
        rows = [_base_row(i) for i in range(3)]
        rows[0]["discharge_pressure"] = -1.0  # valid min is 0.0
        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        assert report.out_of_range_counts["discharge_pressure"] == 1

    def test_valid_values_not_flagged(self, schema) -> None:  # type: ignore[no-untyped-def]
        df = pd.DataFrame([_base_row(i) for i in range(5)])
        report = build_quality_report(df, schema)
        assert all(v == 0 for v in report.out_of_range_counts.values())


class TestFlatlineDetection:
    def test_detects_flatline(self, schema) -> None:  # type: ignore[no-untyped-def]
        # discharge_pressure flatline threshold = 30 min
        rows = [_base_row(i) for i in range(40)]
        for row in rows:
            row["discharge_pressure"] = 8.0  # constant for 40 minutes
        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        flatlines = [f for f in report.flatline_segments if f.sensor == "discharge_pressure"]
        assert len(flatlines) >= 1
        assert flatlines[0].duration_minutes >= 30

    def test_no_flatline_below_threshold(self, schema) -> None:  # type: ignore[no-untyped-def]
        # Only 20 minutes of constant value — below 30-min threshold
        rows = [_base_row(i) for i in range(20)]
        for row in rows:
            row["discharge_pressure"] = 8.0
        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        flatlines = [f for f in report.flatline_segments if f.sensor == "discharge_pressure"]
        assert len(flatlines) == 0

    def test_flatline_duration_is_exact(self, schema) -> None:  # type: ignore[no-untyped-def]
        # 35 rows at 1-min apart → run spans minutes 0..34 = 34 minutes
        rows = [_base_row(i) for i in range(35)]
        for row in rows:
            row["discharge_pressure"] = 8.0
        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        flatlines = [f for f in report.flatline_segments if f.sensor == "discharge_pressure"]
        assert len(flatlines) == 1
        assert flatlines[0].duration_minutes == pytest.approx(34.0)

    def test_flatline_followed_by_normal_values(self, schema) -> None:  # type: ignore[no-untyped-def]
        # First 35 rows flat, then values change — flatline should end at row 34, not row 35
        rows = [_base_row(i) for i in range(40)]
        for row in rows[:35]:
            row["discharge_pressure"] = 8.0
        for i, row in enumerate(rows[35:]):
            row["discharge_pressure"] = 9.0 + i
        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        flatlines = [f for f in report.flatline_segments if f.sensor == "discharge_pressure"]
        assert len(flatlines) == 1
        assert flatlines[0].duration_minutes == pytest.approx(34.0)
        assert flatlines[0].value == pytest.approx(8.0)

    def test_multiple_flatline_segments(self, schema) -> None:  # type: ignore[no-untyped-def]
        # Two separate flatlines separated by varying values.
        # Use a base datetime and timedelta to avoid minute-overflow in _ts().
        base = datetime(2024, 2, 1, tzinfo=UTC)

        def _trow(minutes: int, pressure: float) -> dict:  # type: ignore[type-arg]
            return {
                "timestamp": pd.Timestamp(base) + pd.Timedelta(minutes=minutes),
                "station_id": "s1",
                "device_id": "dev-A",
                "discharge_pressure": pressure,
                "air_flow_rate": 100.0,
                "power_consumption": 50.0,
                "motor_speed": 1500,
                "discharge_temp": 60.0,
            }

        # first flatline: minutes 0-34 (35 rows, duration=34min ≥ 30 threshold)
        rows = [_trow(m, 8.0) for m in range(35)]
        # break: minutes 35-39
        rows += [_trow(35 + i, 5.0 + i) for i in range(5)]
        # second flatline: minutes 40-74 (35 rows, duration=34min ≥ 30 threshold)
        rows += [_trow(40 + m, 12.0) for m in range(35)]

        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        flatlines = [f for f in report.flatline_segments if f.sensor == "discharge_pressure"]
        assert len(flatlines) == 2
        assert flatlines[0].value == pytest.approx(8.0)
        assert flatlines[1].value == pytest.approx(12.0)


class TestQualityScore:
    def test_perfect_data_scores_high(self, schema) -> None:  # type: ignore[no-untyped-def]
        df = pd.DataFrame([_base_row(i) for i in range(10)])
        report = build_quality_report(df, schema)
        assert report.quality_score > 90.0

    def test_heavy_nulls_lower_score(self, schema) -> None:  # type: ignore[no-untyped-def]
        rows = [_base_row(i) for i in range(10)]
        for row in rows:
            row["discharge_pressure"] = None
            row["air_flow_rate"] = None
        df = pd.DataFrame(rows)
        report = build_quality_report(df, schema)
        assert report.quality_score < 70.0
