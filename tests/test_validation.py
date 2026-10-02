from copy import deepcopy
from decimal import Decimal

import pytest

from pipeline.extract import fetch_layer
from pipeline.transform import validate_snapshot


def test_nullable_measures_and_validated_grain(sample_snapshot):
    dimensions, facts = validate_snapshot(sample_snapshot)
    assert len(dimensions) == 1 and len(facts) == 2
    assert facts[0][4] is None  # NGL stays missing.
    assert facts[0][2] == Decimal("1.0")


@pytest.mark.parametrize("change", [
    lambda s: s["fields"].append(deepcopy(s["fields"][0])),
    lambda s: s["production"].append(deepcopy(s["production"][0])),
    lambda s: s["production"][0].update(prfNpdidInformationCarrier=999),
    lambda s: s["production"][0].update(prfMonth=13),
    lambda s: s["production"][0].update(prfPrdOilNetMillSm3=True),
    lambda s: s["production"][0].update(prfPrdOilNetMillSm3="NaN"),
    lambda s: s["production"][0].update(prfPeriod="year"),
    lambda s: s["production"].clear(),
])
def test_rejects_bad_contracts(sample_snapshot, change):
    change(sample_snapshot)
    with pytest.raises(ValueError):
        validate_snapshot(sample_snapshot)


def test_id_batching_fetches_each_record_once():
    def api(layer, params):
        if "returnIdsOnly" in params:
            return {"objectIds": [3, 1, 2]}
        return {"features": [{"attributes": {"OBJECTID": int(i)}}
                             for i in params["objectIds"].split(",")]}
    assert [row["OBJECTID"] for row in fetch_layer(7300, "1=1", api, 2)] == [1, 2, 3]


def test_reported_negative_net_volumes_are_preserved(sample_snapshot):
    sample_snapshot["production"][0]["prfPrdOilNetMillSm3"] = -0.006328
    assert validate_snapshot(sample_snapshot)[1][0][2] == Decimal("-0.006328")


def test_missing_api_page_fails():
    def api(layer, params):
        return {"objectIds": [1, 2]} if "returnIdsOnly" in params else {"features": []}
    with pytest.raises(ValueError, match="incomplete"):
        fetch_layer(7300, "1=1", api)


def test_source_change_during_extraction_fails():
    calls = 0
    def api(layer, params):
        nonlocal calls
        if "returnIdsOnly" in params:
            calls += 1
            return {"objectIds": [1] if calls == 1 else [1, 2]}
        return {"features": [{"attributes": {"OBJECTID": 1}}]}
    with pytest.raises(ValueError, match="changed"):
        fetch_layer(7300, "1=1", api)
