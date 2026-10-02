"""Export committed SQL mart rows for the public BI viewer and Power BI."""

import argparse
from contextlib import closing
import csv
import gzip
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


def serialise(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


def export_dashboard(output="docs/data/dashboard.json", dsn=None):
    destination = Path(output)
    with closing(psycopg2.connect(dsn or os.environ["WAREHOUSE_DSN"])) as conn:
        with conn:
            conn.set_session(isolation_level="REPEATABLE READ", readonly=True)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM mart.pipeline_runs ORDER BY loaded_at DESC LIMIT 1")
                audit = cur.fetchone()
                if not audit:
                    raise ValueError("No successful warehouse load")
                cur.execute("SELECT * FROM mart.field_monthly ORDER BY month, field_id")
                rows = cur.fetchall()
                cur.execute("SELECT * FROM mart.portfolio_monthly ORDER BY month")
                portfolio = cur.fetchall()
    result = {"source": "Norwegian Offshore Directorate · SODIR DataService",
              "source_url": "https://factmaps.sodir.no/api/rest/services/DataService/Data/FeatureServer/7300",
              "exported_at": datetime.now(timezone.utc).isoformat(), "run": dict(audit),
              "portfolio": portfolio, "rows": rows}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(".tmp")
    temp.write_text(json.dumps(result, default=serialise, ensure_ascii=False), encoding="utf-8")
    temp.replace(destination)
    compressed = destination.with_suffix(destination.suffix + ".gz")
    compressed_temp = compressed.with_suffix(".tmp")
    compressed_temp.write_bytes(gzip.compress(destination.read_bytes(), mtime=0))
    compressed_temp.replace(compressed)
    csv_path = destination.with_name("field_monthly.csv")
    with csv_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} SQL mart rows to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/data/dashboard.json")
    args = parser.parse_args()
    export_dashboard(args.output)
