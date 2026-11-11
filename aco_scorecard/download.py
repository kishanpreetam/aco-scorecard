"""Download the pinned CMS Shared Savings Program files listed in config/sources.yml.

What this script records for every file (in data/raw/manifest.json and the committed copy
results/download_manifest.json): source URL, catalog title, bytes, sha256, md5, the HTTP
Last-Modified header and the data dictionary that documents it. Data dictionaries are
downloaded too, and their md5 is checked against the checksum CMS publishes for them.

Safety rules (downloaded files are untrusted input):
  * HTTPS only, and every request and redirect must stay on an allowed host (data.cms.gov).
  * Hard size cap per file; files stream to a temp name and are renamed only when complete.
  * Content is checked for the expected type (CSV text, PDF magic bytes, JSON) and is never
    executed or unpickled.
  * sha256 pins live in config/pins.json. A file whose hash changes stops the run until a
    person reviews it and reruns with --accept-changes.

Usage:
  python -m aco_scorecard.download              # download missing files, verify pins
  python -m aco_scorecard.download --discover   # re-read data.json and report new or revised files
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .paths import CONFIG_DIR, RAW_DIR, RESULTS_DIR, ROOT, load_yaml, write_json

SOURCES_PATH = CONFIG_DIR / "sources.yml"
PINS_PATH = CONFIG_DIR / "pins.json"
MANIFEST_PATH = RAW_DIR / "manifest.json"
RESULTS_MANIFEST_PATH = RESULTS_DIR / "download_manifest.json"
USER_AGENT = "aco-scorecard/1.0 (public data analytics; github.com/kishanpreetam/aco-scorecard)"
CHUNK = 1 << 16


class DownloadError(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def check_url(url: str, allowed_hosts: list[str]) -> None:
    parts = urllib.parse.urlparse(url)
    if parts.scheme != "https":
        raise DownloadError(f"refusing non-HTTPS URL: {url}")
    if parts.hostname not in allowed_hosts:
        raise DownloadError(f"refusing host {parts.hostname!r}; allowed: {allowed_hosts}")


class _GuardedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: list[str]):
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        check_url(newurl, self.allowed_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener(allowed_hosts: list[str]):
    return urllib.request.build_opener(_GuardedRedirect(allowed_hosts))


def fetch_to_file(url: str, dest: Path, allowed_hosts: list[str], max_bytes: int, retries: int = 3) -> dict:
    """Stream url to dest, enforcing host and size rules. Returns size, hashes and headers."""
    check_url(url, allowed_hosts)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with _opener(allowed_hosts).open(req, timeout=120) as resp:
                check_url(resp.geturl(), allowed_hosts)
                sha256, md5, size = hashlib.sha256(), hashlib.md5(), 0
                with open(tmp, "wb") as out:
                    while True:
                        chunk = resp.read(CHUNK)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > max_bytes:
                            raise DownloadError(f"{url} exceeds the {max_bytes} byte cap")
                        sha256.update(chunk)
                        md5.update(chunk)
                        out.write(chunk)
                headers = {
                    "content_type": resp.headers.get("Content-Type"),
                    "last_modified": resp.headers.get("Last-Modified"),
                    "etag": resp.headers.get("ETag"),
                }
            tmp.replace(dest)
            return {"bytes": size, "sha256": sha256.hexdigest(), "md5": md5.hexdigest(), **headers}
        except DownloadError:
            tmp.unlink(missing_ok=True)
            raise
        except Exception as exc:  # network hiccups: retry with backoff
            last_err = exc
            tmp.unlink(missing_ok=True)
            time.sleep(2 * attempt)
    raise DownloadError(f"failed to download {url}: {last_err}")


def fetch_json(url: str, allowed_hosts: list[str], max_bytes: int = 50 * 1024 * 1024, retries: int = 4):
    check_url(url, allowed_hosts)
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.api+json, application/json"})
            with _opener(allowed_hosts).open(req, timeout=60) as resp:
                check_url(resp.geturl(), allowed_hosts)
                body = resp.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise DownloadError(f"{url} exceeds the {max_bytes} byte cap")
            return json.loads(body.decode("utf-8"))
        except DownloadError:
            raise
        except Exception as exc:  # transient timeouts happen on this endpoint
            last_err = exc
            time.sleep(3 * attempt)
    raise DownloadError(f"failed to fetch {url}: {last_err}")


def hash_file(path: Path) -> tuple[str, str, int]:
    sha256, md5, size = hashlib.sha256(), hashlib.md5(), 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            sha256.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return sha256.hexdigest(), md5.hexdigest(), size


def validate_csv(path: Path) -> dict:
    """Cheap structural checks on a downloaded CSV. Raises on anything that is not plain CSV text."""
    with open(path, "rb") as fh:
        head = fh.read(1 << 20)
    if b"\x00" in head:
        raise DownloadError(f"{path.name}: NUL bytes found, not a text CSV")
    if head.lstrip().startswith((b"<", b"{", b"%PDF")):
        raise DownloadError(f"{path.name}: looks like HTML, JSON or PDF, not CSV")
    try:
        text = head.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = head.decode("latin-1")
        encoding = "latin-1"
    header = text.splitlines()[0]
    n_cols = header.count(",") + 1
    if n_cols < 3:
        raise DownloadError(f"{path.name}: header has only {n_cols} columns")
    with open(path, "rb") as fh:
        n_lines = sum(1 for _ in fh)
    return {"encoding_guess": encoding, "header_columns": n_cols, "data_lines": n_lines - 1}


def validate_pdf(path: Path) -> None:
    with open(path, "rb") as fh:
        if fh.read(5) != b"%PDF-":
            raise DownloadError(f"{path.name}: missing PDF magic bytes")


def _strip_html(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def fetch_dictionary_terms(node_id: str, allowed_hosts: list[str]) -> dict:
    """Read a data.cms.gov data dictionary page through its JSON:API and normalize the terms."""
    url = (
        f"https://data.cms.gov/jsonapi/node/data_dictionary_page/{node_id}"
        "?include=field_dictionary_terms"
    )
    doc = fetch_json(url, allowed_hosts)
    node = doc["data"]
    order = [ref["id"] for ref in node["relationships"]["field_dictionary_terms"]["data"]]
    by_id = {x["id"]: x for x in doc.get("included", []) if x["type"] == "paragraph--dictionary_term"}
    terms = []
    for tid in order:
        attrs = by_id[tid]["attributes"]
        definition = (attrs.get("field_dictionary_term_definition") or {}).get("value")
        footnote = attrs.get("field_dictionary_term_footnote")
        if isinstance(footnote, dict):
            footnote = footnote.get("value")
        terms.append(
            {
                "short_name": attrs.get("field_dictionary_term_short_name"),
                "full_name": attrs.get("field_dictionary_term_full_name"),
                "definition": _strip_html(definition),
                "footnote": _strip_html(footnote),
            }
        )
    attrs = node["attributes"]
    return {
        "source_url": url,
        "title": attrs.get("title"),
        "node_id": node_id,
        "revision_id": attrs.get("drupal_internal__vid"),
        "changed": attrs.get("changed"),
        "last_updated_date": attrs.get("field_last_updated_date"),
        "n_terms": len(terms),
        "terms": terms,
    }


def load_pins() -> dict:
    if PINS_PATH.exists():
        return json.loads(PINS_PATH.read_text(encoding="utf-8"))
    return {}


def save_pins(pins: dict) -> None:
    write_json(PINS_PATH, dict(sorted(pins.items())))


def _filename(url: str) -> str:
    return urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name).replace(" ", "_")


def check_pin(key: str, sha: str, pins: dict, accept_changes: bool, changes: list) -> str:
    pinned = pins.get(key)
    if pinned is None:
        pins[key] = sha
        return "pinned (first download)"
    if pinned == sha:
        return "verified"
    if accept_changes:
        changes.append({"key": key, "old_sha256": pinned, "new_sha256": sha})
        pins[key] = sha
        return "changed and accepted"
    raise DownloadError(
        f"{key}: sha256 {sha} does not match pin {pinned}. CMS may have revised the file. "
        "Review it, then rerun with --accept-changes."
    )


def download_all(force: bool = False, accept_changes: bool = False, only: list[str] | None = None) -> dict:
    cfg = load_yaml(SOURCES_PATH)
    allowed = cfg["allowed_hosts"]
    cap = int(cfg["max_bytes_per_file"])
    pins = load_pins()
    changes: list = []
    started = now_utc()
    file_rows, dict_rows = [], []

    for d in cfg["dictionaries"]:
        if only and d["key"] not in only:
            continue
        dest = RAW_DIR / "dictionaries" / _filename(d["url"])
        if dest.exists() and not force and pins.get(d["key"]):
            sha, md5, size = hash_file(dest)
            meta = {"bytes": size, "sha256": sha, "md5": md5, "content_type": None, "last_modified": None, "etag": None, "reused_local_copy": True}
        else:
            meta = fetch_to_file(d["url"], dest, allowed, cap)
        validate_pdf(dest)
        status = check_pin(d["key"], meta["sha256"], pins, accept_changes, changes)
        if d.get("cms_md5") and meta["md5"] != d["cms_md5"]:
            raise DownloadError(f"{d['key']}: md5 {meta['md5']} differs from the CMS published md5 {d['cms_md5']}")
        row = {
            "key": d["key"],
            "title": d["title"],
            "covers_performance_years": d.get("covers"),
            "url": d["url"],
            "path": str(dest.relative_to(ROOT)),
            **meta,
            "cms_published_md5": d.get("cms_md5"),
            "cms_md5_match": (meta["md5"] == d.get("cms_md5")) if d.get("cms_md5") else None,
            "cms_changed": d.get("cms_changed"),
            "pin_status": status,
        }
        if d.get("jsonapi_node"):
            tdest = RAW_DIR / "dictionaries" / f"{d['key']}_terms.json"
            if tdest.exists() and not force:
                terms = json.loads(tdest.read_text(encoding="utf-8"))
            else:
                terms = fetch_dictionary_terms(d["jsonapi_node"], allowed)
                write_json(tdest, terms)
            tsha, _, tsize = hash_file(tdest)
            row["jsonapi_terms"] = {
                "path": str(tdest.relative_to(ROOT)),
                "source_url": terms["source_url"],
                "revision_id": terms["revision_id"],
                "changed": terms["changed"],
                "n_terms": terms["n_terms"],
                "bytes": tsize,
                "sha256": tsha,
            }
        dict_rows.append(row)
        print(f"[dictionary] {d['key']:<22} {row['bytes']:>10,} bytes  {status}", flush=True)

    for f in cfg["files"]:
        if only and f["key"] not in only:
            continue
        dest = RAW_DIR / f["series"] / f"{f['key']}__{_filename(f['url'])}"
        if dest.exists() and not force and pins.get(f["key"]):
            sha, md5, size = hash_file(dest)
            meta = {"bytes": size, "sha256": sha, "md5": md5, "content_type": None, "last_modified": None, "etag": None, "reused_local_copy": True}
        else:
            meta = fetch_to_file(f["url"], dest, allowed, cap)
        shape = validate_csv(dest)
        status = check_pin(f["key"], meta["sha256"], pins, accept_changes, changes)
        file_rows.append(
            {
                "key": f["key"],
                "series": cfg["series"][f["series"]],
                "performance_year": f["performance_year"],
                "period": f["period"],
                "catalog_title": f["catalog_title"],
                "dictionary": f["dictionary"],
                "url": f["url"],
                "path": str(dest.relative_to(ROOT)),
                **meta,
                **shape,
                "pin_status": status,
            }
        )
        print(f"[file] {f['key']:<16} {meta['bytes']:>12,} bytes  lines={shape["data_lines"]:<7} {status}", flush=True)

    save_pins(pins)
    previous = {}
    if MANIFEST_PATH.exists():
        old_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        previous = {r["key"]: r for r in old_manifest.get("files", []) + old_manifest.get("dictionaries", [])}
    for row in file_rows + dict_rows:
        prev = previous.get(row["key"], {})
        if row.get("reused_local_copy"):
            # keep the HTTP metadata captured when the file was actually downloaded
            for k in ("content_type", "last_modified", "etag", "downloaded_at"):
                if prev.get(k):
                    row[k] = prev[k]
        else:
            row["downloaded_at"] = now_utc()
        row.pop("reused_local_copy", None)

    manifest = {
        "generated_at": now_utc(),
        "run_started_at": started,
        "catalog_url": cfg["catalog_url"],
        "allowed_hosts": allowed,
        "files": file_rows,
        "dictionaries": dict_rows,
        "accepted_changes": changes,
        "totals": {
            "data_files": len(file_rows),
            "dictionary_files": len(dict_rows),
            "data_bytes": sum(r["bytes"] for r in file_rows),
            "dictionary_bytes": sum(r["bytes"] for r in dict_rows),
            "all_bytes": sum(r["bytes"] for r in file_rows + dict_rows),
        },
    }
    if not only:
        write_json(MANIFEST_PATH, manifest)
        write_json(RESULTS_MANIFEST_PATH, manifest)
    t = manifest["totals"]
    print(f"done: {t['data_files']} data files ({t['data_bytes']:,} bytes), {t['dictionary_files']} dictionaries ({t['dictionary_bytes']:,} bytes)")
    return manifest


def discover() -> dict:
    """Re-read the data.cms.gov catalog and compare it with the pinned file list."""
    cfg = load_yaml(SOURCES_PATH)
    allowed = cfg["allowed_hosts"]
    dest = RAW_DIR / "catalog" / "data.json"
    meta = fetch_to_file(cfg["catalog_url"], dest, allowed, int(cfg["max_bytes_per_file"]))
    catalog = json.loads(dest.read_text(encoding="utf-8"))
    pinned_urls = {f["url"]: f["key"] for f in cfg["files"]}
    found = []
    for series_key, series_title in cfg["series"].items():
        for ds in catalog.get("dataset", []):
            title = ds.get("title", "")
            if not title.startswith(series_title + " :"):
                continue
            for dist in ds.get("distribution", []):
                url = dist.get("downloadURL")
                if not url:
                    continue
                found.append(
                    {
                        "series": series_key,
                        "catalog_title": title,
                        "temporal": ds.get("temporal"),
                        "modified": dist.get("modified") or ds.get("modified"),
                        "url": url,
                        "dictionary_title": (ds.get("describedBy") or {}).get("title"),
                        "dictionary_url": (ds.get("describedBy") or {}).get("downloadURL"),
                        "pinned_as": pinned_urls.get(url),
                    }
                )
    found_urls = {r["url"] for r in found}
    report = {
        "checked_at": now_utc(),
        "catalog": {"url": cfg["catalog_url"], "bytes": meta["bytes"], "sha256": meta["sha256"], "last_modified": meta["last_modified"]},
        "distributions_found": len(found),
        "new_or_revised_not_pinned": [r for r in found if r["pinned_as"] is None],
        "pinned_missing_from_catalog": [k for u, k in pinned_urls.items() if u not in found_urls],
        "distributions": found,
    }
    write_json(RESULTS_DIR / "catalog_discovery.json", report)
    print(f"catalog: {len(found)} CSV distributions in tracked series")
    for r in report["new_or_revised_not_pinned"]:
        print(f"  NOT PINNED: {r['catalog_title']}  {r['url']}")
    for k in report["pinned_missing_from_catalog"]:
        print(f"  PINNED BUT NOT IN CATALOG: {k}")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--discover", action="store_true", help="re-read data.json and report new or revised files")
    ap.add_argument("--force", action="store_true", help="download again even when a verified local copy exists")
    ap.add_argument("--accept-changes", action="store_true", help="accept files whose sha256 changed since pinning")
    ap.add_argument("--only", nargs="*", help="limit to these file keys (manifest is not rewritten)")
    args = ap.parse_args(argv)
    try:
        if args.discover:
            discover()
        else:
            download_all(force=args.force, accept_changes=args.accept_changes, only=args.only)
    except DownloadError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
