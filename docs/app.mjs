import {aggregateMonths, filterRows, reviewQueue, csvRows, daysInMonth} from './analytics.mjs';
const $=id=>document.getElementById(id);
const fmt=(v,n=3)=>v===null||v===undefined?'n/a':Number(v).toLocaleString('en-US',{minimumFractionDigits:n,maximumFractionDigits:n});
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const monthName=m=>new Date(m+'T00:00:00Z').toLocaleDateString('en-GB',{month:'short',year:'numeric',timeZone:'UTC'});
let data, visible=[];

function lineChart(series){
  const w=650,h=260,p={l:45,r:14,t:18,b:34};
  const known=series.filter(r=>r.oe!==null);
  if(!known.length)return '<p class="note">No reported oil-equivalent measures.</p>';
  const max=Math.max(...known.map(r=>r.oe),0.01)*1.12,min=Math.min(...known.map(r=>r.oe),0)*1.12;
  const x=i=>p.l+i*(w-p.l-p.r)/Math.max(series.length-1,1),y=v=>h-p.b-(v-min)/(max-min)*(h-p.t-p.b);
  let svg=`<svg class="svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Monthly oil equivalent production trend">`;
  for(let i=0;i<5;i++){const v=min+(max-min)*i/4;svg+=`<line class="gridline" x1="${p.l}" x2="${w-p.r}" y1="${y(v)}" y2="${y(v)}"/><text class="chart-label" x="${p.l-8}" y="${y(v)+4}" text-anchor="end">${fmt(v,1)}</text>`;}
  // Start a new segment after missing months; never bridge missing measures.
  let segment=[];
  const draw=()=>{if(segment.length)svg+=`<polyline fill="none" stroke="#087f8c" stroke-width="3" stroke-linejoin="round" points="${segment.join(' ')}"/>`;segment=[];};
  series.forEach((r,i)=>{if(r.oe===null){draw();return;}segment.push(`${x(i)},${y(r.oe)}`);});draw();
  series.forEach((r,i)=>{if(r.oe!==null)svg+=`<circle cx="${x(i)}" cy="${y(r.oe)}" r="3" fill="#087f8c"><title>${monthName(r.month)}: ${fmt(r.oe)} million Sm³ o.e.; ${r.reported} field records</title></circle>`;});
  const ticks=[...new Set([0,Math.floor((series.length-1)/2),series.length-1])];
  ticks.forEach(i=>{svg+=`<text class="chart-label" x="${x(i)}" y="${h-8}" text-anchor="${i===0?'start':i===series.length-1?'end':'middle'}">${monthName(series[i].month)}</text>`;});
  return svg+'</svg>';
}

function mixChart(current){
  const parts=[['Oil',current.oil,'#087f8c'],['NGL',current.ngl,'#63bfb3'],['Condensate',current.condensate,'#e4b06a']];
  if(parts.some(p=>p[1]===null||p[1]<0))return '<p class="note">Liquid mix unavailable: one or more component totals are missing or negative. See reported values in the detail table.</p>';
  const total=parts.reduce((s,p)=>s+p[1],0);if(total<=0)return '<p class="note">No reported liquid production.</p>';
  let angle=0;
  let circles='';
  for(const [name,value,color]of parts){const share=value/total*100;circles+=`<circle cx="100" cy="100" r="70" fill="none" stroke="${color}" stroke-width="23" pathLength="100" stroke-dasharray="${share} ${100-share}" stroke-dashoffset="${-angle}" transform="rotate(-90 100 100)"><title>${name}: ${fmt(value)} million Sm³ (${fmt(share,1)}%)</title></circle>`;angle+=share;}
  return `<div class="mix-wrap"><svg viewBox="0 0 200 200" role="img" aria-label="Liquid production composition">${circles}<text x="100" y="99" text-anchor="middle" fill="#173345" font-size="24" font-weight="700">${fmt(total,2)}</text><text x="100" y="120" text-anchor="middle" fill="#526c79" font-size="10">million Sm³ liquids</text></svg><div class="legend">${parts.map(([name,value,color])=>`<div><span class="swatch" style="background:${color}"></span><b>${name} · ${fmt(value/total*100,1)}%</b><small>${fmt(value)} million Sm³</small></div>`).join('')}</div></div>`;
}

