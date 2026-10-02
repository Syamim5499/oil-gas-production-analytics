"""Publish a validated snapshot atomically; retries with the same run ID are safe."""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

from pipeline.transform import validate_snapshot

ROOT = Path(__file__).resolve().parents[1]


def load_snapshot(path, run_id, dsn=None):
    snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    fields, facts = validate_snapshot(snapshot)
    content = {key: snapshot[key] for key in ("fields", "production")}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    if digest != snapshot.get("sha256"):
        raise ValueError("Snapshot checksum mismatch")
    with closing(psycopg2.connect(dsn or os.environ["WAREHOUSE_DSN"])) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute((ROOT / "sql/schema.sql").read_text())
                cursor.execute("SELECT pg_advisory_xact_lock(74002026)")
                cursor.execute("SELECT snapshot_hash FROM mart.pipeline_runs WHERE run_id = %s", (run_id,))
                existing = cursor.fetchone()
                if existing:
                    if existing[0] != digest:
                        raise ValueError("Run ID already used for a different snapshot")
                    return {"run_id": run_id, "status": "already_loaded", "fact_rows": len(facts)}
                cursor.execute("""INSERT INTO raw.api_snapshot VALUES (%s, %s, %s)
                                  ON CONFLICT (snapshot_hash) DO NOTHING""",
                               (digest, snapshot["extracted_at"], Json(snapshot)))
                cursor.execute("TRUNCATE core.fact_production_monthly, core.dim_field")
                execute_values(cursor, "INSERT INTO core.dim_field VALUES %s", fields)
                execute_values(cursor, "INSERT INTO core.fact_production_monthly VALUES %s", facts)
                cursor.execute((ROOT / "sql/marts.sql").read_text())
                cursor.execute("SELECT count(*) FROM mart.field_monthly")
                if cursor.fetchone()[0] != len(facts):
                    raise ValueError("Analytics join changed the fact grain")
                cursor.execute("""INSERT INTO mart.pipeline_runs
                    (run_id, snapshot_hash, field_rows, fact_rows, first_month, last_month)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                               (run_id, digest, len(fields), len(facts), facts[0][1], facts[-1][1]))
    return {"run_id": run_id, "status": "loaded", "fact_rows": len(facts)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/snapshot.json")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(load_snapshot(args.input, args.run_id))
