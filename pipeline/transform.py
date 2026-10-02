"""Validate source grain, identities, nullable measures, and join cardinality."""

from datetime import date
from decimal import Decimal, InvalidOperation

MEASURES = {
    "oil_msm3": "prfPrdOilNetMillSm3",
    "gas_bsm3": "prfPrdGasNetBillSm3",
    "ngl_msm3": "prfPrdNGLNetMillSm3",
    "condensate_msm3": "prfPrdCondensateNetMillSm3",
    "oe_msm3": "prfPrdOeNetMillSm3",
}


def integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Invalid {label}: {value}")
    return value


def measure(value, label):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Invalid {label}")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {label}") from exc
    if not number.is_finite():
        raise ValueError(f"Invalid {label}: expected finite reported volume")
    return number


def validate_snapshot(snapshot):
    fields, facts = [], []
    dimensions = {}
    seen = set()
    for item in snapshot.get("fields", []):
        field_id = integer(item.get("fldNpdidField"), "field ID")
        if field_id in dimensions:
            raise ValueError("Duplicate field dimension ID; join would multiply facts")
        name = item.get("fldName")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Missing field name")
        row = (field_id, name, item.get("fldMainArea") or "Unknown",
               item.get("cmpLongName") or "Unknown", item.get("fldCurrentActivitySatus") or "Unknown")
        dimensions[field_id] = row
        fields.append(row)

    for item in snapshot.get("production", []):
        if item.get("prfPeriod") != "month" or item.get("prfInformationCarrierKind") != "FIELD":
            raise ValueError("Non-monthly or non-field record in production snapshot")
        field_id = integer(item.get("prfNpdidInformationCarrier"), "production field ID")
        if field_id not in dimensions:
            raise ValueError(f"Unmatched production field ID {field_id}")
        year, month = item.get("prfYear"), item.get("prfMonth")
        if isinstance(year, bool) or isinstance(month, bool):
            raise ValueError("Invalid month/year")
        try:
            period = date(year, month, 1)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid month/year") from exc
        if year < 2020 or period > date.today().replace(day=1):
            raise ValueError("Period outside supported scope")
        key = (field_id, period)
        if key in seen:
            raise ValueError("Duplicate field/month fact")
        seen.add(key)
        values = [measure(item.get(source), target) for target, source in MEASURES.items()]
        facts.append((field_id, period, *values))
    if not fields or not facts:
        raise ValueError("Empty dimension or fact snapshot")
    return sorted(fields), sorted(facts, key=lambda row: (row[1], row[0]))
