"""Public writing rules: no em dashes, double dashes or arrows in prose, and no AI attribution."""

import re

import pytest

from aco_scorecard.paths import ROOT

PUBLIC = ["README.md", "docs/metric_definitions.md", "docs/schema_mapping.md", "docs/data_dictionary.md",
          "results/resume_lines.md", "results/semantic_layer_tests.md", "results/pipeline_monitoring.md",
          "aco_scorecard/dashboard_template.html"]


def prose(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    return text


@pytest.mark.parametrize("name", PUBLIC)
def test_no_em_dashes_double_dashes_or_arrows(name):
    path = ROOT / name
    if not path.exists():
        pytest.skip(f"{name} not written yet")
    text = prose(path.read_text())
    assert "—" not in text, "em dash"
    assert "→" not in text, "arrow"
    assert re.search(r"\s--\s", text) is None, "double dash"
    assert re.search(r"\s->\s", text) is None, "ascii arrow"


@pytest.mark.parametrize("name", PUBLIC)
def test_no_ai_attribution(name):
    path = ROOT / name
    if not path.exists():
        pytest.skip(f"{name} not written yet")
    lowered = path.read_text().lower()
    for phrase in ("claude", "generated with", "co-authored-by", "chatgpt", "openai"):
        assert phrase not in lowered, phrase
