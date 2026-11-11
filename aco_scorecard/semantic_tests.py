"""Test the semantic layer against real business questions.

Each question is answered twice:
  1. through MetricFlow (`mf query`), using only the governed metric definitions in
     warehouse/models/semantic/semantic_models.yml, and
  2. with hand-written SQL that reads the raw text tables (raw.puf_py*) directly, parses the
     published values itself and never touches a dbt model.
The two answers must agree (relative tolerance 1e-9). Results go to
results/semantic_layer_tests.json and .md, and a machine-readable metric catalog for BI and
AI tools goes to results/semantic_catalog.json.
"""

from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .paths import DBT_DIR, RESULTS_DIR, ROOT, WAREHOUSE_PATH, connect, write_json

MF = ROOT / ".venv" / "bin" / "mf"
REL_TOL = 1e-9
ABS_TOL = 1e-6


def num(col: str) -> str:
    """Independent parser for raw text values (strip $ , % and cast)."""
    return f"try_cast(nullif(replace(replace(replace(trim({col}), '$', ''), ',', ''), '%', ''), '') as double)"


def all_periods_union(select_sql: str, years: list[str]) -> str:
    """Apply the same SELECT to several raw PUF tables and stack the results."""
    parts = [select_sql.format(t=f"raw.puf_py{y.lower()}", y=y[:4]) for y in years]
    return "\nunion all\n".join(parts)


YEARS = ["2013", "2014", "2015", "2016", "2017", "2018", "2019", "2019A", "2020", "2021", "2022", "2023", "2024"]

TRACK_2024 = """case trim("Current_Track")
        when 'A' then 'BASIC A and B (one-sided)' when 'B' then 'BASIC A and B (one-sided)'
        when 'C' then 'BASIC C to E (two-sided)' when 'D' then 'BASIC C to E (two-sided)' when 'E' then 'BASIC C to E (two-sided)'
        when 'EN' then 'ENHANCED' end"""

RISK_ADJ_ROW = """(
    coalesce(case when {r_e} > 0 then {p_e} / {r_e} * {y_e} end, 0) + coalesce(case when {r_d} > 0 then {p_d} / {r_d} * {y_d} end, 0)
  + coalesce(case when {r_u} > 0 then {p_u} / {r_u} * {y_u} end, 0) + coalesce(case when {r_n} > 0 then {p_n} / {r_n} * {y_n} end, 0)
) / nullif(
    coalesce(case when {r_e} > 0 and {p_e} is not null then {y_e} end, 0) + coalesce(case when {r_d} > 0 and {p_d} is not null then {y_d} end, 0)
  + coalesce(case when {r_u} > 0 and {p_u} is not null then {y_u} end, 0) + coalesce(case when {r_n} > 0 and {p_n} is not null then {y_n} end, 0), 0)"""


def risk_adj_expr() -> str:
    cols = {}
    for k, t in (("e", "ESRD"), ("d", "DIS"), ("u", "AGDU"), ("n", "AGND")):
        cols[f"r_{k}"] = num(f'"CMS_HCC_RiskScore_{t}_PY"')
        cols[f"p_{k}"] = num(f'"Per_Capita_Exp_ALL_{t}_PY"')
    cols["y_e"] = num('"N_AB_Year_ESRD_PY"')
    cols["y_d"] = num('"N_AB_Year_DIS_PY"')
    cols["y_u"] = num('"N_AB_Year_AGED_Dual_PY"')
    cols["y_n"] = num('"N_AB_Year_AGED_NonDual_PY"')
    return RISK_ADJ_ROW.format(**cols)


