"""Pipeline monitoring report: source freshness, load audit, row counts, test results and data
health indicators, written to results/pipeline_monitoring.json and .md.

Each run is also appended to results/monitoring_history.jsonl, and row counts are compared with
the previous run so an unexpected change in a public file (or in the pipeline) is visible.
"""

from __future__ import annotations

import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from importlib import metadata
from pathlib import Path

from .paths import DATA_DIR, RAW_DIR, RESULTS_DIR, connect, write_json

RUN_RESULTS_SNAPSHOT = DATA_DIR / "warehouse" / "dbt_run_results.json"
HISTORY = RESULTS_DIR / "monitoring_history.jsonl"
SCHEMAS = ("raw", "staging", "intermediate", "core", "reporting", "reference")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _version(pkg: str) -> str | None:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return None


def source_section(now: datetime) -> dict:
    manifest = json.loads((RAW_DIR / "manifest.json").read_text())
    files = []
    for f in manifest["files"] + manifest["dictionaries"]:
        lm = f.get("last_modified")
        age = None
        if lm:
            age = (now - parsedate_to_datetime(lm)).days
        files.append(
            {
                "key": f["key"],
                "kind": "dictionary" if f in manifest["dictionaries"] else "data",
                "period": f.get("period"),
                "bytes": f["bytes"],
                "sha256": f["sha256"],
                "cms_last_modified": lm,
                "days_since_cms_update": age,
                "downloaded_at": f.get("downloaded_at"),
                "pin_status": f.get("pin_status"),
            }
        )
    newest = max((x for x in files if x["kind"] == "data" and x["days_since_cms_update"] is not None), key=lambda x: -x["days_since_cms_update"])
    latest_puf_year = max(f["performance_year"] for f in manifest["files"] if f["key"].startswith("puf_"))
    discovery = None
    dpath = RESULTS_DIR / "catalog_discovery.json"
    if dpath.exists():
        d = json.loads(dpath.read_text())
        discovery = {"checked_at": d["checked_at"], "not_pinned": len(d["new_or_revised_not_pinned"]), "pinned_missing": len(d["pinned_missing_from_catalog"])}
    return {
        "files": files,
        "totals": manifest["totals"],
        "latest_performance_year_loaded": latest_puf_year,
        "most_recently_updated_file": {"key": newest["key"], "cms_last_modified": newest["cms_last_modified"]},
        "catalog_discovery": discovery,
    }


def table_counts(con) -> dict:
    rows = con.execute(
        """
        select table_schema, table_name, table_type
        from information_schema.tables
        where table_schema in ({})
        order by 1, 2
        """.format(", ".join(f"'{s}'" for s in SCHEMAS))
    ).fetchall()
    out = {}
    for schema, name, ttype in rows:
        n = con.execute(f'select count(*) from "{schema}"."{name}"').fetchone()[0]
        out[f"{schema}.{name}"] = {"rows": n, "type": "view" if "VIEW" in ttype.upper() else "table"}
    return out


def dbt_section() -> dict | None:
    if not RUN_RESULTS_SNAPSHOT.exists():
        return None
    rr = json.loads(RUN_RESULTS_SNAPSHOT.read_text())
    by_type: dict[str, Counter] = {}
    failures, timings = [], []
    for r in rr["results"]:
        uid = r["unique_id"]
        rtype = uid.split(".")[0]
        by_type.setdefault(rtype, Counter())[r["status"]] += 1
        if r["status"] not in ("pass", "success"):
            failures.append({"node": uid, "status": r["status"], "message": r.get("message"), "failures": r.get("failures")})
        timings.append((r.get("execution_time") or 0.0, uid))
    timings.sort(reverse=True)
    return {
        "invocation_id": rr["metadata"].get("invocation_id"),
        "generated_at": rr["metadata"].get("generated_at"),
        "dbt_version": rr["metadata"].get("dbt_version"),
        "elapsed_seconds": round(rr.get("elapsed_time", 0.0), 2),
        "status_by_resource_type": {k: dict(v) for k, v in by_type.items()},
        "nodes": len(rr["results"]),
        "non_passing": failures,
        "slowest_nodes": [{"node": u, "seconds": round(t, 3)} for t, u in timings[:5]],
    }


