import test from 'node:test';
import assert from 'node:assert/strict';
import {sumKnown,aggregateMonths,filterRows,reviewQueue,daysInMonth,csvRows} from '../docs/analytics.mjs';

test('missing values remain missing; zeros remain zeros',()=>{
  assert.equal(sumKnown([{x:null}], 'x'),null);
  assert.equal(sumKnown([{x:0},{x:null}], 'x'),0);
});
test('region and field filters are cumulative',()=>{
  const rows=[{region:'A',field_id:1},{region:'B',field_id:2}];
  assert.equal(filterRows(rows,'A','2').length,0);
  assert.equal(filterRows(rows,'A','1').length,1);
});
test('aggregation keeps reported and positive-producing fields distinct',()=>{
  const rows=[{month:'2025-01-01',oe_msm3:2,oil_msm3:1,gas_bsm3:1,ngl_msm3:0,condensate_msm3:0},
    {month:'2025-01-01',oe_msm3:0,oil_msm3:0,gas_bsm3:0,ngl_msm3:null,condensate_msm3:0}];
  const result=aggregateMonths(rows)[0];
  assert.equal(result.oe,2);assert.equal(result.reported,2);assert.equal(result.producing,1);assert.equal(result.incomplete,1);
});
test('decline screen excludes tiny baselines and unknown changes',()=>{
  const rows=[{prior_year_oe_msm3:.02,yoy_daily_rate_pct:-25},
    {prior_year_oe_msm3:.001,yoy_daily_rate_pct:-90},
    {prior_year_oe_msm3:1,yoy_daily_rate_pct:null}];
  assert.equal(reviewQueue(rows).length,1);
});
test('day normalisation handles leap years',()=>{
  assert.equal(daysInMonth('2024-02-01'),29);assert.equal(daysInMonth('2025-02-01'),28);
});
test('missing calendar months appear as gaps rather than zero production',()=>{
  const months=aggregateMonths([{month:'2025-01-01',oe_msm3:2},{month:'2025-03-01',oe_msm3:3}]);
  assert.equal(months.length,3);assert.equal(months[1].month,'2025-02-01');assert.equal(months[1].oe,null);assert.equal(months[1].reported,0);
});
test('CSV quotes names with commas and quotes',()=>{
  assert.ok(csvRows([{field_name:'A, "B"'}]).includes('"A, ""B"""'));
});
