"""Schema loading — parses sensor_schema.json into typed objects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidRange:
    min: float
    max: float

    def contains(self, value: float) -> bool:
        return self.min <= value <= self.max


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    type: str
    required: bool
    valid_range: ValidRange | None


@dataclass(frozen=True)
class SensorSpec:
    category: str
    typical_range: ValidRange
    flatline_threshold_minutes: int


@dataclass(frozen=True)
class Schema:
    version: str
    columns: dict[str, ColumnSpec]
    sensor_specs: dict[str, SensorSpec]

    @classmethod
    def from_file(cls, path: str | Path) -> Schema:
        with open(path) as f:
            raw = json.load(f)

        columns: dict[str, ColumnSpec] = {}
        for name, col in raw["tables"]["sensor_readings"]["columns"].items():
            vr = col.get("valid_range")
            columns[name] = ColumnSpec(
                name=name,
                type=col["type"],
                required=col["required"],
                valid_range=ValidRange(vr["min"], vr["max"]) if vr else None,
            )

        sensor_specs: dict[str, SensorSpec] = {}
        for name, spec in raw["sensor_types"].items():
            tr = spec["typical_operating_range"]
            sensor_specs[name] = SensorSpec(
                category=spec["category"],
                typical_range=ValidRange(tr["min"], tr["max"]),
                flatline_threshold_minutes=spec["flatline_threshold_minutes"],
            )

        return cls(version=raw["version"], columns=columns, sensor_specs=sensor_specs)
