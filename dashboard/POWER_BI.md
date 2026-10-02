# Use the same warehouse in Power BI Desktop

The included public BI viewer is fully populated and interactive. This optional guide lets you rebuild the same analyses in Power BI; the repository does not claim to contain a native `.pbix` file.

1. Start the stack and run the Airflow DAG successfully.
2. In Power BI Desktop, choose **Get data → PostgreSQL database**. Server: `localhost:5434`; database: `warehouse`. Enter user `warehouse` and the password from your local `.env`. Select Import mode for this educational model. If the connector requires a driver in your installed version, follow the [Microsoft PostgreSQL connector documentation](https://learn.microsoft.com/en-us/power-query/connectors/postgresql).
3. Load `mart.field_monthly`. Rename the model table **Production**. Set `month` to Date, `field_id` to whole number, numeric measures to decimal, and labels to text.
4. Create a calendar table spanning all dates, relate `Calendar[Date]` to `Production[month]`, and mark it as the date table. Monthly facts occur on the first day; month-level visuals are appropriate.
5. Create the measures from `measures.dax`. The YoY metric already exists in SQL at field-month grain; display it for a single field/month rather than summing percentages.

| Visual | Fields / filters |
| --- | --- |
| Cards | Net Oil Equivalent, Net Oil, Net Gas, Producing Fields |
| Line | `month` axis; Net Oil Equivalent values |
| Liquid composition | Oil/NGL/condensate measures; exclude gas to retain consistent units |
| Top 10 bar | `field_name`; Net Oil Equivalent; positive volume; Top N=10 |
| Review table | `field_name`, `oe_msm3`, `yoy_daily_rate_pct`; prior baseline ≥0.01 and YoY ≤−20 |
| Slicers | `region`, `field_name`, `month` |

Do not label current operator as historical operator, sum mixed gas/liquid units, or interpret field volumes as equity production. Negative source net values must remain visible in the detail table; use a table instead of a donut when components are negative. Import refresh re-queries the warehouse after the DAG loads. Power BI Service refresh of a computer-local database would require a separately configured gateway.

As an alternative, `pipeline.export` produces `docs/data/field_monthly.csv`, which Power BI can import without a database connection. That is a file snapshot and refresh requires a newly exported CSV.
