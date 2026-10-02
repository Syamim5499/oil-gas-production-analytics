# Validation evidence — 2 October 2026

## Data and warehouse

- Live requests to the official SODIR API succeeded. Matching IDs were fetched in batches and verified before and after extraction.
- Extracted **142 field dimensions** and **7,581 field-month production records**, covering **January 2020–July 2026**.
- All production field IDs matched a unique dimension; the SQL join retained exactly 7,581 fact rows.
- The actual Python loader and SQL marts ran through psycopg2 against **PGlite's PostgreSQL engine and wire protocol**. Docker/native PostgreSQL were unavailable in the authoring workspace.
- The included public dashboard data was exported from the committed SQL marts, not generated independently or populated from the synthetic unit fixture.

## Automated checks

- **14 Python tests passed**, including database integration: null preservation, calendar YoY calculation, retry idempotence, changed-snapshot/run-ID rejection, atomic rollback of raw/core writes after an injected SQL error, and JSON/gzip/CSV export.
- **7 JavaScript tests passed**: filters, aggregation, missing measures, missing calendar months, baseline screening, leap-year month length and CSV quoting.
- Python compilation and JavaScript syntax checks passed. Compose YAML parsed successfully.
- GitHub Actions completed successfully against **native PostgreSQL 16**, including the integration test and `docker compose config -q`: [validation run](https://github.com/Syamim5499/oil-gas-production-analytics/actions/runs/37031430087). GitHub Pages deployment also completed successfully.

## Example observations from the July 2026 snapshot

These are descriptive sample findings, not operational diagnoses:

| Metric | Result |
| --- | --- |
| Reported net oil equivalent | 20.688186 million Sm³ o.e. |
| Reported net oil | 8.788574 million Sm³ |
| Reported net gas | 10.903369 billion Sm³ |
| Reported fields | 106 |
| Fields with positive net oil equivalent | 91 |
| Fields meeting the review screen | 25 |
| Top three fields by positive reported o.e. | Troll, Johan Sverdrup, Oseberg |
| Top-three share of positive reported o.e. | 37.7% |

The complete historical extract contains **79 records with a negative net measure**. Those values are preserved. The latest month has one such record and no missing measures among reported field rows. This does not establish that all expected fields reported, or why a signed value occurred.

## Limits

The Airflow scheduler/webserver Docker stack has not been executed in the authoring workspace. Local PGlite checks and native PostgreSQL CI validate the load/export and SQL analytics; they do not prove Airflow container startup. API source data can be revised. The public dashboard is a dated snapshot; the provided DAG and export commands enable refresh on the user's machine.
