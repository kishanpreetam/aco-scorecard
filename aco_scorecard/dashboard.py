"""Build the static dashboard (results/dashboard.html) and the metrics file (results/metrics.json).

All values are read from the dbt marts in the DuckDB warehouse. The page is a single
self-contained HTML file: plotly.js (from the plotly package on PyPI) and the data are inlined,
so it opens offline and can be shared as one file.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from .paths import DATA_DIR, RAW_DIR, RESULTS_DIR, connect, write_json

TEMPLATE = Path(__file__).with_name("dashboard_template.html")
RUN_RESULTS_SNAPSHOT = DATA_DIR / "warehouse" / "dbt_run_results.json"
QUALITY_MEASURES = [
    ("Q113", "Colorectal cancer screening"),
    ("Q112", "Breast cancer screening"),
    ("Q236", "Controlling high blood pressure"),
    ("Q134", "Depression screening and follow-up"),
    ("Q001", "HbA1c poor control (lower is better)"),
]


def rows(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    out = []
    for r in cur.fetchall():
        rec = {}
        for c, v in zip(cols, r):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                v = None
            elif hasattr(v, "isoformat"):
                v = v.isoformat()
            elif v is not None and type(v).__name__ == "Decimal":
                v = float(v)
            rec[c] = v
        out.append(rec)
    return out


def pipeline_summary(con) -> dict:
    manifest = json.loads((RAW_DIR / "manifest.json").read_text())
    tests_total = tests_passed = unit_total = unit_passed = None
    if RUN_RESULTS_SNAPSHOT.exists():
        rr = json.loads(RUN_RESULTS_SNAPSHOT.read_text())["results"]
        data_tests = [r for r in rr if r["unique_id"].startswith("test.")]
        units = [r for r in rr if r["unique_id"].startswith("unit_test.")]
        tests_total, tests_passed = len(data_tests), sum(r["status"] == "pass" for r in data_tests)
        unit_total, unit_passed = len(units), sum(r["status"] == "pass" for r in units)
    sem = {}
    spath = RESULTS_DIR / "semantic_layer_tests.json"
    if spath.exists():
        sem = json.loads(spath.read_text())["summary"]
    bridge = con.execute("select (select count(*) from intermediate.int_aco_id_bridge), (select count(*) from staging.stg_puf__py2017)").fetchone()
    counts = con.execute(
        """select (select count(*) from core.dim_aco), (select count(*) from core.fct_aco_financial_year),
                  (select count(*) from core.fct_aco_quality_measure), (select count(*) from core.fct_aco_county_assignment),
                  (select count(*) from core.fct_attribution)"""
    ).fetchone()
    chips = [
        f"{unit_passed} of {unit_total} dbt unit tests passed" if unit_total is not None else "dbt unit tests not run",
        "13 performance periods, PY 2013 to 2024",
        f"{counts[0]:,} ACOs tracked across years",
        f"{counts[1]:,} ACO performance periods",
        f"{counts[2]:,} quality measure results",
        f"{counts[4]:,} attribution rows by enrollment type",
        f"{counts[3]:,} ACO by county rows",
        f"{sem.get('values_passed', 0)} of {sem.get('values_compared', 0)} semantic layer values matched plain SQL",
    ]
    return {
        "dbt_tests_total": tests_total,
        "dbt_tests_passed": tests_passed,
        "dbt_unit_tests_total": unit_total,
        "dbt_unit_tests_passed": unit_passed,
        "semantic_total": sem.get("questions"),
        "semantic_passed": sem.get("questions_passed"),
        "semantic_values_compared": sem.get("values_compared"),
        "semantic_values_passed": sem.get("values_passed"),
        "files_pinned": manifest["totals"]["data_files"] + manifest["totals"]["dictionary_files"],
        "bytes": manifest["totals"]["all_bytes"],
        "bridged": bridge[0],
        "acos_2017": bridge[1],
        "chips": chips,
    }


def latest_revision() -> str:
    from email.utils import parsedate_to_datetime

    manifest = json.loads((RAW_DIR / "manifest.json").read_text())
    dated = [(parsedate_to_datetime(f["last_modified"]), f["key"]) for f in manifest["files"] if f.get("last_modified")]
    when, key = max(dated)
    return f"{key} on {when.date().isoformat()}"


def build_data(con) -> dict:
    program = rows(con, "select * from reporting.mart_program_year_summary order by performance_year")
    aco_years = rows(
        con,
        """
        select s.performance_year, s.aco_key, s.aco_name, s.risk_model, s.track_family,
               s.n_assigned_beneficiaries, round(s.savings_rate, 6) as savings_rate,
               round(s.quality_score, 2) as quality_score, round(s.earned_shared_savings, 0) as earned_shared_savings,
               round(s.savings_rate_change_yoy, 6) as savings_rate_change_yoy, d.primary_state
        from reporting.mart_aco_year_scorecard as s
        left join core.dim_aco as d using (aco_key)
        order by s.performance_year, s.aco_key
        """,
    )
    periods = rows(con, "select distinct performance_year, comparability_group, quality_measure_set from core.dim_performance_year order by 1")
    corr = {str(r["performance_year"]): (round(r["c"], 3) if r["c"] is not None else None) for r in rows(con, "select performance_year, corr(quality_score, savings_rate) as c from reporting.mart_aco_year_scorecard group by 1")}
    families = [r["track_family"] for r in rows(con, "select track_family, min(display_order) as o from core.dim_track group by 1 order by o")]
    tracks = rows(con, "select performance_year, track_family, aco_count, savings_rate, earned_shared_savings, share_of_year_earned_savings from reporting.mart_track_year_summary order by performance_year, track_family")
    keys = ", ".join(f"'{k}'" for k, _ in QUALITY_MEASURES)
    quality = rows(
        con,
        f"""select measure_key, performance_year, round(median_value, 3) as median_value, reported_results, aco_results
            from reporting.mart_quality_measure_year
            where collection_type = 'Web Interface' and measure_key in ({keys}) order by measure_key, performance_year""",
    )
    states = rows(
        con,
        """select performance_year, state_name, round(reported_person_years, 2) as reported_person_years, acos_with_beneficiaries,
                  share_of_reported_person_years, coverage_of_program, state_rank_in_year
           from reporting.mart_state_year_assignment where state_rank_in_year <= 12 order by performance_year, state_rank_in_year""",
    )
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "latest_revision": latest_revision(),
        "program_by_year": program,
        "aco_years": aco_years,
        "periods": periods,
        "correlations": corr,
        "track_families": families,
        "track_by_year": tracks,
        "quality_measures": [{"measure_key": k, "label": label} for k, label in QUALITY_MEASURES],
        "quality_trends": quality,
        "states": states,
        "pipeline": pipeline_summary(con),
    }


def metrics_file(data: dict) -> dict:
    latest = max(r["performance_year"] for r in data["program_by_year"])
    cur = next(r for r in data["program_by_year"] if r["performance_year"] == latest)
    prev = next(r for r in data["program_by_year"] if r["performance_year"] == latest - 1)
    top = sorted((r for r in data["aco_years"] if r["performance_year"] == latest), key=lambda r: -r["earned_shared_savings"])[:10]
    first = data["program_by_year"][0]
    return {
        "generated_at": data["generated_at"],
        "description": "Headline metrics computed by the ACO Scorecard pipeline from CMS Shared Savings Program public use files. Rates are fractions; dollars are nominal.",
        "latest_performance_year": latest,
        "latest_year": cur,
        "prior_year": prev,
        "change_latest_vs_prior": {
            "savings_rate_points": cur["savings_rate"] - prev["savings_rate"],
            "earned_shared_savings_dollars": cur["earned_shared_savings"] - prev["earned_shared_savings"],
            "net_savings_to_medicare_dollars": cur["net_savings_to_medicare"] - prev["net_savings_to_medicare"],
            "aco_count": cur["aco_count"] - prev["aco_count"],
        },
        "program_totals_all_years": {
            "years": f"{first['performance_year']} to {latest}",
            "benchmark_minus_expenditures": sum(r["benchmark_minus_expenditures"] for r in data["program_by_year"]),
            "earned_shared_savings": sum(r["earned_shared_savings"] for r in data["program_by_year"]),
            "shared_losses_owed": sum(r["shared_losses_owed"] for r in data["program_by_year"]),
            "net_savings_to_medicare": sum(r["net_savings_to_medicare"] for r in data["program_by_year"]),
        },
        "program_by_year": data["program_by_year"],
        "track_by_year": data["track_by_year"],
        "quality_vs_savings_correlation_by_year": data["correlations"],
        "quality_measure_medians_web_interface": data["quality_trends"],
        "top_states_by_year": data["states"],
        "top_acos_latest_year": top,
        "pipeline": data["pipeline"],
    }


def main() -> int:
    con = connect(read_only=True)
    data = build_data(con)
    con.close()
    write_json(RESULTS_DIR / "metrics.json", metrics_file(data))

    from plotly.offline import get_plotlyjs

    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=True).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__DATA_JSON__", payload).replace("__PLOTLY_JS__", get_plotlyjs())
    out = RESULTS_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB) and results/metrics.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
