-- Current operator/region is a present-day classification, not historical ownership.
CREATE OR REPLACE VIEW mart.field_monthly AS
SELECT f.field_id, d.field_name, d.region, d.current_operator, d.current_status,
       f.month, f.oil_msm3, f.gas_bsm3, f.ngl_msm3, f.condensate_msm3, f.oe_msm3,
       f.oe_msm3 / extract(day FROM (f.month + interval '1 month - 1 day')) AS oe_msm3_per_day,
       p.oe_msm3 AS prior_year_oe_msm3,
       CASE WHEN p.oe_msm3 > 0 THEN
       100 * ((f.oe_msm3 / extract(day FROM (f.month + interval '1 month - 1 day'))) /
         NULLIF(p.oe_msm3 / extract(day FROM (p.month + interval '1 month - 1 day')), 0) - 1)
       END AS yoy_daily_rate_pct,
       (f.oil_msm3 < 0 OR f.gas_bsm3 < 0 OR f.ngl_msm3 < 0
        OR f.condensate_msm3 < 0 OR f.oe_msm3 < 0) AS has_negative_measure
FROM core.fact_production_monthly f
JOIN core.dim_field d ON d.field_id = f.field_id
LEFT JOIN core.fact_production_monthly p ON p.field_id = f.field_id
    AND p.month = (f.month - interval '1 year')::date;

CREATE OR REPLACE VIEW mart.portfolio_monthly AS
SELECT month, sum(oil_msm3) AS oil_msm3, sum(gas_bsm3) AS gas_bsm3,
       sum(ngl_msm3) AS ngl_msm3, sum(condensate_msm3) AS condensate_msm3,
       sum(oe_msm3) AS oe_msm3,
       count(*) AS reported_fields, count(oe_msm3) AS measured_oe_fields,
       count(*) FILTER (WHERE oe_msm3 > 0) AS producing_fields,
       count(*) FILTER (WHERE oil_msm3 IS NULL OR gas_bsm3 IS NULL OR
          ngl_msm3 IS NULL OR condensate_msm3 IS NULL OR oe_msm3 IS NULL) AS incomplete_rows,
       count(*) FILTER (WHERE oil_msm3 < 0 OR gas_bsm3 < 0 OR ngl_msm3 < 0
          OR condensate_msm3 < 0 OR oe_msm3 < 0) AS negative_measure_rows
FROM core.fact_production_monthly GROUP BY month;

CREATE OR REPLACE VIEW mart.decline_screen AS
SELECT * FROM mart.field_monthly
WHERE month = (SELECT max(month) FROM core.fact_production_monthly)
  AND prior_year_oe_msm3 >= 0.01 AND yoy_daily_rate_pct <= -20;
