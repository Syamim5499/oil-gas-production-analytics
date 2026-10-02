import hashlib
import json

import pytest


def sign(snapshot):
    content = {key: snapshot[key] for key in ("fields", "production")}
    snapshot["sha256"] = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    return snapshot


@pytest.fixture
def sample_snapshot():
    """Explicit synthetic contract fixture; never used by the public dashboard."""
    field = {"fldNpdidField": 101, "fldName": "TEST FIELD", "fldMainArea": "NORTH SEA",
             "cmpLongName": "TEST OPERATOR", "fldCurrentActivitySatus": "Producing"}
    fact = {"prfPeriod": "month", "prfInformationCarrierKind": "FIELD",
            "prfNpdidInformationCarrier": 101, "prfYear": 2024, "prfMonth": 1,
            "prfPrdOilNetMillSm3": 1.0, "prfPrdGasNetBillSm3": 2.0,
            "prfPrdNGLNetMillSm3": None, "prfPrdCondensateNetMillSm3": 0.0,
            "prfPrdOeNetMillSm3": 3.0}
    return sign({"extracted_at": "2026-10-02T00:00:00+00:00", "fields": [field],
                 "production": [fact, {**fact, "prfYear": 2025, "prfPrdOeNetMillSm3": 2.0}]})