QUESTIONS = [
    {
        "id": "Q01",
        "question": "What was the program-wide savings rate (total savings over total benchmark) in each performance year from 2013 to 2024?",
        "metrics": ["savings_rate"],
        "group_by": ["metric_time__year"],
        "where": None,
        "expected_sql": "select year, sum(bme) / sum(bench) as savings_rate from ("
        + all_periods_union("select {y} as year, " + num('"BnchmkMinExp"') + " as bme, " + num('"ABtotBnchmk"') + " as bench from {t}", YEARS)
        + ") group by year",
        "keys": ["year"],
    },
    {
        "id": "Q02",
        "question": "In PY 2024, how much did CMS pay ACOs in shared savings, how much did ACOs owe in losses, and what were net savings to Medicare?",
        "metrics": ["earned_shared_savings", "shared_losses_owed", "net_savings_to_medicare"],
        "group_by": [],
        "where": "{{ Dimension('aco_period__performance_year') }} = 2024",
        "expected_sql": f"""
            select sum(greatest(e, 0)) as earned_shared_savings,
                   sum(greatest(-e, 0)) as shared_losses_owed,
                   sum(bme) - sum(greatest(e, 0)) + sum(greatest(-e, 0)) as net_savings_to_medicare
            from (select {num('"EarnSaveLoss"')} as e, {num('"BnchmkMinExp"')} as bme from raw.puf_py2024)""",
        "keys": [],
    },
    {
        "id": "Q03",
        "question": "Which track family had the highest savings rate in PY 2024?",
        "metrics": ["savings_rate"],
        "group_by": ["track__track_family"],
        "where": "{{ Dimension('aco_period__performance_year') }} = 2024",
        "expected_sql": f"""
            select {TRACK_2024} as track_family, sum({num('"BnchmkMinExp"')}) / sum({num('"ABtotBnchmk"')}) as savings_rate
            from raw.puf_py2024 group by 1""",
        "keys": ["track_family"],
    },
    {
        "id": "Q04",
        "question": "How many distinct ACOs were reconciled in PY 2019, counting both the January and July 2019 periods?",
        "metrics": ["aco_count"],
        "group_by": [],
        "where": "{{ Dimension('aco_period__performance_year') }} = 2019",
        "expected_sql": 'select count(distinct id) as aco_count from (select trim("ACO_ID") as id from raw.puf_py2019 union all select trim("ACO_ID") from raw.puf_py2019a)',
        "keys": [],
    },
    {
        "id": "Q05",
        "question": "What share of ACO reconciliations earned a shared savings payment in each year from 2021 to 2024?",
        "metrics": ["share_earning_savings"],
        "group_by": ["metric_time__year"],
        "where": "{{ Dimension('aco_period__performance_year') }} >= 2021",
        "expected_sql": "select year, avg(case when e > 0 then 1.0 else 0.0 end) as share_earning_savings from ("
        + all_periods_union("select {y} as year, " + num('"EarnSaveLoss"') + " as e from {t}", ["2021", "2022", "2023", "2024"])
        + ") group by year",
        "keys": ["year"],
    },
    {
        "id": "Q06",
        "question": "In PY 2023, how did earned shared savings per assigned beneficiary compare between one-sided and two-sided ACOs?",
        "metrics": ["earned_shared_savings_per_assigned_beneficiary"],
        "group_by": ["aco_period__risk_model"],
        "where": "{{ Dimension('aco_period__performance_year') }} = 2023",
        "expected_sql": f"""
            select trim("Risk_Model") as risk_model,
                   sum(greatest({num('"EarnSaveLoss"')}, 0)) / sum({num('"N_AB"')}) as earned_shared_savings_per_assigned_beneficiary
            from raw.puf_py2023 group by 1""",
        "keys": ["risk_model"],
    },
    {
        "id": "Q07",
        "question": "What was the mean ACO quality score in each year of the APM Performance Pathway era (2021 to 2024)?",
        "metrics": ["mean_quality_score"],
        "group_by": ["metric_time__year"],
        "where": "{{ Dimension('aco_period__performance_year') }} >= 2021",
        "expected_sql": "select year, avg(q) as mean_quality_score from ("
        + all_periods_union("select {y} as year, " + num('"QualScore"') + " as q from {t}", ["2021", "2022", "2023", "2024"])
        + ") group by year",
        "keys": ["year"],
    },
    {
        "id": "Q08",
        "question": "What was risk-adjusted per capita expenditure (spending divided by CMS-HCC risk score, by enrollment type) in PY 2023 and PY 2024?",
        "metrics": ["risk_adjusted_per_capita_expenditure"],
        "group_by": ["metric_time__year"],
        "where": "{{ Dimension('aco_period__performance_year') }} in (2023, 2024)",
        "expected_sql": "select year, sum(rapc * py) / sum(py) as risk_adjusted_per_capita_expenditure from ("
        + all_periods_union("select {y} as year, " + risk_adj_expr() + " as rapc, " + num('"N_AB_Year_PY"') + " as py from {t}", ["2023", "2024"])
        + ") group by year",
        "keys": ["year"],
    },
    {
        "id": "Q09",
        "question": "How many Medicare beneficiaries were assigned to Shared Savings Program ACOs in PY 2024?",
        "metrics": ["assigned_beneficiaries"],
        "group_by": [],
        "where": "{{ Dimension('aco_period__performance_year') }} = 2024",
        "expected_sql": f"select sum({num('\"N_AB\"')}) as assigned_beneficiaries from raw.puf_py2024",
        "keys": [],
    },
    {
        "id": "Q10",
        "question": "What was the person-year weighted mean CMS-HCC risk score for each Medicare enrollment type in PY 2024?",
        "metrics": ["mean_risk_score"],
        "group_by": ["attribution_row__enrollment_type_code"],
        "where": "{{ TimeDimension('metric_time', 'year') }} = '2024-01-01'",
        "expected_sql": "\nunion all\n".join(
            f"select '{code}' as enrollment_type_code, sum(r * y) / sum(case when r is not null then y end) as mean_risk_score "
            f"from (select {num(chr(34) + 'CMS_HCC_RiskScore_' + t + '_PY' + chr(34))} as r, {num(chr(34) + pycol + chr(34))} as y from raw.puf_py2024)"
            for code, t, pycol in (
                ("esrd", "ESRD", "N_AB_Year_ESRD_PY"),
                ("disabled", "DIS", "N_AB_Year_DIS_PY"),
                ("aged_dual", "AGDU", "N_AB_Year_AGED_Dual_PY"),
                ("aged_nondual", "AGND", "N_AB_Year_AGED_NonDual_PY"),
            )
        ),
        "keys": ["enrollment_type_code"],
    },
    {
        "id": "Q11",
        "question": "For Controlling High Blood Pressure (Quality ID 236) in PY 2024, what share of ACOs reported a result through each collection type?",
        "metrics": ["quality_reporting_rate"],
        "group_by": ["measure_result__collection_type"],
        "where": "{{ Entity('quality_measure') }} = 'Q236' and {{ TimeDimension('metric_time', 'year') }} = '2024-01-01'",
        "expected_sql": "\nunion all\n".join(
            f"select '{label}' as collection_type, avg(case when {num(chr(34) + col + chr(34))} is not null then 1.0 else 0.0 end) as quality_reporting_rate from raw.puf_py2024"
            for label, col in (
                ("Web Interface", "QualityID_236_WI"),
                ("eCQM", "QualityID_236_eCQM"),
                ("MIPS CQM", "QualityID_236_MIPSCQM"),
                ("Medicare CQM", "QualityID_236_MedicareCQM"),
            )
        ),
        "keys": ["collection_type"],
    },
    {
        "id": "Q12",
        "question": "How many ACOs saved 5 percent or more of their benchmark in PY 2024, and what was their combined savings rate?",
        "metrics": ["aco_count", "savings_rate"],
        "group_by": [],
        "where": "{{ Dimension('aco_period__performance_year') }} = 2024 and {{ Dimension('aco_period__savings_rate_band') }} = '5 percent or more'",
        "expected_sql": f"""
            select count(*) as aco_count, sum(bme) / sum(bench) as savings_rate
            from (select {num('"BnchmkMinExp"')} as bme, {num('"ABtotBnchmk"')} as bench from raw.puf_py2024)
            where bme / bench >= 0.05""",
        "keys": [],
    },
]


