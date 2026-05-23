"""DataSource protocol — abstract interface for reading sensor data."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd

from sensor_platform.domain.models import Station


class DataSource(Protocol):
    def read_readings(
        self,
        station_id: str | None = None,
        device_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> pd.DataFrame:
        """Return DataFrame with columns: timestamp, station_id, device_id, <sensor cols>."""
        ...

    def read_stations(self) -> list[Station]:
        """Return all station metadata."""
        ...
