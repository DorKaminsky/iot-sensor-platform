"""Unit tests for domain metric functions."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from sensor_platform.domain.metrics import (
    compute_avg_pressure,
    compute_cycle_count,
    compute_peak_pressure,
    compute_specific_power,
    compute_total_flow_volume,
    compute_uptime_pct,
)


def _df(**cols: list) -> pd.DataFrame:  # type: ignore[type-arg]
    return pd.DataFrame(cols)


class TestUptimePct:
    def test_all_running(self) -> None:
        df = _df(motor_speed=[1000, 1500, 2000])
        assert compute_uptime_pct(df) == 100.0

    def test_all_stopped(self) -> None:
        df = _df(motor_speed=[0, 0, 0])
        assert compute_uptime_pct(df) == 0.0

    def test_mixed(self) -> None:
        df = _df(motor_speed=[0, 1000, 0, 1000])
        assert compute_uptime_pct(df) == 50.0

    def test_with_nulls(self) -> None:
        df = _df(motor_speed=[None, 1000, None, 1000])
        assert compute_uptime_pct(df) == 100.0

    def test_empty(self) -> None:
        assert compute_uptime_pct(pd.DataFrame()) == 0.0


class TestAvgPressure:
    def test_basic(self) -> None:
        df = _df(discharge_pressure=[8.0, 9.0, 10.0])
        assert compute_avg_pressure(df) == pytest.approx(9.0)

    def test_all_null(self) -> None:
        df = _df(discharge_pressure=[None, None])
        assert math.isnan(compute_avg_pressure(df))

    def test_empty(self) -> None:
        assert math.isnan(compute_avg_pressure(pd.DataFrame()))


class TestPeakPressure:
    def test_basic(self) -> None:
        df = _df(discharge_pressure=[7.0, 12.5, 9.0])
        assert compute_peak_pressure(df) == pytest.approx(12.5)


class TestSpecificPower:
    def test_basic(self) -> None:
        # 100 kW / 50 m³h = 2.0
        df = _df(power_consumption=[100.0, 100.0], air_flow_rate=[50.0, 50.0])
        assert compute_specific_power(df) == pytest.approx(2.0)

    def test_excludes_zero_flow(self) -> None:
        # Row with zero flow should be excluded
        df = _df(power_consumption=[100.0, 50.0], air_flow_rate=[0.0, 50.0])
        assert compute_specific_power(df) == pytest.approx(1.0)

    def test_all_zero_flow(self) -> None:
        df = _df(power_consumption=[100.0], air_flow_rate=[0.0])
        assert math.isnan(compute_specific_power(df))


class TestCycleCount:
    def test_one_cycle(self) -> None:
        df = _df(motor_speed=[0, 1000, 1000, 0])
        assert compute_cycle_count(df) == 1.0

    def test_two_cycles(self) -> None:
        df = _df(motor_speed=[0, 1000, 0, 1000, 0])
        assert compute_cycle_count(df) == 2.0

    def test_always_on(self) -> None:
        df = _df(motor_speed=[1000, 1500, 2000])
        assert compute_cycle_count(df) == 0.0

    def test_empty(self) -> None:
        assert compute_cycle_count(pd.DataFrame()) == 0.0


class TestTotalFlowVolume:
    def test_basic(self) -> None:
        # 60 m³/h * (5min/60) = 5 m³ per row, 3 rows = 15 m³
        df = _df(air_flow_rate=[60.0, 60.0, 60.0])
        assert compute_total_flow_volume(df, freq_minutes=5) == pytest.approx(15.0)

    def test_empty(self) -> None:
        assert compute_total_flow_volume(pd.DataFrame(), freq_minutes=5) == 0.0
