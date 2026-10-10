'use strict';
const icons = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  flow:'<rect x="8" y="2" width="8" height="5" rx="1"/><rect x="2" y="17" width="8" height="5" rx="1"/><rect x="14" y="17" width="8" height="5" rx="1"/><path d="M12 7v5M6 17v-5h12v5"/>',
  file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  book:'<path d="M12 5v16M3 3h5a4 4 0 0 1 4 3 4 4 0 0 1 4-3h5v16h-5a4 4 0 0 0-4 2 4 4 0 0 0-4-2H3z"/>',
  code:'<path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9.5 8.5a2.5 2.5 0 0 1 5 1c0 2-2.5 2-2.5 4m0 3h.01"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/>',
  play:'<path d="m8 4 13 8-13 8z"/>',
  money:'<path d="M12 2v20m5-16H9a3 3 0 0 0 0 6h6a3 3 0 0 1 0 6H6"/>',
  bag:'<rect x="4" y="7" width="16" height="14" rx="2"/><path d="M8 9V6a4 4 0 0 1 8 0v3"/>',
  trend:'<path d="m3 17 6-6 4 4 8-10m-7 0h7v7"/>',
  cart:'<path d="M2 3h3l3 12h10l3-9H6"/><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/>',
  pie:'<path d="M21 12a9 9 0 1 1-9-9v9z"/><path d="M15 3a9 9 0 0 1 6 6h-6z"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  table:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
  check:'<path d="m4 12 5 5L20 6"/>',
  copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>'
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.file}</svg>`;
const fillIcons = () => document.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const money = (number, digits=2) => new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:digits,minimumFractionDigits:digits}).format(number);
const monthLabel = period => new Intl.DateTimeFormat('en-US',{month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(`${period}-01T00:00:00Z`));
const colors = ['#9473d9','#c2ace9','#e1d5f1','#ba9aca'];
let currentRun, localPipeline=false, auditExpanded=false, loading=false, loadVersion=0;
const viewMeta = {
  overview:['Overview','YOUR BUSINESS, AT A GLANCE','Good data. Clear decisions.','The numbers that matter, without the spreadsheet shuffle.'],
  pipeline:['Data pipeline','FROM RAW TO RELIABLE','A cleaner path to insight.','Every row checked. Every transformation accounted for.'],
  reports:['Reports & email','THE FINISHED HANDOFF','Your report. Ready to go.','Useful numbers, a clear narrative and an email ready for delivery.'],
  project:['Project notes','THE PROJECT BEHIND THE NUMBERS','Built to make busywork disappear.','An engineering portfolio for automated business reporting.']
};
function switchView(){
  const requested=location.hash.slice(1)||'overview';
  if(requested==='main')return;
  const view=viewMeta[requested]?requested:'overview';
  const [breadcrumb,eyebrow,title,subtitle]=viewMeta[view];
  $('breadcrumb').textContent=breadcrumb; $('eyebrow').textContent=eyebrow;
  $('page-title').textContent=title; $('page-subtitle').textContent=subtitle;
  document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==`view-${view}`);
  document.querySelectorAll('nav a').forEach(el=>{const active=el.dataset.view===view;el.classList.toggle('active',active);if(active)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
  if(view!=='project') $('demo-video').pause();
  if(view==='overview'&&currentRun)chart(currentRun.metrics,currentRun.month);
  window.scrollTo({top:0,behavior:'instant'});
}
function showStatus(text,error=false){$('status').textContent=text;$('status').classList.toggle('error',error);}
function renderMetrics(m){
  const defs=[['Net revenue','revenue',money(m.revenue),'money'],['Completed orders','orders',m.orders.toLocaleString(),'bag'],['Gross margin','margin',m.margin.toFixed(1)+'%','trend'],['Average order value','aov',money(m.aov),'cart']];
  $('metrics').innerHTML=defs.map(([label,key,value,symbol])=>{
    const delta=m.deltas[key];const change=delta===null?'No baseline':`${delta>=0?'↗':'↘'} ${Math.abs(delta).toFixed(1)}${key==='margin'?' pp':'%'}`;
    return `<article class="metric-card"><div class="metric-label"><span>${label}</span><span class="metric-icon"><span data-icon="${symbol}"></span></span></div><div class="metric-value">${value}</div><div class="metric-bottom"><span class="delta ${delta===null?'none':delta<0?'down':''}">${change}</span><span>vs. previous month</span></div></article>`;
  }).join('');
}
function chart(m,period){
  const days=new Date(Number(period.slice(0,4)),Number(period.slice(5,7)),0).getDate();
  const series=Array.from({length:days},(_,i)=>m.daily.find(item=>Number(item.name.slice(-2))===i+1)?.revenue||0);
  const prior=m.previous?Array.from({length:days},(_,i)=>m.previous.daily.find(item=>Number(item.name.slice(-2))===i+1)?.revenue||0):[];
  const W=Math.max(260,$('revenue-chart').clientWidth-42),H=205,L=45,R=14,T=14,B=28;
  const max=Math.max(...series,...prior,1);const top=Math.ceil(max/1000)*1000;
  const x=i=>L+i/(days-1)*(W-L-R);const y=v=>T+(1-v/top)*(H-T-B);
  const line=values=>values.map((v,i)=>`${i===0?'M':'L'}${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(' ');
  const grid=Array.from({length:5},(_,i)=>{const value=top*i/4,yy=y(value);return `<line x1="${L}" y1="${yy}" x2="${W-R}" y2="${yy}" stroke="#f0edf5" stroke-dasharray="3 4"/><text x="${L-10}" y="${yy+3}" text-anchor="end" fill="#a79ab8" font-size="9">${value?money(value/1000,1)+'k':'$0'}</text>`;}).join('');
  const labels=[0,7,14,21,days-1].map(i=>`<text x="${x(i)}" y="${H-4}" text-anchor="middle" fill="#a99bbb" font-size="9">${String(i+1).padStart(2,'0')} ${new Intl.DateTimeFormat('en-US',{month:'short',timeZone:'UTC'}).format(new Date(period+'-01T00:00:00Z'))}</text>`).join('');
  const dots=series.map((v,i)=>`<circle cx="${x(i)}" cy="${y(v)}" r="4" fill="transparent"><title>${period}-${String(i+1).padStart(2,'0')}: ${money(v)}</title></circle>`).join('');
  $('revenue-chart').innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Daily net revenue for ${monthLabel(period)}"><title>Daily revenue, USD. Current month solid purple; previous month dashed.</title><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#b59ae7" stop-opacity=".28"/><stop offset="100%" stop-color="#b59ae7" stop-opacity=".01"/></linearGradient></defs>${grid}<path d="${line(series)} L${x(days-1)},${y(0)} L${x(0)},${y(0)}Z" fill="url(#area)"/>${prior.length?`<path d="${line(prior)}" fill="none" stroke="#d5cede" stroke-width="1.4" stroke-dasharray="4 5"/>`:''}<path d="${line(series)}" fill="none" stroke="#a180df" stroke-width="2.2" stroke-linejoin="round"/>${dots}${labels}</svg>`;
  $('chart-period').textContent=`${monthLabel(period)} · ${m.previous?'comparison aligned by day':'no prior month available'}`;
  document.querySelector('.chart-key').hidden=!m.previous;
}
function channels(m){
  const radius=61,circumference=2*Math.PI*radius;let offset=0;
  const arcs=m.channels.map((item,i)=>{const share=m.revenue?item.revenue/m.revenue:0,length=share*circumference;const result=`<circle cx="77" cy="77" r="${radius}" fill="none" stroke="${colors[i]}" stroke-width="17" stroke-dasharray="${Math.max(0,length-3)} ${circumference}" stroke-dashoffset="${-offset}"/>`;offset+=length;return result;}).join('');
  $('channel-chart').innerHTML=`<div class="donut-wrap"><svg viewBox="0 0 154 154" role="img" aria-label="Revenue by sales channel"><circle cx="77" cy="77" r="${radius}" fill="none" stroke="#f6f2fa" stroke-width="17"/>${arcs}</svg><div class="donut-label"><strong>${money(m.revenue/1000,1)}k</strong><small>Total revenue</small></div></div><div class="channel-legend">${m.channels.map((item,i)=>`<div><i style="background:${colors[i]}"></i><span>${escapeHTML(item.name)}</span><strong>${money(item.revenue,0)}</strong><small>${m.revenue?(item.revenue/m.revenue*100).toFixed(0):0}%</small></div>`).join('')}</div>`;
}
function auditRows(){
  const rows=auditExpanded?currentRun.audit.rejected:currentRun.audit.rejected.slice(0,6);
  $('audit-rows').innerHTML=rows.map(row=>`<tr><td>${row.line}</td><td>${escapeHTML(row.order_id)}</td><td>${escapeHTML(row.reason)}</td><td><span class="tag amber">Excluded</span></td></tr>`).join('');
  $('expand-audit').textContent=auditExpanded?'Show fewer rows ↑':`Show all ${currentRun.audit.rejected_rows} rejected rows ↓`;
}
function render(run){
  currentRun=run; const m=run.metrics,a=run.audit,path=`reports/${run.month}/`;
  renderMetrics(m); chart(m,run.month); channels(m);
  $('summary-count').textContent=`${a.accepted_rows} validated source rows · ${a.rejected_rows} exceptions logged · email prepared`;
  $('category-rows').innerHTML=m.categories.map((item,i)=>{const share=m.revenue?item.revenue/m.revenue*100:0;return `<tr><td><span class="category-dot" style="background:${colors[i]}"></span>${escapeHTML(item.name)}</td><td>${item.orders}</td><td>${money(item.revenue,0)}</td><td><span class="share-cell"><span class="share-bar"><i style="width:${share}%"></i></span>${share.toFixed(0)}%</span></td></tr>`;}).join('');
  $('insight-title').textContent=m.categories.length?`${m.categories[0].name} leads the way.`:'A quieter month to review.';
  $('insight-body').textContent=run.insights[1]||run.insights[0];
  $('insight-secondary').textContent=run.insights[0];
  $('audit-metrics').innerHTML=[['Source rows',a.raw_rows,'Complete three-month CSV'],['Accepted rows',a.accepted_rows,`${a.acceptance_rate}% acceptance rate`],['Normalized rows',a.normalized_rows,'Formatting fixed, value preserved'],['Rejected rows',a.rejected_rows,'Every exception documented']].map(([label,value,detail])=>`<div class="audit-metric"><small>${label}</small><strong>${value}</strong><p>${detail}</p></div>`).join('');
  const stages=[['Read the source CSV',`${a.raw_rows} rows loaded with a strict, documented schema.`,'data/synthetic_orders.csv','Inspect source CSV'],['Clean & validate',`${a.accepted_rows} accepted · ${a.normalized_rows} normalized · ${a.rejected_rows} rejected.`,path+'audit.json','Inspect the audit'],['Calculate business metrics',`${m.orders} completed orders · ${money(m.revenue)} net revenue.`,path+'metrics.json','Inspect metrics JSON'],['Generate the executive report','Monthly summary, category performance and documented assumptions.',path+'report.html','Open the report'],['Prepare the email','MIME message built with the HTML report attached. Delivery is separate.',path+'report.eml','Download the email']];
  $('stages').innerHTML=stages.map(([title,body,url,label],i)=>`<li id="stage-${i}"><span class="stage-number">0${i+1}</span><div><h3>${title}</h3><p>${body}</p><a href="${url}" ${i===4?'download':'target="_blank" rel="noopener"'}>${label} ↗</a></div><span class="stage-check"><span data-icon="check"></span>${i===4?'Prepared':'Complete'}</span></li>`).join('');
  $('source-hash').textContent=a.source_sha256; auditRows();
  $('clean-rows').innerHTML=run.preview_rows.map(row=>`<tr><td>${escapeHTML(row.order_id)}</td><td>${escapeHTML(row.order_date)}</td><td>${escapeHTML(row.category)}</td><td>${escapeHTML(row.channel)}</td><td>${row.quantity}</td><td>${money(Number(row.unit_price))}</td><td><span class="tag ${row.status==='completed'?'green':'amber'}">${escapeHTML(row.status)}</span></td></tr>`).join('');
  for(const [id,file] of [['download-rejected','rejected.csv'],['download-cleaned','cleaned.csv'],['open-report','report.html'],['download-report','report.html'],['download-email','report.eml'],['download-metrics','metrics.json']]) $(id).href=path+file;
  $('report-month').textContent=monthLabel(run.month);
  $('email-subject').textContent=`[Synthetic demo] Projenk business report · ${run.month}`;
  $('attachment-name').textContent=`projenk-report-${run.month}.html`;
  $('email-body').innerHTML=`<p>Hello,</p><p>Your ${escapeHTML(run.month)} synthetic business report is ready.</p><ul><li>Net revenue: <strong>${money(m.revenue)}</strong></li><li>Completed orders: <strong>${m.orders}</strong></li><li>Gross margin: <strong>${m.margin.toFixed(1)}%</strong></li><li>Average order value: <strong>${money(m.aov)}</strong></li></ul><p>The attached HTML report includes category performance, observations and the validation methodology. All figures are synthetic.</p><p style="margin-top:15px">Projenk Reporting</p>`;
  $('report-insights').innerHTML=run.insights.map(note=>`<li>${escapeHTML(note)}</li>`).join(''); fillIcons();
}
async function fetchRun(period){
  const response=await fetch(`reports/${period}/run.json`,{cache:'no-store'});
  if(!response.ok)throw new Error('The report could not be loaded. Please retry.');
  return response.json();
}
async function changePeriod(){
  const version=++loadVersion;loading=true;$('run-button').disabled=true;
  try{const run=await fetchRun($('period').value);if(version===loadVersion){render(run);showStatus('');}}
  catch(error){if(version===loadVersion)showStatus(error.message,true);}
  finally{if(version===loadVersion){loading=false;$('run-button').disabled=!currentRun;}}
}
async function runDemo(){
  if(loading)return;loading=true;$('run-button').disabled=true;$('period').disabled=true;location.hash='pipeline';
  try{
    showStatus(localPipeline?'Running the Python pipeline…':'Replaying the stored Python run. No email will be sent.');
    let run;
    if(localPipeline){const response=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({month:$('period').value})});run=await response.json();if(!response.ok)throw new Error(run.error||'Pipeline failed');}
    else run=await fetchRun($('period').value);
    render(run);
    for(let i=0;i<5;i++){const stage=$(`stage-${i}`);stage.classList.add('running');await new Promise(resolve=>setTimeout(resolve,matchMedia('(prefers-reduced-motion: reduce)').matches?0:450));stage.classList.remove('running');}
    showStatus(`${localPipeline?'Python pipeline complete':'Replay complete'}: ${run.audit.accepted_rows} accepted rows, ${run.audit.rejected_rows} rejected. Report and email preview are ready.`);
  }catch(error){showStatus(error.message,true);}
  finally{loading=false;$('run-button').disabled=false;$('period').disabled=false;}
}
async function initialize(){
  fillIcons(); switchView(); $('run-button').disabled=true;
  try{
    const response=await fetch('data/manifest.json');if(!response.ok)throw new Error('Demo manifest unavailable');
    const manifest=await response.json();$('period').value=manifest.default_period;
    if(['127.0.0.1','localhost'].includes(location.hostname)){
      try{const configResponse=await fetch('/api/config');if(configResponse.ok)localPipeline=(await configResponse.json()).local_pipeline===true;}catch(_){/* Static preview remains usable. */}
    }
    if(localPipeline){$('run-label').textContent='Run pipeline';$('mode-note').textContent='Local mode: the button runs the real Python pipeline against the synthetic CSV. Artifacts are regenerated; email is prepared without sending.';}
    await changePeriod();
  }catch(error){showStatus(`${error.message}. Serve this folder over HTTP; see the setup guide.`,true);}
}
window.addEventListener('hashchange',switchView);
window.addEventListener('resize',()=>{if(currentRun)chart(currentRun.metrics,currentRun.month);});
$('period').addEventListener('change',changePeriod);
$('run-button').addEventListener('click',runDemo);
$('expand-audit').addEventListener('click',()=>{auditExpanded=!auditExpanded;auditRows();});
$('copy-setup').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('setup-code').textContent);showStatus('Setup commands copied.');}catch(_){showStatus('Select and copy the commands from the setup box.');}});
initialize();
