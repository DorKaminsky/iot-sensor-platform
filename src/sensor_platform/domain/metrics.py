"""Metric computation — pure functions on DataFrames, one per metric."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd


def compute_uptime_pct(df: pd.DataFrame) -> float:
    """% of readings where motor_speed > 0 (device is running)."""
    if df.empty or "motor_speed" not in df.columns:
        return 0.0
    valid = df["motor_speed"].dropna()
    if valid.empty:
        return 0.0
    return round(float((valid > 0).mean() * 100), 2)


def compute_avg_pressure(df: pd.DataFrame) -> float:
    """Mean discharge pressure in bar."""
    col = df.get("discharge_pressure") if isinstance(df, pd.DataFrame) else None
    if col is None or col.dropna().empty:
        return float("nan")
    return round(float(col.mean()), 4)


def compute_peak_pressure(df: pd.DataFrame) -> float:
    """Maximum discharge pressure observed."""
    col = df.get("discharge_pressure") if isinstance(df, pd.DataFrame) else None
    if col is None or col.dropna().empty:
        return float("nan")
    return round(float(col.max()), 4)


def compute_specific_power(df: pd.DataFrame) -> float:
    """Mean of power_consumption / air_flow_rate (kW per m³/h).

    Rows where flow is zero or null are excluded to avoid division by zero —
    those represent idle/off periods, not an efficiency measurement.
    """
    if df.empty:
        return float("nan")
    mask = df["air_flow_rate"].notna() & (df["air_flow_rate"] > 0) & df["power_consumption"].notna()
    filtered = df[mask]
    if filtered.empty:
        return float("nan")
    ratio = filtered["power_consumption"] / filtered["air_flow_rate"]
    return round(float(ratio.mean()), 4)


def compute_cycle_count(df: pd.DataFrame) -> float:
    """Number of on/off transitions detected via motor_speed crossing zero."""
    if df.empty or "motor_speed" not in df.columns:
        return 0.0
    valid = df["motor_speed"].dropna()
    if valid.empty:
        return 0.0
    running = (valid > 0).astype(int)
    # A transition is a change from 0→1 or 1→0
    transitions = (running.diff().abs() == 1).sum()
    # Each cycle = one start + one stop = 2 transitions; round down
    return float(transitions // 2)


def compute_total_flow_volume(df: pd.DataFrame, freq_minutes: float) -> float:
    """Approximate total air volume in m³ by integrating flow rate over time.

    volume = sum(flow_rate * interval_hours)
    freq_minutes must match the resample frequency used before calling this.
    """
    if df.empty or "air_flow_rate" not in df.columns:
        return 0.0
    flow = df["air_flow_rate"].dropna()
    if flow.empty:
        return 0.0
    interval_hours = freq_minutes / 60.0
    return round(float(flow.sum() * interval_hours), 2)


METRIC_REGISTRY: dict[str, Callable[[pd.DataFrame], float]] = {
    "uptime_pct": compute_uptime_pct,
    "avg_pressure": compute_avg_pressure,
    "peak_pressure": compute_peak_pressure,
    "specific_power": compute_specific_power,
    "cycle_count": compute_cycle_count,
}
