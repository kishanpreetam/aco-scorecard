"""The saved results are complete, consistent with each other and self-contained."""

import json
import re

from aco_scorecard.paths import ROOT


def test_semantic_layer_answers_match_plain_sql(results):
    report = results("semantic_layer_tests.json")
    assert report["summary"]["questions"] >= 10
    assert report["summary"]["questions_passed"] == report["summary"]["questions"]
    assert report["summary"]["values_passed"] == report["summary"]["values_compared"]


def test_monitoring_checks_pass(results):
    report = results("pipeline_monitoring.json")
    assert report["all_checks_passed"], [c for c in report["checks"] if not c["pass"]]


def test_metrics_file_agrees_with_semantic_layer(results):
    metrics = results("metrics.json")
    sem = results("semantic_layer_tests.json")
    q2 = next(q for q in sem["questions"] if q["id"] == "Q02")
    earned = next(c for c in q2["checks"] if c["metric"] == "earned_shared_savings")["expected"]
    assert metrics["latest_performance_year"] == 2024
    assert abs(metrics["latest_year"]["earned_shared_savings"] - earned) < 1


def test_dashboard_is_self_contained():
    html = (ROOT / "results" / "dashboard.html").read_text()
    assert len(html.encode()) < 16 * 1024 * 1024
    assert re.search(r"<script[^>]+src=", html) is None, "dashboard must not load external scripts"
    assert 'id="dashboard-data"' in html
    payload = html.split('<script id="dashboard-data" type="application/json">', 1)[1].split("</script>", 1)[0]
    data = json.loads(payload)
    assert len(data["program_by_year"]) == 12
