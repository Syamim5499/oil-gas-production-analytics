# Offshore Pulse — Oil & Gas Production Analytics

A working industry portfolio case study: official public API → Apache Airflow → PostgreSQL → interactive BI dashboard. It uses real monthly field production on the Norwegian continental shelf, published by the **Norwegian Offshore Directorate (SODIR)**. No API key, proprietary company data, or fabricated dashboard records are required.

**[Open the BI dashboard](https://Syamim5499.github.io/oil-gas-production-analytics/)** · [Source API metadata](https://factmaps.sodir.no/api/rest/services/DataService/Data/FeatureServer/7300) · [Power BI connection guide](dashboard/POWER_BI.md)

## Business problem

An upstream portfolio analyst needs to identify which fields drive production, how liquid and gas volumes change, and which fields warrant a performance review. Monthly reports have different units, current-operator labels, missing values, signed net adjustments, and source revisions. This project turns those reports into auditable analytics with explicit definitions.

| Study | Business question | Dashboard output |
| --- | --- | --- |
| Portfolio production | How is monthly reported production changing? | Net oil-equivalent trend; oil, gas and positive-producing field KPIs |
| Liquid product mix | What share of liquid volume is oil, NGL or condensate? | Composition chart using comparable million Sm³ units |
| Field concentration | Which fields dominate reported positive production? | Top 10 fields and top-three share |
| Performance screening | Which fields show a large YoY fall in daily output rate? | Review queue: ≤−20% YoY, baseline ≥0.01 million Sm³ o.e. |

Region, field, report month and trend-window filters affect all relevant visuals. Hover a chart point for its value. Download the selected month as CSV. The public dashboard ships with a **populated warehouse export**, so it can be viewed without installing Airflow.

## Architecture

```mermaid
flowchart TD
    A["SODIR public REST API"] --> B["Airflow: extract snapshot"]
    B --> C["Validate IDs, dates and measures"]
    C --> D["PostgreSQL: raw JSON + star schema"]
    D --> E["SQL marts + load audit"]
    E --> F["BI JSON/CSV export"]
    F --> G["Interactive dashboard / Power BI"]
```

| Object | Grain / role |
| --- | --- |
| `raw.api_snapshot` | One JSON snapshot per SHA-256 content hash; source evidence |
| `core.dim_field` | One official field ID; current region/operator/status |
| `core.fact_production_monthly` | One field ID and calendar month; five reported net volume measures |
| `mart.field_monthly` | Fact grain + metadata, daily oil-equivalent rate, exact-calendar YoY and negative-value flag |
| `mart.portfolio_monthly` | One month; volume totals and reporting/quality coverage |
| `mart.decline_screen` | Latest source month, fields meeting the review criteria |
| `mart.pipeline_runs` | One successful warehouse run with hash, row counts and date coverage |

## Run the complete stack

Requires Docker Engine and Compose v2, plus internet access to the SODIR API. The Airflow stack benefits from at least 4 GB of available memory. Use this disposable local demo on your own computer:

```bash
git clone https://github.com/Syamim5499/oil-gas-production-analytics.git
cd oil-gas-production-analytics
cp .env.example .env
mkdir -p data docs/data
# Linux/macOS: allow Airflow's container user to write these public-data folders.
chmod a+rwx data docs/data
docker compose up --build -d
docker compose ps
```

On Windows, copy `.env.example` to `.env` and create the folders in Explorer/PowerShell; the Unix `chmod` command is not required. `.env` contains local demo credentials and is excluded from Git. Use simple alphanumeric passwords if changing them because the example interpolates them into database connection URLs.

1. Open **[Airflow](http://localhost:8081)**. Sign in using `AIRFLOW_ADMIN_USER` and `AIRFLOW_ADMIN_PASSWORD` from `.env`.
2. Unpause **`oil_gas_production_analytics`** and click **Trigger DAG**.
3. Check that `extract`, `validate_and_load` and `publish_bi` all succeed.
4. Open **[the local BI dashboard](http://localhost:8502)** and refresh. Its source date and warehouse run are displayed.

The DAG runs Monday at 06:00 UTC / 14:00 Malaysia time to check for monthly source updates. `catchup=False` avoids redundant backfill, and `max_active_runs=1` prevents overlapping DAG runs. Task retries are spaced five minutes apart. Raw snapshots pass between tasks through a shared data volume; XCom carries only a file path and small load result. This is a single-host LocalExecutor design. Distributed workers would need shared object storage.

Warehouse connection: **localhost:5434**, database/user **warehouse**, password from `.env`. Airflow metadata lives in a separate database. Airflow, database and BI ports bind only to local loopback. `docker compose down` stops the stack; `docker compose down -v` additionally erases both database volumes.

The public GitHub Pages viewer is a committed snapshot. Running a local DAG refreshes your local export, **not the public GitHub repo automatically**. To update the public viewer, commit `docs/data/dashboard.json.gz` after a successful run. No token or password is stored in the DAG. `publish_bi` serves an atomic file replacement; the page reads its snapshot when loaded/refreshed.

## Run the pipeline without Airflow

With a PostgreSQL database you own and Python 3.11+:

```bash
python -m pip install -r requirements.txt
export WAREHOUSE_DSN='postgresql://warehouse:YOUR_PASSWORD@localhost:5434/warehouse'
python -m pipeline.extract --output data/snapshot.json
python -m pipeline.load --input data/snapshot.json --run-id manual-001
python -m pipeline.export --output docs/data/dashboard.json
python -m http.server 8502 --directory docs
```

The loader creates its schemas and tables. Use a **new run ID for a new extraction**. Retrying the same run ID with the same snapshot is a no-op; reusing it with different content fails. The export includes uncompressed JSON, gzip JSON and a full CSV. The browser uses gzip JSON with the modern `DecompressionStream` API (current Chrome, Edge, Firefox or Safari).

## Source contract and engineering decisions

- Layer **7100** provides field metadata. Layer **7300** provides historical production profiles. Filter: `prfPeriod = 'month' AND prfInformationCarrierKind = 'FIELD' AND prfYear >= 2020`. Annual rows and discovery rows are excluded to prevent double counting.
- Extract all matching object IDs, sort them, fetch batches of 500 through the documented ArcGIS **POST query**, and verify every requested ID was returned exactly once. Recheck the ID set at the end. This detects insert/delete changes during extraction, but the API has no frozen multi-request snapshot guarantee; in-place revisions during extraction remain possible.
- HTTP requests have timeouts and bounded retries for transient errors. Empty, duplicate, truncated or non-JSON responses fail before publication.
- A primary key on field ID validates lookup cardinality. Duplicate field-month facts and unmatched field IDs fail instead of multiplying or silently dropping records.
- Missing measures stay `NULL`. Reported **negative net values are preserved** and flagged; they may reflect reporting adjustments, so their cause is not inferred by this project. A product-mix chart is withheld when a selected component total is negative or missing.
- A full refresh of the 2020+ scope captures historical revisions and removals. Raw evidence, core replacement, mart definitions and audit row share one transaction. A PostgreSQL advisory lock serialises warehouse publishers; failed SQL leaves the previous publication intact.
- The export reads the marts and load audit in one repeatable-read transaction. It does not independently recalculate the warehouse's YoY measure. Browser filters recompute scoped totals from exported mart rows.

## Units and interpretation

Oil/NGL/condensate: **million standard cubic metres (million Sm³)**. Gas: **billion standard cubic metres (billion Sm³)**. Oil equivalent: the source's reported **million Sm³ o.e.** value; it is not a barrel figure and is not reconstructed from the components. Liquid composition excludes gas.

YoY daily-rate change compares the same field in the same calendar month of the preceding year, dividing each monthly volume by its own days in month. An absent or zero baseline yields `NULL`, not infinity. A ≤−20% change flags a review, not proven downtime, reservoir decline or a causal event. Top-three share uses positive field output as the denominator; portfolio totals retain signed values.

Current-operator metadata is applied to historical records as a current classification. The operator chart/query is not a historical ownership or equity-production calculation. Source coverage may vary by month; missing field-month observations are not zero. The dashboard reports missing and negative measures. It contains no prices, demand, inventory, emissions, reserves, revenues or forecasts.

## Tests and validation

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --test tests/analytics.test.mjs
python -m compileall -q pipeline dags
docker compose config -q
```

Without `TEST_DATABASE_DSN`, the PostgreSQL integration test is skipped. Set it only for a disposable empty test database. GitHub Actions runs that test against PostgreSQL 16 and also validates Compose configuration. Local verification used PostgreSQL-in-WASM (PGlite) with the PostgreSQL wire protocol because Docker was unavailable; the actual Python loader, SQL views, failure rollback and export executed against that engine. The Airflow Docker scheduler/webserver have not been run in the authoring workspace. See [validation evidence](dashboard/VALIDATION.md).

## Data attribution

Data source: **Norwegian Offshore Directorate**, [SODIR DataService](https://factmaps.sodir.no/api/rest/services/DataService/Data/FeatureServer), accessed 2 October 2026. Published under the [Norwegian Licence for Open Government Data (NLOD)](https://www.sodir.no/en/facts/data-and-analyses/open-data/). Source documentation: [field attributes](https://factpages.sodir.no/en/field/Attributes), [profile schema](https://factmaps.sodir.no/api/rest/services/DataService/Data/FeatureServer/7300), [ArcGIS query contract](https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/). This educational dashboard is an independent transformation and is not an official SODIR product. Source data can be revised.
