"""Load and expand config/schema_mapping.yml.

The YAML uses period ranges ("2016..2020") so the mapping stays readable. This module expands
them into an explicit period by period spec that the staging generator, the loader checks and
the docs all share.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .paths import CONFIG_DIR, load_yaml

MAPPING_PATH = CONFIG_DIR / "schema_mapping.yml"
PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


@dataclass(frozen=True)
class Source:
    column: str | None = None
    scale: float | None = None
    expr: str | None = None

    def columns(self) -> list[str]:
        if self.column:
            return [self.column]
        if self.expr:
            return PLACEHOLDER.findall(self.expr)
        return []


@dataclass
class Field:
    name: str
    type: str
    description: str = ""
    unit: str | None = None
    sources: dict[str, Source | None] = field(default_factory=dict)


@dataclass
class Mapping:
    version: str
    periods: list[dict]
    fields: list[Field]
    tracks: dict[str, dict]
    quality: dict[str, list[dict]]
    county_periods: list[str]
    county_fields: list[Field]
    raw: dict

    @property
    def period_ids(self) -> list[str]:
        return [p["id"] for p in self.periods]

    def period(self, period_id: str) -> dict:
        for p in self.periods:
            if p["id"] == period_id:
                return p
        raise KeyError(period_id)

    def required_columns(self, period_id: str) -> set[str]:
        """Every raw column the financial and quality staging models read for a period."""
        cols: set[str] = set()
        for f in self.fields:
            src = f.sources.get(period_id)
            if src:
                cols.update(src.columns())
        track = self.tracks.get(period_id) or {}
        cols.update((track.get("flags") or {}).keys())
        if track.get("code"):
            cols.add(track["code"]["column"])
        for q in self.quality.get(period_id, []):
            cols.add(q["column"])
        return cols

    def required_county_columns(self, period_id: str) -> set[str]:
        cols: set[str] = set()
        for f in self.county_fields:
            src = f.sources.get(period_id)
            if src:
                cols.update(src.columns())
        return cols


def expand_range(key: str, order: list[str]) -> list[str]:
    key = str(key)
    if ".." not in key:
        if key not in order:
            raise ValueError(f"unknown period {key!r}")
        return [key]
    start, end = key.split("..", 1)
    if start not in order or end not in order:
        raise ValueError(f"unknown period in range {key!r}")
    i, j = order.index(start), order.index(end)
    if j < i:
        raise ValueError(f"range runs backwards: {key!r}")
    return order[i : j + 1]


def _parse_source(spec) -> Source | None:
    if spec is None:
        return None
    if isinstance(spec, str):
        return Source(column=spec)
    if isinstance(spec, dict):
        if "expr" in spec:
            return Source(expr=spec["expr"])
        return Source(column=spec["column"], scale=spec.get("scale"))
    raise ValueError(f"bad source spec: {spec!r}")


def _expand_sources(raw_sources: dict, order: list[str], name: str) -> dict[str, Source | None]:
    out: dict[str, Source | None] = {}
    for key, spec in (raw_sources or {}).items():
        for pid in expand_range(key, order):
            if pid in out:
                raise ValueError(f"{name}: period {pid} mapped twice")
            out[pid] = _parse_source(spec)
    return out


@lru_cache(maxsize=1)
def load_mapping(path: Path = MAPPING_PATH) -> Mapping:
    raw = load_yaml(path)
    periods = raw["periods"]
    order = [p["id"] for p in periods]

    fields = []
    seen = set()
    for f in raw["fields"]:
        if f["name"] in seen:
            raise ValueError(f"duplicate field {f['name']}")
        seen.add(f["name"])
        fields.append(
            Field(
                name=f["name"],
                type=f["type"],
                description=f.get("description", ""),
                unit=f.get("unit"),
                sources=_expand_sources(f.get("sources"), order, f["name"]),
            )
        )

    tracks: dict[str, dict] = {}
    for key, spec in raw["tracks"].items():
        for pid in expand_range(key, order):
            tracks[pid] = spec

    quality: dict[str, list[dict]] = {pid: [] for pid in order}
    for m in raw.get("quality_measures", []):
        for key, column in m["sources"].items():
            for pid in expand_range(key, order):
                quality[pid].append(
                    {
                        "measure_key": m["measure_key"],
                        "collection": m["collection"],
                        "column": column,
                        "scale": m.get("scale"),
                    }
                )
    for pid, rows in quality.items():
        pairs = [(r["measure_key"], r["collection"]) for r in rows]
        if len(pairs) != len(set(pairs)):
            raise ValueError(f"duplicate measure and collection pair in period {pid}")
        cols = [r["column"] for r in rows]
        if len(cols) != len(set(cols)):
            raise ValueError(f"a raw column is mapped to two measures in period {pid}")

    county_periods = [str(p) for p in raw.get("county_periods", [])]
    county_fields = [
        Field(name=f["name"], type=f["type"], sources=_expand_sources(f.get("sources"), order, f["name"]))
        for f in raw.get("county_fields", [])
    ]
    return Mapping(
        version=str(raw["version"]),
        periods=periods,
        fields=fields,
        tracks=tracks,
        quality=quality,
        county_periods=county_periods,
        county_fields=county_fields,
        raw=raw,
    )