def health_section(con) -> dict:
    q = lambda sql: con.execute(sql).fetchall()
    bridge = q(
        """
        select
            (select count(*) from staging.stg_puf__py2017) as acos_2017,
            (select count(*) from staging.stg_puf__py2018 where initial_start_date < date '2018-01-01') as continuing_acos_2018,
            (select count(*) from intermediate.int_aco_id_bridge) as bridged
        """
    )[0]
    county = q(
        """
        with c as (select aco_period_key, sum(total_person_years) as rp, count(*) as n, count(*) filter (where is_suppressed) as s
                   from core.fct_aco_county_assignment group by 1)
        select f.performance_period_id, sum(c.rp) / sum(f.person_years), sum(c.s) * 1.0 / sum(c.n)
        from core.fct_aco_financial_year f join c using (aco_period_key)
        group by 1 order by 1
        """
    )
    suppressed_types = q(
        """
        select performance_period_id, count(*) filter (where person_years_esrd is null or person_years_disabled is null
                                                       or person_years_aged_dual is null or person_years_aged_nondual is null)
        from intermediate.int_aco_period__keyed group by 1 order by 1
        """
    )
    quality = q(
        """
        select performance_period_id, count(*) filter (where is_reported) * 1.0 / count(*),
               count(*) filter (where value_status = 'suppressed_small_cell'),
               count(*) filter (where value_status in ('cahps_waived_auto_credit', 'pay_for_reporting_suppressed'))
        from core.fct_aco_quality_measure group by 1 order by 1
        """
    )
    quality_score_nulls = q("select performance_period_id, count(*) filter (where quality_score is null) from core.fct_aco_financial_year group by 1 having count(*) filter (where quality_score is null) > 0 order by 1")
    keys = q("select aco_key_method, count(*) from core.dim_aco group by 1 order by 1")
    return {
        "aco_id_bridge": {
            "acos_in_py2017": bridge[0],
            "py2018_acos_started_before_2018": bridge[1],
            "bridged": bridge[2],
            "share_of_py2017_acos_bridged": round(bridge[2] / bridge[0], 4),
            "share_of_continuing_py2018_acos_bridged": round(bridge[2] / bridge[1], 4),
        },
        "dim_aco_key_methods": dict(keys),
        "county_files": [{"period": p, "reported_share_of_puf_person_years": round(cov, 4), "suppressed_row_share": round(sup, 4)} for p, cov, sup in county],
        "acos_with_a_suppressed_enrollment_type_cell": dict(suppressed_types),
        "quality_measures": [{"period": p, "reported_share": round(r, 4), "suppressed_cells": s, "waived_cells": w} for p, r, s, w in quality],
        "quality_score_null_counts": dict(quality_score_nulls),
    }


def previous_run() -> dict | None:
    if not HISTORY.exists():
        return None
    lines = [x for x in HISTORY.read_text().splitlines() if x.strip()]
    return json.loads(lines[-1]) if lines else None


def compare_with_previous(counts: dict) -> list[dict]:
    last = previous_run()
    if last is None:
        return []
    prev = last["row_counts"]
    changes = []
    for name, info in counts.items():
        old = prev.get(name)
        if old is None:
            changes.append({"relation": name, "previous": None, "current": info["rows"], "note": "new relation"})
        elif old != info["rows"]:
            changes.append({"relation": name, "previous": old, "current": info["rows"], "note": "row count changed"})
    for name in prev:
        if name not in counts:
            changes.append({"relation": name, "previous": prev[name], "current": None, "note": "relation removed"})
    return changes


