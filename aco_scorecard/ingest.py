"""Load the downloaded CSV files into the DuckDB `raw` schema, one table per file.

Every value is loaded as text, exactly as published; typing and unit changes happen in the
dbt staging models generated from config/schema_mapping.yml. Before a table is accepted the
loader checks, and stops on failure:
  * the file's sha256 still matches the download manifest,
  * every column the schema mapping reads for that period exists in the file,
  * every quality measure column in the file is mapped (nothing is dropped silently).
Header whitespace is trimmed (PY 2017 county headers end in a tab). A load audit table
(raw._load_audit) and results/ingest_report.json record what was loaded.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone

from .download import hash_file
from .mapping import load_mapping
from .paths import RAW_DIR, RESULTS_DIR, ROOT, connect, write_json

MEASURE_COLUMN = re.compile(r"^(ACO\d+|DM_Comp|CAHPS_\d+|Measure_\w+|QualityID_[\w-]+)$")


class IngestError(RuntimeError):
    pass


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def load_file(con, key: str, path, sha256: str, loaded_at: str) -> dict:
    sha_now, _, _ = hash_file(path)
    if sha_now != sha256:
        raise IngestError(f"{key}: file on disk does not match the manifest sha256; rerun the download step")
    encoding = "utf-8"
    try:
        con.execute(
            f"create or replace temp table _stage as select * from read_csv(?, header = true, all_varchar = true, sample_size = -1)",
            [str(path)],
        )
    except Exception:
        encoding = "latin-1"
        con.execute(
            f"create or replace temp table _stage as select * from read_csv(?, header = true, all_varchar = true, sample_size = -1, encoding = 'latin-1')",
            [str(path)],
        )
    original = [r[0] for r in con.execute("describe _stage").fetchall()]
    trimmed = [c.strip() for c in original]
    if len(set(trimmed)) != len(trimmed):
        raise IngestError(f"{key}: duplicate column names after trimming whitespace")
    select_list = ", ".join(f"{_quote(o)} as {_quote(t)}" for o, t in zip(original, trimmed))
    con.execute(
        f"""
        create or replace table raw.{key} as
        select {select_list},
               ? as _source_file_key,
               ? as _source_sha256,
               ? as _source_path,
               cast(? as timestamp) as _loaded_at,
               row_number() over () as _source_row_number
        from _stage
        """,
        [key, sha256, str(path.relative_to(ROOT)), loaded_at],
    )
    rows = con.execute(f"select count(*) from raw.{key}").fetchone()[0]
    return {
        "columns": trimmed,
        "renamed_headers": [o for o, t in zip(original, trimmed) if o != t],
        "rows": rows,
        "encoding": encoding,
    }


def ingest() -> dict:
    manifest_path = RAW_DIR / "manifest.json"
    if not manifest_path.exists():
        raise IngestError("data/raw/manifest.json not found; run the download step first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mapping = load_mapping()
    period_by_file = {p["file_key"]: p["id"] for p in mapping.periods}
    county_by_file = {p["county_file_key"]: p["id"] for p in mapping.periods if p.get("county_file_key")}
    loaded_at = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat()

    con = connect()
    con.execute("create schema if not exists raw")
    report = {"loaded_at_utc": loaded_at, "files": []}
    audit_rows = []
    for f in manifest["files"]:
        key = f["key"]
        path = ROOT / f["path"]
        info = load_file(con, key, path, f["sha256"], loaded_at)
        cols = set(info["columns"])
        if key in period_by_file:
            pid = period_by_file[key]
            required = mapping.required_columns(pid)
            mapped_measures = {q["column"] for q in mapping.quality.get(pid, [])}
            unmapped_measures = sorted(c for c in cols if MEASURE_COLUMN.match(c) and c not in mapped_measures)
            if unmapped_measures:
                raise IngestError(f"{key}: quality measure columns not in the schema mapping: {unmapped_measures}")
        elif key in county_by_file:
            pid = county_by_file[key]
            required = mapping.required_county_columns(pid)
        else:
            raise IngestError(f"{key}: no period in the schema mapping uses this file")
        missing = sorted(required - cols)
        if missing:
            raise IngestError(f"{key}: columns named in the schema mapping are missing from the file: {missing}")
        unmapped = sorted(cols - required)
        if f.get("data_lines") is not None and f["data_lines"] != info["rows"]:
            print(f"  note: {key} has {f['data_lines']} data lines but {info['rows']} parsed rows (quoted line breaks)")
        entry = {
            "key": key,
            "period_id": pid,
            "series": f["series"],
            "rows": info["rows"],
            "n_columns": len(info["columns"]),
            "n_columns_mapped": len(required),
            "n_columns_not_used": len(unmapped),
            "columns_not_used": unmapped,
            "renamed_headers": info["renamed_headers"],
            "encoding": info["encoding"],
            "sha256": f["sha256"],
        }
        report["files"].append(entry)
        audit_rows.append((key, pid, f["series"], info["rows"], len(info["columns"]), len(required), f["sha256"], f["path"], f.get("last_modified"), f.get("downloaded_at"), loaded_at))
        print(f"[raw] {key:<16} period={pid:<6} rows={info['rows']:<7} cols={len(info['columns']):<4} mapped={len(required):<4} not_used={len(unmapped)}")

    con.execute(
        """
        create or replace table raw._load_audit (
            file_key varchar, period_id varchar, series varchar, row_count bigint, column_count integer,
            mapped_column_count integer, sha256 varchar, source_path varchar, http_last_modified varchar,
            downloaded_at varchar, loaded_at timestamp
        )
        """
    )
    con.executemany("insert into raw._load_audit values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, cast(? as timestamp))", audit_rows)
    con.close()
    report["total_rows"] = sum(x["rows"] for x in report["files"])
    write_json(RESULTS_DIR / "ingest_report.json", report)
    print(f"done: {len(report['files'])} tables, {report['total_rows']:,} rows")
    return report


def main() -> int:
    try:
        ingest()
    except IngestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
