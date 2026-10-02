CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS raw.api_snapshot (
    snapshot_hash text PRIMARY KEY,
    first_fetched_at timestamptz NOT NULL,
    payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS core.dim_field (
    field_id bigint PRIMARY KEY,
    field_name text NOT NULL,
    region text NOT NULL,
    current_operator text NOT NULL,
    current_status text NOT NULL
);
CREATE TABLE IF NOT EXISTS core.fact_production_monthly (
    field_id bigint REFERENCES core.dim_field(field_id),
    month date NOT NULL,
    oil_msm3 numeric, gas_bsm3 numeric, ngl_msm3 numeric,
    condensate_msm3 numeric, oe_msm3 numeric,
    PRIMARY KEY (field_id, month),
    CHECK (extract(day FROM month) = 1)
);
CREATE TABLE IF NOT EXISTS mart.pipeline_runs (
    run_id text PRIMARY KEY,
    snapshot_hash text REFERENCES raw.api_snapshot(snapshot_hash),
    loaded_at timestamptz NOT NULL DEFAULT now(),
    field_rows integer NOT NULL,
    fact_rows integer NOT NULL,
    first_month date NOT NULL,
    last_month date NOT NULL
);
