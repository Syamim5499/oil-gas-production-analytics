"""Runs against a disposable PostgreSQL database when TEST_DATABASE_DSN is set."""
import json
from contextlib import closing, contextmanager
import os
from pathlib import Path

import psycopg2
import pytest

from pipeline.export import export_dashboard
from pipeline.load import load_snapshot
from conftest import sign

DSN = os.environ.get("TEST_DATABASE_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="Requires disposable TEST_DATABASE_DSN")


@contextmanager
def db():
    with closing(psycopg2.connect(DSN)) as connection:
        with connection:
            yield connection


def test_load_idempotence_sql_nulls_and_atomic_rollback(sample_snapshot, tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(sample_snapshot))
    result = load_snapshot(path, "test-baseline", DSN)
    assert result["fact_rows"] == 2
    assert load_snapshot(path, "test-baseline", DSN)["status"] == "already_loaded"
    with db() as c:
        with c.cursor() as cur:
            cur.execute("SELECT ngl_msm3, yoy_daily_rate_pct FROM mart.field_monthly ORDER BY month DESC")
            missing, yoy = cur.fetchone()
            assert missing is None
            assert float(yoy) == pytest.approx(-100/3)
            cur.execute("SELECT count(*) FROM mart.pipeline_runs")
            assert cur.fetchone()[0] == 1
            cur.execute("""CREATE OR REPLACE FUNCTION core.reject_insert() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'test injected SQL failure'; END $$;
                CREATE TRIGGER reject_insert BEFORE INSERT ON core.fact_production_monthly
                FOR EACH ROW EXECUTE FUNCTION core.reject_insert();""")

    sample_snapshot["production"][0]["prfPrdOilNetMillSm3"] = 1.5
    path.write_text(json.dumps(sign(sample_snapshot)))
    with pytest.raises(psycopg2.Error, match="test injected SQL failure"):
        load_snapshot(path, "test-rollback", DSN)
    with db() as c:
        with c.cursor() as cur:
            cur.execute("SELECT count(*), min(oil_msm3) FROM core.fact_production_monthly")
            count, oil = cur.fetchone()
            assert count == 2 and float(oil) == 1.0
            cur.execute("SELECT count(*) FROM raw.api_snapshot")
            assert cur.fetchone()[0] == 1  # New raw snapshot rolled back too.
            cur.execute("DROP TRIGGER reject_insert ON core.fact_production_monthly")
            cur.execute("DROP FUNCTION core.reject_insert()")
    with pytest.raises(ValueError, match="different snapshot"):
        load_snapshot(path, "test-baseline", DSN)
    # A negative prior-year net baseline does not support a growth percentage.
    sample_snapshot["production"][0]["prfPrdOeNetMillSm3"] = -3.0
    path.write_text(json.dumps(sign(sample_snapshot)))
    load_snapshot(path, "test-signed-baseline", DSN)
    with db() as c:
        with c.cursor() as cur:
            cur.execute("SELECT yoy_daily_rate_pct FROM mart.field_monthly ORDER BY month DESC LIMIT 1")
            assert cur.fetchone()[0] is None
    output = tmp_path / "dashboard.json"
    export_dashboard(str(output), DSN)
    exported = json.loads(output.read_text())
    assert len(exported["rows"]) == 2
    assert exported["rows"][0]["ngl_msm3"] is None
    assert output.with_name("field_monthly.csv").exists()
    assert output.with_suffix(".json.gz").exists()
