"""Project paths and small shared helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_PATH = Path(os.environ.get("ACO_WAREHOUSE", DATA_DIR / "warehouse" / "aco.duckdb"))
RESULTS_DIR = ROOT / "results"
DBT_DIR = ROOT / "warehouse"
DOCS_DIR = ROOT / "docs"

# Keep DuckDB modest: other jobs share this machine.
DUCKDB_MEMORY_LIMIT = os.environ.get("ACO_DUCKDB_MEMORY_LIMIT", "1GB")
DUCKDB_THREADS = int(os.environ.get("ACO_DUCKDB_THREADS", "2"))


def load_yaml(path: Path):
    import yaml

    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False, default=str)
        fh.write("\n")
    tmp.replace(path)


def connect(read_only: bool = False):
    """Open the project DuckDB file with the memory cap applied."""
    import duckdb

    WAREHOUSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(
        str(WAREHOUSE_PATH),
        read_only=read_only,
        config={"memory_limit": DUCKDB_MEMORY_LIMIT, "threads": DUCKDB_THREADS},
    )
    return con