function barChart(rows){
  const top=rows.filter(r=>r.oe_msm3!==null&&r.oe_msm3>0).sort((a,b)=>b.oe_msm3-a.oe_msm3).slice(0,10);
  if(!top.length)return '<p class="note">No positive production reported.</p>';
  const w=610,h=top.length*28+16,left=132,right=70,max=top[0].oe_msm3;
  return `<svg class="svg-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Top ten fields by monthly production">${top.map((r,i)=>{const width=r.oe_msm3/max*(w-left-right);return `<text class="chart-label" x="${left-10}" y="${i*28+24}" text-anchor="end">${escape(r.field_name)}</text><rect x="${left}" y="${i*28+10}" width="${width}" height="18" rx="3" fill="${i===0?'#087f8c':'#8bc7c5'}"><title>${escape(r.field_name)}: ${fmt(r.oe_msm3)} million Sm³ o.e.</title></rect><text class="chart-label" x="${left+width+8}" y="${i*28+24}">${fmt(r.oe_msm3,2)}</text>`;}).join('')}</svg>`;
}

function updateFields(){
  const old=$('field').value;
  const rows=filterRows(data.rows,$('region').value);
  const fields=[...new Map(rows.map(r=>[String(r.field_id),r.field_name])).entries()].sort((a,b)=>a[1].localeCompare(b[1]));
  $('field').innerHTML='<option value="all">All fields</option>'+fields.map(([id,name])=>`<option value="${id}">${escape(name)}</option>`).join('');
  if(fields.some(([id])=>id===old))$('field').value=old;
}

