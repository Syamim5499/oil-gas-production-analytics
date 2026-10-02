export const sumKnown = (rows, key) => {
  const values = rows.map(r => r[key]).filter(v => v !== null && v !== undefined);
  return values.length ? values.reduce((a,b) => a+b, 0) : null;
};
export function daysInMonth(month) {
  const [year, m] = month.split('-').map(Number);
  return new Date(Date.UTC(year, m, 0)).getUTCDate();
}
export function filterRows(rows, region='all', field='all') {
  return rows.filter(r => (region === 'all' || r.region === region) &&
    (field === 'all' || String(r.field_id) === field));
}
export function aggregateMonths(rows) {
  const groups = new Map();
  for (const r of rows) { if (!groups.has(r.month)) groups.set(r.month, []); groups.get(r.month).push(r); }
  const periods=[...groups.keys()].sort();
  if(periods.length){
    const cursor=new Date(periods[0]+'T00:00:00Z'),end=new Date(periods.at(-1)+'T00:00:00Z');
    while(cursor<=end){const key=cursor.toISOString().slice(0,10);if(!groups.has(key))groups.set(key,[]);cursor.setUTCMonth(cursor.getUTCMonth()+1);}
  }
  return [...groups.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([month, group])=>({
    month, oe:sumKnown(group,'oe_msm3'), oil:sumKnown(group,'oil_msm3'), gas:sumKnown(group,'gas_bsm3'),
    ngl:sumKnown(group,'ngl_msm3'), condensate:sumKnown(group,'condensate_msm3'), reported:group.length,
    producing:group.filter(r=>r.oe_msm3>0).length,
    incomplete:group.filter(r=>['oil_msm3','gas_bsm3','ngl_msm3','condensate_msm3','oe_msm3'].some(k=>r[k]===null)).length,
    negative:group.filter(r=>r.has_negative_measure===true).length
  }));
}
export function reviewQueue(rows) {
  return rows.filter(r=>r.prior_year_oe_msm3>=0.01 && r.yoy_daily_rate_pct!==null &&
    r.yoy_daily_rate_pct<=-20).sort((a,b)=>a.yoy_daily_rate_pct-b.yoy_daily_rate_pct);
}
export function csvRows(rows) {
  const keys=['month','field_name','region','current_operator','oil_msm3','gas_bsm3','ngl_msm3','condensate_msm3','oe_msm3','yoy_daily_rate_pct'];
  const quote=v=>`"${String(v??'').replaceAll('"','""')}"`;
  return [keys.join(','),...rows.map(r=>keys.map(k=>quote(r[k])).join(','))].join('\r\n');
}
