-- Case 1: compare portfolio monthly output; unequal month length matters.
SELECT month, oe_msm3, oil_msm3, gas_bsm3, producing_fields, incomplete_rows
FROM mart.portfolio_monthly ORDER BY month DESC LIMIT 24;

-- Case 2: largest fields by reported monthly net oil-equivalent volume.
SELECT field_name, region, current_operator, oe_msm3, yoy_daily_rate_pct
FROM mart.field_monthly
WHERE month = (SELECT max(month) FROM mart.field_monthly)
ORDER BY oe_msm3 DESC NULLS LAST LIMIT 10;

-- Case 3: screen fields for a ≥20% YoY fall in day-normalised output.
-- This is a review queue, not a diagnosis of operational downtime.
SELECT field_name, month, oe_msm3, prior_year_oe_msm3, yoy_daily_rate_pct
FROM mart.decline_screen ORDER BY yoy_daily_rate_pct;

-- Case 4: current-operator view of reported volume.
-- These are gross field volumes attributed to today's operator, not equity shares.
SELECT current_operator, sum(oe_msm3) AS operated_field_oe_msm3
FROM mart.field_monthly
WHERE month = (SELECT max(month) FROM mart.field_monthly)
GROUP BY current_operator ORDER BY operated_field_oe_msm3 DESC;