def mf_env() -> dict:
    env = dict(os.environ)
    env.update(
        {
            "ACO_WAREHOUSE": str(WAREHOUSE_PATH),
            "DBT_PROFILES_DIR": str(DBT_DIR),
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            "MF_DISABLE_TRACKING": "true",
        }
    )
    return env


def mf_args(q: dict) -> list[str]:
    args = [str(MF), "query", "--metrics", ",".join(q["metrics"])]
    if q["group_by"]:
        args += ["--group-by", ",".join(q["group_by"])]
    if q["where"]:
        args += ["--where", q["where"]]
    return args


def run_mf(q: dict) -> tuple[list[dict], str]:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "result.csv"
        res = subprocess.run(mf_args(q) + ["--csv", str(out)], cwd=DBT_DIR, env=mf_env(), capture_output=True, text=True, timeout=300)
        if res.returncode != 0 or not out.exists():
            raise RuntimeError(f"{q['id']}: mf query failed\n{res.stdout}\n{res.stderr}")
        with open(out, newline="") as fh:
            rows = list(csv.DictReader(fh))
    exp = subprocess.run(mf_args(q) + ["--explain"], cwd=DBT_DIR, env=mf_env(), capture_output=True, text=True, timeout=300)
    sql = exp.stdout
    if "SELECT" in sql:
        sql = sql[sql.index("SELECT"):].strip()
    return rows, sql


