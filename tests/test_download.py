"""Safety rules of the downloader: host allowlist, content checks and sha256 pins."""

import json
from pathlib import Path

import pytest

from aco_scorecard import download
from aco_scorecard.paths import CONFIG_DIR, ROOT, load_yaml

ALLOWED = ["data.cms.gov"]


@pytest.mark.parametrize(
    "url",
    [
        "http://data.cms.gov/file.csv",
        "https://evil.example.com/file.csv",
        "https://data.cms.gov.evil.example.com/file.csv",
        "ftp://data.cms.gov/file.csv",
    ],
)
def test_check_url_refuses_other_schemes_and_hosts(url):
    with pytest.raises(download.DownloadError):
        download.check_url(url, ALLOWED)


def test_check_url_accepts_https_on_allowed_host():
    download.check_url("https://data.cms.gov/sites/default/files/x.csv", ALLOWED)


def test_redirect_to_another_host_is_refused():
    handler = download._GuardedRedirect(ALLOWED)
    with pytest.raises(download.DownloadError):
        handler.redirect_request(None, None, 302, "Found", {}, "https://evil.example.com/x.csv")


@pytest.mark.parametrize(
    "content",
    [b"<html><body>not a csv</body></html>", b"%PDF-1.7 binary", b"a,b\x00,c\n1,2,3\n", b"onlyonecolumn\n1\n"],
)
def test_validate_csv_rejects_non_csv(tmp_path, content):
    path = tmp_path / "bad.csv"
    path.write_bytes(content)
    with pytest.raises(download.DownloadError):
        download.validate_csv(path)


def test_validate_csv_accepts_plain_csv(tmp_path):
    path = tmp_path / "ok.csv"
    path.write_text("ACO_ID,N_AB,QualScore\nA1001,10000,95.5\nA1002,\"12,000\",90\n")
    info = download.validate_csv(path)
    assert info["header_columns"] == 3
    assert info["data_lines"] == 2


def test_pin_check_first_verified_and_mismatch():
    pins, changes = {}, []
    assert download.check_pin("k", "aaa", pins, False, changes) == "pinned (first download)"
    assert download.check_pin("k", "aaa", pins, False, changes) == "verified"
    with pytest.raises(download.DownloadError):
        download.check_pin("k", "bbb", pins, False, changes)
    assert download.check_pin("k", "bbb", pins, True, changes) == "changed and accepted"
    assert changes == [{"key": "k", "old_sha256": "aaa", "new_sha256": "bbb"}]


def test_every_configured_source_is_https_on_data_cms_gov():
    cfg = load_yaml(CONFIG_DIR / "sources.yml")
    assert cfg["allowed_hosts"] == ["data.cms.gov"]
    for entry in cfg["files"] + cfg["dictionaries"]:
        download.check_url(entry["url"], cfg["allowed_hosts"])


def test_manifest_matches_pins_and_cms_checksums():
    manifest = json.loads((ROOT / "results" / "download_manifest.json").read_text())
    pins = json.loads((CONFIG_DIR / "pins.json").read_text())
    for row in manifest["files"] + manifest["dictionaries"]:
        assert pins[row["key"]] == row["sha256"], row["key"]
    for row in manifest["dictionaries"]:
        if row.get("cms_published_md5"):
            assert row["cms_md5_match"] is True, row["key"]
    assert manifest["totals"]["data_files"] == 23