function render(){
  const rows=filterRows(data.rows,$('region').value,$('field').value);
  const month=$('month').value;
  visible=rows.filter(r=>r.month===month).sort((a,b)=>(b.oe_msm3??-1)-(a.oe_msm3??-1));
  const allMonths=aggregateMonths(rows), current=allMonths.find(r=>r.month===month);
  if(!current||current.reported===0){$('kpis').innerHTML='<p>No field records for this month and selection.</p>';$('trend').innerHTML=lineChart(allMonths.filter(r=>r.month<=month));['mix','ranking','declines','details'].forEach(id=>$(id).innerHTML='');$('coverage').textContent='No reported records. Missing observations are not zero.';$('concentration').textContent='';return;}
  const index=allMonths.indexOf(current),previous=allMonths[index-1];
  const monthIndex=m=>Number(m.slice(0,4))*12+Number(m.slice(5,7));
  const consecutive=previous&&monthIndex(current.month)-monthIndex(previous.month)===1;
  const rateChange=consecutive&&previous.oe>0&&current.oe!==null?(current.oe/daysInMonth(current.month)/(previous.oe/daysInMonth(previous.month))-1)*100:null;
  const delta=rateChange===null?'Previous calendar month unavailable':`${rateChange>=0?'+':''}${fmt(rateChange,1)}% vs prior month daily rate`;
  const cards=[['NET OIL EQUIVALENT',current.oe,'million Sm³ o.e.',delta],['NET OIL',current.oil,'million standard m³','Reported monthly net volume'],['NET GAS',current.gas,'billion standard m³','Reported monthly net volume'],['PRODUCING FIELDS',current.producing,'fields with positive net o.e.',`${current.reported} field records reported`]];
  $('kpis').innerHTML=cards.map(([label,value,unit,detail])=>`<div class="kpi"><div class="label">${label}</div><div class="value">${fmt(value,label==='PRODUCING FIELDS'?0:2)}</div><div class="unit">${unit}</div><div class="delta">${detail}</div></div>`).join('');
  const length=$('window').value;let trend=allMonths.filter(r=>r.month<=month);if(length!=='all')trend=trend.slice(-Number(length));
  $('trend').innerHTML=lineChart(trend);$('mix').innerHTML=mixChart(current);$('ranking').innerHTML=barChart(visible);
  const top3=visible.filter(r=>r.oe_msm3>0).slice(0,3).reduce((s,r)=>s+r.oe_msm3,0);
  const positiveTotal=visible.filter(r=>r.oe_msm3>0).reduce((s,r)=>s+r.oe_msm3,0);
  $('concentration').textContent=`Top three fields account for ${positiveTotal>0?fmt(top3/positiveTotal*100,1)+'%':'n/a'} of positive reported net oil-equivalent volume in this selection.`;
  const queue=reviewQueue(visible);
  $('declines').innerHTML=queue.length?queue.map(r=>`<tr><td>${escape(r.field_name)}</td><td class="numeric">${fmt(r.oe_msm3)}</td><td class="numeric negative">${fmt(r.yoy_daily_rate_pct,1)}%</td></tr>`).join(''):'<tr><td colspan="3">No fields meet this screen in the selection.</td></tr>';
  $('details').innerHTML=visible.map(r=>`<tr><td><b>${escape(r.field_name)}</b></td><td>${escape(r.region)}</td><td>${escape(r.current_operator)}</td><td class="numeric">${fmt(r.oil_msm3)}</td><td class="numeric">${fmt(r.gas_bsm3)}</td><td class="numeric">${fmt(r.oe_msm3)}</td><td class="numeric">${r.yoy_daily_rate_pct===null?'n/a':fmt(r.yoy_daily_rate_pct,1)+'%'}</td></tr>`).join('');
  $('coverage').textContent=`${monthName(month)} · ${current.reported} reported field records · ${current.incomplete} records have missing measures · ${current.negative} records have negative reported measures. Current operator labels apply across the history.`;
}

async function init(){
  const response=await fetch('./data/dashboard.json.gz');if(!response.ok)throw Error('Unable to load the warehouse export');
  const decompressed=response.body.pipeThrough(new DecompressionStream('gzip'));
  data=await new Response(decompressed).json();if(!Array.isArray(data.rows)||!data.rows.length)throw Error('The export has no production records');
  const regions=[...new Set(data.rows.map(r=>r.region))].sort();
  $('region').innerHTML+=[...regions].map(r=>`<option value="${escape(r)}">${escape(r)}</option>`).join('');
  const months=[...new Set(data.rows.map(r=>r.month))].sort().reverse();
  $('month').innerHTML=months.map(m=>`<option value="${m}">${monthName(m)}</option>`).join('');
  $('freshness').textContent=`Source through ${monthName(months[0])} · snapshot exported ${data.exported_at.slice(0,10)}`;
  $('audit').textContent=`Warehouse run: ${data.run.run_id} · ${data.run.fact_rows.toLocaleString()} source field-month rows · ${data.run.field_rows} field dimensions · checksum ${data.run.snapshot_hash.slice(0,16)}`;
  updateFields();render();
  $('region').addEventListener('change',()=>{updateFields();render();});
  ['field','month','window'].forEach(id=>$(id).addEventListener('change',render));
  $('reset').addEventListener('click',()=>{$('region').value='all';$('field').value='all';$('month').value=months[0];$('window').value='24';updateFields();render();});
  $('download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([csvRows(visible)],{type:'text/csv;charset=utf-8;'}));const a=document.createElement('a');a.href=url;a.download=`oil-gas-${$('month').value}.csv`;a.click();URL.revokeObjectURL(url);});
}
init().catch(error=>{$('error').hidden=false;$('error').textContent=`Dashboard could not load: ${error.message}. Run the pipeline and serve the docs folder over HTTP; opening index.html directly may block the data request.`;});