def _norm_key(name: str, value) -> str:
    if name in ("year", "metric_time__year", "attribution_row__attribution_year_start__year"):
        return str(value)[:4]
    return str(value)


def compare(q: dict, mf_rows: list[dict], expected_rows: list[dict]) -> dict:
    key_map = dict(zip(q["keys"], q["group_by"])) if q["keys"] else {}
    mf_index = {}
    for r in mf_rows:
        key = tuple(_norm_key(k, r[key_map[k]]) for k in q["keys"])
        mf_index[key] = r
    checks = []
    ok = len(mf_rows) == len(expected_rows)
    for e in expected_rows:
        key = tuple(_norm_key(k, e[k]) for k in q["keys"])
        m = mf_index.get(key)
        for metric in q["metrics"]:
            exp_v = e[metric]
            mf_v = float(m[metric]) if m is not None and m.get(metric) not in (None, "") else None
            passed = mf_v is not None and exp_v is not None and math.isclose(mf_v, float(exp_v), rel_tol=REL_TOL, abs_tol=ABS_TOL)
            ok = ok and passed
            checks.append({"key": dict(zip(q["keys"], key)), "metric": metric, "metricflow": mf_v, "expected": exp_v, "pass": passed})
    return {"pass": ok, "checks": checks, "metricflow_rows": len(mf_rows), "expected_rows": len(expected_rows)}


def build_catalog() -> dict:
    manifest_path = DBT_DIR / "target" / "semantic_manifest.json"
    sm = json.loads(manifest_path.read_text())
    catalog = {"generated_from": "warehouse/target/semantic_manifest.json", "semantic_models": [], "metrics": []}
    for m in sm["semantic_models"]:
        catalog["semantic_models"].append(
            {
                "name": m["name"],
                "description": (m.get("description") or "").strip(),
                "table": m["node_relation"]["relation_name"],
                "entities": [{"name": e["name"], "type": e["type"], "column": e.get("expr") or e["name"]} for e in m["entities"]],
                "dimensions": [{"name": d["name"], "type": d["type"], "description": d.get("description")} for d in m["dimensions"]],
                "measures": [{"name": x["name"], "agg": x["agg"], "expr": x.get("expr"), "description": x.get("description")} for x in m.get("measures", [])],
            }
        )
    for x in sm["metrics"]:
        tp = x["type_params"]
        inputs = []
        if tp.get("measure"):
            inputs.append(tp["measure"]["name"])
        for k in ("numerator", "denominator"):
            if tp.get(k):
                inputs.append(f"{k}: {tp[k]['name']}")
        for mm in tp.get("metrics") or []:
            inputs.append(mm["name"])
        catalog["metrics"].append(
            {"name": x["name"], "label": x.get("label"), "type": x["type"], "description": x.get("description"), "expr": tp.get("expr"), "inputs": inputs}
        )
    return catalog


