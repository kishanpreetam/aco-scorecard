import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ACO_WAREHOUSE", str(ROOT / "data" / "warehouse" / "aco.duckdb"))

from aco_scorecard.paths import WAREHOUSE_PATH  # noqa: E402


@pytest.fixture(scope="session")
def con():
    if not WAREHOUSE_PATH.exists():
        pytest.skip("warehouse not built; run make all")
    import duckdb

    c = duckdb.connect(str(WAREHOUSE_PATH), read_only=True, config={"memory_limit": "1GB", "threads": 2})
    yield c
    c.close()


@pytest.fixture(scope="session")
def results():
    def load(name):
        path = ROOT / "results" / name
        if not path.exists():
            pytest.skip(f"results/{name} not produced yet; run make all")
        return json.loads(path.read_text())

    return load
