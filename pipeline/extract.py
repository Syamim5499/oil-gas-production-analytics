"""Fetch official ArcGIS features with ID batching and completeness checks."""

import argparse
import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://factmaps.sodir.no/api/rest/services/DataService/Data/FeatureServer"
START_YEAR = 2020
PRODUCTION_WHERE = "prfPeriod = 'month' AND prfInformationCarrierKind = 'FIELD' AND prfYear >= 2020"


def request_json(layer, params):
    encoded = urllib.parse.urlencode({"f": "json", **params})
    # Official ArcGIS query supports POST; avoid a long objectIds query URL.
    url = f"{BASE}/{layer}/query" + ("" if "objectIds" in params else "?" + encoded)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url,
                data=encoded.encode() if "objectIds" in params else None,
                headers={"User-Agent": "oil-gas-portfolio/1.0",
                         "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=60) as response:
                try:
                    payload = json.load(response)
                except json.JSONDecodeError as exc:
                    raise ValueError("API returned a non-JSON response") from exc
            if "error" in payload:
                raise ValueError(f"ArcGIS API error: {payload['error']}")
            return payload
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
        time.sleep(min(2 ** attempt, 8))
    raise RuntimeError("API retries exhausted")


def fetch_layer(layer, where, requester=request_json, batch_size=500):
    """Use IDs to avoid unstable offset pagination; reject missing/extra rows."""
    def get_ids():
        response = requester(layer, {"where": where, "returnIdsOnly": "true"})
        ids = response.get("objectIds")
        if not isinstance(ids, list) or not ids or len(ids) >= 1_000_000:
            raise ValueError("Empty, invalid, or potentially truncated object ID response")
        if any(isinstance(item, bool) or not isinstance(item, int) for item in ids):
            raise ValueError("Invalid object ID")
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate object IDs")
        return sorted(ids)

    ids = get_ids()
    rows = []
    for offset in range(0, len(ids), batch_size):
        batch = ids[offset:offset + batch_size]
        page = requester(layer, {"objectIds": ",".join(map(str, batch)),
                                 "outFields": "*", "returnGeometry": "false"})
        if page.get("exceededTransferLimit"):
            raise ValueError("API page exceeded transfer limit; reduce batch size")
        features = page.get("features")
        if not isinstance(features, list):
            raise ValueError("Missing API features array")
        attrs = [feature["attributes"] for feature in features]
        returned = [row.get("OBJECTID") for row in attrs]
        if len(returned) != len(batch) or set(returned) != set(batch):
            raise ValueError("API page is incomplete or contains duplicate/unrequested records")
        rows.extend(attrs)
        logging.info("Layer %s: %s/%s rows", layer, len(rows), len(ids))
    if ids != get_ids():
        raise ValueError("Source ID set changed during extraction; retry the complete run")
    return rows


def extract_snapshot(path):
    fields = fetch_layer(7100, "1=1")
    production = fetch_layer(7300, PRODUCTION_WHERE)
    content = {"fields": fields, "production": production}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    snapshot = {"source": BASE, "extracted_at": datetime.now(timezone.utc).isoformat(),
                "start_year": START_YEAR, "sha256": digest, **content}
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    temporary.replace(destination)
    print(f"Extracted {len(fields)} fields and {len(production)} monthly records to {path}")
    return str(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/snapshot.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    extract_snapshot(args.output)