def main() -> int:
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    mf_results = {}
    for q in QUESTIONS:
        rows, sql = run_mf(q)
        mf_results[q["id"]] = (rows, sql)
        print(f"[mf] {q['id']} rows={len(rows)}", flush=True)

    con = connect(read_only=True)
    report = {"run_started_at": started, "tolerance": {"relative": REL_TOL, "absolute": ABS_TOL}, "questions": []}
    for q in QUESTIONS:
        cur = con.execute(q["expected_sql"])
        cols = [d[0] for d in cur.description]
        expected = [dict(zip(cols, r)) for r in cur.fetchall()]
        rows, sql = mf_results[q["id"]]
        result = compare(q, rows, expected)
        report["questions"].append(
            {
                "id": q["id"],
                "question": q["question"],
                "metricflow_query": " ".join(a if " " not in a else repr(a) for a in mf_args(q)[1:]),
                "metricflow_sql": sql,
                "independent_sql": " ".join(q["expected_sql"].split()),
                **result,
            }
        )
        print(f"[check] {q['id']} {'PASS' if result['pass'] else 'FAIL'} ({len(result['checks'])} values)")
    con.close()
    n_pass = sum(1 for x in report["questions"] if x["pass"])
    n_values = sum(len(x["checks"]) for x in report["questions"])
    report["summary"] = {
        "questions": len(QUESTIONS),
        "questions_passed": n_pass,
        "values_compared": n_values,
        "values_passed": sum(1 for x in report["questions"] for c in x["checks"] if c["pass"]),
    }
    write_json(RESULTS_DIR / "semantic_layer_tests.json", report)
    write_json(RESULTS_DIR / "semantic_catalog.json", build_catalog())
    write_markdown(report)
    print(f"semantic layer: {n_pass}/{len(QUESTIONS)} questions passed, {report['summary']['values_passed']}/{n_values} values matched")
    return 0 if n_pass == len(QUESTIONS) else 1


def _fmt(v) -> str:
    if v is None:
        return "n/a"
    v = float(v)
    if v.is_integer() and abs(v) < 1e6:
        return f"{int(v):,}"
    if abs(v) >= 1e6:
        return f"{v:,.0f}"
    if abs(v) >= 100:
        return f"{v:,.2f}"
    return f"{v:.6f}"


def write_markdown(report: dict) -> None:
    lines = [
        "# Semantic layer tests",
        "",
        f"Run started {report['run_started_at']}. Each business question is answered by MetricFlow from the governed metric",
        "definitions and, separately, by plain SQL over the raw text tables. Values must agree within a relative tolerance of 1e-9.",
        "",
        f"Result: {report['summary']['questions_passed']} of {report['summary']['questions']} questions passed; "
        f"{report['summary']['values_passed']} of {report['summary']['values_compared']} values matched.",
        "",
    ]
    for q in report["questions"]:
        lines += [f"## {q['id']}: {q['question']}", "", f"`mf {q['metricflow_query']}`", "", "| group | metric | MetricFlow | plain SQL | match |", "|---|---|---|---|---|"]
        for c in q["checks"]:
            key = ", ".join(f"{k}={v}" for k, v in c["key"].items()) or "all"
            lines.append(f"| {key} | {c['metric']} | {_fmt(c['metricflow'])} | {_fmt(c['expected'])} | {'yes' if c['pass'] else 'NO'} |")
        lines.append("")
    (RESULTS_DIR / "semantic_layer_tests.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