def main() -> int:
    now = _now()
    con = connect(read_only=True)
    counts = table_counts(con)
    load_audit = [
        dict(zip(["file_key", "period_id", "rows", "columns", "loaded_at"], r))
        for r in con.execute("select file_key, period_id, row_count, column_count, cast(loaded_at as varchar) from raw._load_audit order by file_key").fetchall()
    ]
    health = health_section(con)
    con.close()

    semantic = None
    spath = RESULTS_DIR / "semantic_layer_tests.json"
    if spath.exists():
        semantic = json.loads(spath.read_text())["summary"]
    dbt = dbt_section()
    last_run = previous_run()
    changes = compare_with_previous(counts)

    checks = []
    if dbt:
        bad = len(dbt["non_passing"])
        checks.append({"check": "dbt build: every model, seed, data test and unit test passed", "pass": bad == 0, "detail": f"{dbt['nodes']} nodes, {bad} not passing"})
    if semantic:
        checks.append({"check": "semantic layer answers match independent SQL", "pass": semantic["questions_passed"] == semantic["questions"], "detail": f"{semantic['questions_passed']}/{semantic['questions']} questions, {semantic['values_passed']}/{semantic['values_compared']} values"})
    sources = source_section(now)
    pins_ok = all(f["pin_status"] in ("verified", "pinned (first download)") for f in sources["files"])
    checks.append({"check": "every source file matches its sha256 pin", "pass": pins_ok, "detail": f"{len(sources['files'])} files"})
    expected_periods = 13
    loaded_periods = len({r["period_id"] for r in load_audit if r["file_key"].startswith("puf_")})
    checks.append({"check": "all 13 PUF performance periods loaded", "pass": loaded_periods == expected_periods, "detail": f"{loaded_periods} loaded"})
    if last_run is None:
        detail = "first recorded run, nothing to compare"
    else:
        detail = f"{len(changes)} differences from the run at {last_run['generated_at']}" if changes else f"no differences from the run at {last_run['generated_at']}"
    checks.append({"check": "row counts unchanged since the previous run", "pass": not [c for c in changes if c["note"] != "new relation"], "detail": detail})
    if sources["catalog_discovery"]:
        d = sources["catalog_discovery"]
        checks.append({"check": "no new or revised CMS files waiting in the catalog", "pass": d["not_pinned"] == 0 and d["pinned_missing"] == 0, "detail": f"checked {d['checked_at']}: {d['not_pinned']} not pinned, {d['pinned_missing']} pinned files missing"})

    report = {
        "generated_at": now.isoformat(),
        "environment": {
            "python": platform.python_version(),
            "duckdb": _version("duckdb"),
            "dbt_core": _version("dbt-core"),
            "dbt_duckdb": _version("dbt-duckdb"),
            "metricflow": _version("metricflow"),
            "platform": platform.platform(terse=True),
        },
        "checks": checks,
        "all_checks_passed": all(c["pass"] for c in checks),
        "sources": sources,
        "load_audit": load_audit,
        "row_counts": counts,
        "row_count_changes_vs_previous_run": changes,
        "dbt": dbt,
        "semantic_layer": semantic,
        "data_health": health,
    }
    write_json(RESULTS_DIR / "pipeline_monitoring.json", report)
    with open(HISTORY, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"generated_at": report["generated_at"], "all_checks_passed": report["all_checks_passed"], "row_counts": {k: v["rows"] for k, v in counts.items()}}) + "\n")
    write_markdown(report)
    print(f"monitoring: {sum(c['pass'] for c in checks)}/{len(checks)} checks passed")
    for c in checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['check']} ({c['detail']})")
    return 0 if report["all_checks_passed"] else 1


