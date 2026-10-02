from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import get_current_context

from pipeline.extract import extract_snapshot
from pipeline.load import load_snapshot
from pipeline.export import export_dashboard


with DAG(
    "oil_gas_production_analytics",
    description="SODIR API → validated PostgreSQL production marts → BI export",
    schedule="0 6 * * 1",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "portfolio", "retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["oil-gas", "public-api", "postgresql", "bi"],
) as dag:
    @task
    def extract():
        context = get_current_context()
        # Shared volume is suitable for this single-host LocalExecutor example.
        stamp = context["logical_date"].strftime("%Y%m%dT%H%M%S")
        return extract_snapshot(f"/opt/project/data/{stamp}/snapshot.json")

    @task
    def validate_and_load(path):
        return load_snapshot(path, get_current_context()["run_id"])

    @task
    def publish_bi(_load_result):
        export_dashboard("/opt/project/docs/data/dashboard.json")

    publish_bi(validate_and_load(extract()))
