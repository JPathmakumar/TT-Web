"""
app.py — Backend for trashtitans2026.ca

Fetches the City of Toronto "Waste Wizard" dataset (CKAN), extracts only the
items that belong in the Green Bin (organics/compost), caches the result in
memory, and serves it at a same-origin API endpoint your frontend can call
without hitting CORS issues.

Run:
    pip install flask requests
    python3 app.py
    # serves on http://localhost:5000

Endpoints:
    GET /api/compost-items         -> JSON list of compost-eligible items
    GET /api/compost-items?q=apple -> filtered by search term
    GET /healthz                   -> cache status, for debugging
"""

import time
import threading
import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")

BASE_URL = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
PACKAGE_ID = "waste-wizard-lookup-table"

# How long to keep the fetched/filtered data before refreshing from the
# source (the dataset itself only refreshes quarterly, so a long cache is fine).
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

_cache = {
    "items": [],
    "fetched_at": 0,
    "source_file": None,
    "error": None,
}
_cache_lock = threading.Lock()

# Terms that identify an item as belonging in the Green Bin (organics/compost).
# The Waste Wizard dataset labels each item's disposal stream as free text
# (e.g. "Green Bin", "Green Bin (Curbside)"), so we match on substrings.
GREEN_BIN_MARKERS = ["green bin", "organics", "compost"]


def _get_json_resource_url(package_id: str) -> str:
    """Look up the package, find its JSON resource, and return its download URL."""
    resp = requests.get(
        f"{BASE_URL}/api/3/action/package_show",
        params={"id": package_id},
        timeout=20,
    )
    resp.raise_for_status()
    package = resp.json()["result"]

    for resource in package["resources"]:
        if resource.get("format", "").upper() == "JSON":
            if resource.get("datastore_active"):
                # Not expected for this dataset, but handle it just in case.
                return None
            # Non-datastore resource: metadata (incl. download url) via resource_show
            meta_resp = requests.get(
                f"{BASE_URL}/api/3/action/resource_show",
                params={"id": resource["id"]},
                timeout=20,
            )
            meta_resp.raise_for_status()
            return meta_resp.json()["result"]["url"]

    raise RuntimeError("No JSON resource found in the waste-wizard-lookup-table package")


def _normalize_record(record: dict):
    """
    The raw records use varying key casing/naming across dataset refreshes.
    Pull out (name, bin/stream, instructions) defensively by scanning keys.
    Returns None if the record doesn't look like a usable item.
    """
    lower_map = {k.lower(): k for k in record.keys()}

    def pick(*candidates):
        for c in candidates:
            if c in lower_map:
                val = record[lower_map[c]]
                if val:
                    return str(val).strip()
        return ""

    name = pick("item", "title", "keyword", "keywords", "name", "material")
    bin_stream = pick("bin", "stream", "category", "disposal", "wastestream", "material_stream")
    instructions = pick("instructions", "description", "howtodispose", "notes", "details")

    if not name or not bin_stream:
        return None

    return {"item": name, "bin": bin_stream, "instructions": instructions}


def _refresh_cache():
    try:
        file_url = _get_json_resource_url(PACKAGE_ID)
        data_resp = requests.get(file_url, timeout=60)
        data_resp.raise_for_status()
        raw = data_resp.json()

        # The dataset has historically been a list of records; some refreshes
        # wrap it in a top-level key. Handle both shapes.
        records = raw if isinstance(raw, list) else raw.get("data") or raw.get("items") or []

        items = []
        for record in records:
            if not isinstance(record, dict):
                continue
            normalized = _normalize_record(record)
            if normalized and any(marker in normalized["bin"].lower() for marker in GREEN_BIN_MARKERS):
                items.append(normalized)

        # De-duplicate and sort alphabetically for a clean listing
        seen = set()
        deduped = []
        for it in sorted(items, key=lambda x: x["item"].lower()):
            key = it["item"].lower()
            if key not in seen:
                seen.add(key)
                deduped.append(it)

        with _cache_lock:
            _cache["items"] = deduped
            _cache["fetched_at"] = time.time()
            _cache["source_file"] = file_url
            _cache["error"] = None

    except Exception as exc:  # noqa: BLE001 — surface any failure into cache status
        with _cache_lock:
            _cache["error"] = str(exc)


def _ensure_fresh_cache():
    if time.time() - _cache["fetched_at"] > CACHE_TTL_SECONDS or not _cache["items"]:
        _refresh_cache()


@app.route("/api/compost-items")
def compost_items():
    _ensure_fresh_cache()

    if _cache["error"] and not _cache["items"]:
        return jsonify({"error": _cache["error"]}), 502

    q = request.args.get("q", "").strip().lower()
    items = _cache["items"]
    if q:
        items = [it for it in items if q in it["item"].lower()]

    return jsonify(
        {
            "count": len(items),
            "total_available": len(_cache["items"]),
            "fetched_at": _cache["fetched_at"],
            "items": items,
        }
    )


@app.route("/healthz")
def healthz():
    return jsonify(
        {
            "cached_items": len(_cache["items"]),
            "fetched_at": _cache["fetched_at"],
            "source_file": _cache["source_file"],
            "error": _cache["error"],
        }
    )


# Serve the frontend page (app.html) at the site root for local testing
@app.route("/")
def index():
    return send_from_directory(".", "app.html")


if __name__ == "__main__":
    _refresh_cache()  # warm the cache on startup
    app.run(host="0.0.0.0", port=5000, debug=True)