def write_markdown(r: dict) -> None:
    L = ["# Pipeline monitoring report", "", f"Generated {r['generated_at']}.", ""]
    L += ["## Checks", "", "| check | result | detail |", "|---|---|---|"]
    L += [f"| {c['check']} | {'pass' if c['pass'] else 'FAIL'} | {c['detail']} |" for c in r["checks"]]
    s = r["sources"]
    L += ["", "## Sources", "", f"{s['totals']['data_files']} data files ({s['totals']['data_bytes']:,} bytes) and {s['totals']['dictionary_files']} data dictionaries ({s['totals']['dictionary_bytes']:,} bytes) from data.cms.gov. Latest performance year loaded: {s['latest_performance_year_loaded']}. Most recently revised file: {s['most_recently_updated_file']['key']} ({s['most_recently_updated_file']['cms_last_modified']}).", ""]
    L += ["| file | period | bytes | CMS last modified | days since CMS update | pin |", "|---|---|---|---|---|---|"]
    L += [f"| {f['key']} | {f['period'] or ''} | {f['bytes']:,} | {f['cms_last_modified'] or ''} | {f['days_since_cms_update'] if f['days_since_cms_update'] is not None else ''} | {f['pin_status']} |" for f in s["files"]]
    if r["dbt"]:
        d = r["dbt"]
        L += ["", "## dbt build", "", f"dbt {d['dbt_version']}, {d['nodes']} nodes in {d['elapsed_seconds']} seconds.", "", "| resource type | status counts |", "|---|---|"]
        L += [f"| {k} | {', '.join(f'{s}: {n}' for s, n in v.items())} |" for k, v in d["status_by_resource_type"].items()]
        if d["non_passing"]:
            L += ["", "Not passing:"] + [f"- {x['node']}: {x['status']} {x['message']}" for x in d["non_passing"]]
    if r["semantic_layer"]:
        sl = r["semantic_layer"]
        L += ["", "## Semantic layer", "", f"{sl['questions_passed']} of {sl['questions']} business questions passed; {sl['values_passed']} of {sl['values_compared']} values matched plain SQL."]
    L += ["", "## Row counts", "", "| relation | type | rows |", "|---|---|---|"]
    L += [f"| {k} | {v['type']} | {v['rows']:,} |" for k, v in r["row_counts"].items() if not k.startswith("staging.")]
    staging_rows = sum(v["rows"] for k, v in r["row_counts"].items() if k.startswith("staging."))
    n_staging = sum(1 for k in r["row_counts"] if k.startswith("staging."))
    L += [f"| staging ({n_staging} views) | view | {staging_rows:,} |"]
    h = r["data_health"]
    b = h["aco_id_bridge"]
    L += ["", "## Data health", "", f"- ACO identifier bridge (PY 2017 to PY 2018): {b['bridged']} of {b['acos_in_py2017']} PY 2017 ACOs linked ({b['share_of_py2017_acos_bridged']:.1%}); {b['share_of_continuing_py2018_acos_bridged']:.1%} of the {b['py2018_acos_started_before_2018']} PY 2018 ACOs that started before 2018."]
    L += [f"- ACO keys by method: " + ", ".join(f"{k} {v}" for k, v in h["dim_aco_key_methods"].items()) + "."]
    L += ["- County files: reported (unsuppressed) county person years as a share of PUF person years: " + ", ".join(f"{c['period']} {c['reported_share_of_puf_person_years']:.1%}" for c in h["county_files"]) + "."]
    L += ["- Quality results reported share: " + ", ".join(f"{q['period']} {q['reported_share']:.1%}" for q in h["quality_measures"]) + "."]
    L += ["- ACO rows with a suppressed enrollment type cell: " + ", ".join(f"{k} {v}" for k, v in h["acos_with_a_suppressed_enrollment_type_cell"].items() if v) + "."]
    L += ["- Quality score not published (pay for reporting): " + ", ".join(f"{k} {v}" for k, v in h["quality_score_null_counts"].items()) + "."]
    if r["row_count_changes_vs_previous_run"]:
        L += ["", "## Row count changes since the previous run", ""] + [f"- {c['relation']}: {c['previous']} to {c['current']} ({c['note']})" for c in r["row_count_changes_vs_previous_run"]]
    (RESULTS_DIR / "pipeline_monitoring.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
