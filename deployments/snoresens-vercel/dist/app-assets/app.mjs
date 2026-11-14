import {analyzeInBrowser} from './browser-inference.mjs';
import {eventTime} from './temporal.mjs';
import {listRecords,saveRecord,deleteRecord,clearRecords} from './store.mjs';
import {startRecording} from './audio.mjs';

const $=s=>document.querySelector(s),content=$('#content'),modal=$('#modal');
const {researchScores,toCsv}=window.SanorMeasurements;
const nav=[['home','house','หน้าหลัก'],['report','chart-no-axes-column','รายงาน'],['history','history','ประวัติ'],['profile','user-round','โปรไฟล์']];
let records=[],selectedId=null,latestRecordingId=null,consentGranted=false,busy=false,session=null,starting=false,finishing=false,elapsed=0,toastTimer,sourceUrl,storageUnavailable=false;
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon=(name,extra='')=>`<span class="icon ${extra}" style="--icon:url('/app-assets/icons/${name}.svg')" aria-hidden="true"></span>`;
const clock=seconds=>{const s=Math.max(0,Math.floor(seconds||0));return [Math.floor(s/3600),Math.floor(s/60)%60,s%60].map(n=>String(n).padStart(2,'0')).join(':');};
const value=(n,d=1)=>Number.isFinite(n)?n.toFixed(d):'—';
const duration=s=>s>=3600?`${Math.floor(s/3600)} ชม. ${Math.floor(s%3600/60)} น.`:s>=60?`${Math.floor(s/60)} น. ${Math.floor(s%60)} วิ.`:`${value(s,1)} วิ.`;
const date=(iso,short=false)=>new Date(iso).toLocaleDateString('th-TH',{day:'numeric',month:short?'short':'long',...(!short?{year:'numeric'}:{})});
const current=()=>records.find(r=>r.id===selectedId)||records[0];
const pct=r=>100*r.analysis.summary.detected_snore_seconds/r.analysis.summary.recording_seconds;
const countLabel=r=>`พบกรน ${value(pct(r),1)}%`;
function readName(){try{return localStorage.getItem('snoresens-name')||'ผู้ใช้ทั่วไป';}catch{return 'ผู้ใช้ทั่วไป';}}
function route(){return (location.hash.slice(1).split('/')[0]||'home');}
function go(page,id){const hash='#'+page+(id?'/'+encodeURIComponent(id):'');if(location.hash===hash)render();else location.hash=hash;}
function toast(message,error=false){clearTimeout(toastTimer);const node=$('#toast');node.textContent=message;node.className='toast'+(error?' error':'');node.hidden=false;toastTimer=setTimeout(()=>node.hidden=true,error?9000:4500);}
function progress(text){$('#progress').hidden=!text;if(text)$('#progress-text').textContent=text;}
function header(title,back=false){return `<header class="page-header">${back?`<button class="icon-button" data-action="back" aria-label="กลับหน้าหลัก">${icon('chevron-left')}</button><h1>${title}</h1>`:`${icon('moon','brand-logo')}<span class="brand-title">Snoresens AI</span><button class="icon-button header-end" data-action="guide" aria-label="คำแนะนำก่อนบันทึก">${icon('bell')}</button>`}</header>`;}
function renderNav(){for(const target of ['#side-nav','#bottom-nav'])$(target).innerHTML=nav.map(([key,glyph,label])=>`<a class="nav-item ${route()===key?'active':''}" href="#${key}" ${route()===key?'aria-current="page"':''}>${icon(glyph)}<span>${label}</span></a>`).join('');}
function banner(){return session?.active?`<button class="record-banner" data-action="return-record">${icon('mic')}กำลังบันทึก · แตะเพื่อกลับ</button>`:'';}
function empty(title='ยังไม่มีบันทึก',text='บันทึกเสียงหรืออัปโหลด WAV เพื่อดูผล'){return `<section class="empty-card"><div class="empty-icon">${icon('moon')}</div><h3>${title}</h3><p>${text}</p><button class="text-button" data-action="upload">${icon('upload')}เลือกไฟล์เสียง</button></section>`;}
function recordCard(r,latest=false){return `<button class="${latest?'latest-card':'history-card'}" data-action="open-report" data-id="${esc(r.id)}">${latest?icon('sun','sun'):''}<div><div class="record-title">${esc(date(r.createdAt,latest))}${latest?` · บันทึก ${duration(r.analysis.summary.recording_seconds)}`:''}</div><div class="record-subtitle">${latest?'':duration(r.analysis.summary.recording_seconds)+' · '}${r.isSample?'เสียงตัวอย่าง':'เสียงของคุณ'}</div>${latest?`<span class="pill amber" style="margin-top:8px">${countLabel(r)}</span>`:''}</div>${latest?icon('chevron-right','chevron'):`<span class="pill">${countLabel(r)}</span>`}</button>`;}
function home(){
  const latest=records[0];
  const disabled=busy||starting||finishing;
  const heights=[10,18,9,28,40,19,12,24,35,16,8,20,31,46,22,13,27,39,18,9,26,35,15,8,19,29,43,21,12,23,33,16,8,20,30,14,9,18,25,12];
  return `${header()}${banner()}
    <section class="home-welcome"><h1>บันทึกเสียงคืนนี้</h1><span>${esc(date(new Date().toISOString()))}</span></section>
    <div class="home-dashboard">
      <section class="home-start">
        <div class="home-recorder">
          <div class="home-recorder-heading">${icon('moon')}<h2>บันทึกเสียงระหว่างนอน</h2></div>
          <p>วางอุปกรณ์ข้างเตียง แล้วเริ่มบันทึก</p>
          <div class="home-signal" aria-hidden="true"><div class="home-signal-line">${heights.map(h=>`<i style="--height:${h}px"></i>`).join('')}</div><div class="home-mic">${icon('mic')}</div><div class="home-signal-line">${heights.slice().reverse().map(h=>`<i style="--height:${h}px"></i>`).join('')}</div></div>
          <button class="primary home-record-button" data-action="start-guide" ${disabled?'disabled':''}>${icon('mic')}${session?.active?'กลับไปดูการบันทึก':'เริ่มบันทึก'}${icon('chevron-right')}</button>
          <p class="home-record-hint">เปิดเว็บและหน้าจอไว้ระหว่างบันทึก</p>
        </div>
        <div class="home-utilities">
          <button class="home-utility" data-action="upload" ${disabled||session?.active?'disabled':''}>${icon('upload')}<span><strong>อัปโหลดเสียง</strong><small>เลือกไฟล์ WAV</small></span>${icon('chevron-right')}</button>
          <button class="home-utility" data-action="sample" ${disabled||session?.active?'disabled':''}>${icon('headphones')}<span><strong>ลองเสียงตัวอย่าง</strong><small>ดูตัวอย่างผลวิเคราะห์</small></span>${icon('chevron-right')}</button>
        </div>
      </section>
      <aside class="home-recent">
        <div class="section-title"><h2>บันทึกล่าสุด</h2><a href="#history">ดูทั้งหมด ${icon('chevron-right')}</a></div>
        ${latest?`<div class="home-latest">${recordCard(latest,true)}<div class="home-latest-stats"><div><span>เวลาบันทึก</span><strong>${duration(latest.analysis.summary.recording_seconds)}</strong></div><div><span>เวลาที่พบกรน</span><strong>${duration(latest.analysis.summary.detected_snore_seconds)}</strong></div></div><button class="text-button" data-action="open-report" data-id="${esc(latest.id)}">เปิดรายงาน ${icon('arrow-up-right')}</button></div>`:`<div class="home-no-record"><div class="home-empty-icon">${icon('audio-lines')}</div><h3>ยังไม่มีบันทึก</h3><p>ผลจะแสดงที่นี่เมื่อวิเคราะห์เสร็จ</p></div>`}
      </aside>
    </div>
    <footer class="home-bottom"><span>${icon('shield-check')}เสียงและผลเก็บในเบราว์เซอร์นี้</span><p>ผลประมาณเสียงกรน ไม่ใช่การวินิจฉัยโรค</p></footer>`;
}
function report(){
  const r=current();if(!r)return header('รายงานการนอน',true)+empty();
  const s=r.analysis.summary,percent=pct(r),score=researchScores(r.analysis).combined;
  const hop=s.analysis_hop_seconds??1,isV2=s.model_version==='snore-v2-breathing-negatives';
  return `${header('รายงานการนอน',true)}${banner()}<div class="report-meta"><span>บันทึกเมื่อ ${esc(date(r.createdAt))}</span><span class="pill">${r.isSample?'เสียงตัวอย่าง':'ผลวิเคราะห์เสียง'}</span></div><div class="analysis-method"><button class="text-button" data-action="reanalyze" ${busy?'disabled':''}>วิเคราะห์ใหม่</button></div><div class="report-layout"><section><div class="assessment"><span class="pill amber">${countLabel(r)}</span><h2>${s.detected_snore_seconds>0?'พบเสียงคล้ายกรน':'ไม่พบเสียงกรน'}</h2></div><div class="stats-grid"><div class="stat"><div class="label">ระยะเวลาบันทึก</div><div class="number">${duration(s.recording_seconds)}</div></div><div class="stat"><div class="label">เสียงกรน</div><div class="number">${duration(s.detected_snore_seconds)}</div></div></div><section class="sound-summary"><div class="section-title"><h2>สัดส่วนเสียง</h2><span class="small muted">${clock(s.recording_seconds)}</span></div><div class="ratio-track" role="img" aria-label="เสียงกรน ${value(percent)} เปอร์เซ็นต์"><span class="ratio-snore" style="width:${percent}%"></span><span class="ratio-other" style="width:${100-percent}%"></span></div><div class="ratio-legend"><span><i class="dot"></i>กรน ${value(percent)}%</span><span><i class="dot other"></i>ไม่พบกรน ${value(100-percent)}%</span></div></section><button class="insight-button" data-action="show-events">${icon('chart-no-axes-column')}<div><strong>พบกรน ${s.snore_event_count} ช่วง</strong></div>${icon('chevron-right')}</button><p class="report-note">${esc(r.name)}<br>สัดส่วนคำนวณจากเวลาบันทึก ไม่ใช่เวลาหลับ</p><button class="text-button" data-action="explanation">วิธีอ่านผล</button></section><section><div class="player-panel"><h3>ย้อนฟังเสียง</h3><audio id="report-audio" controls preload="metadata"></audio><div class="timeline-visual" id="audio-timeline" role="slider" tabindex="0" aria-label="เลือกเวลาจากกราฟเสียง" aria-valuemin="0" aria-valuemax="${s.recording_seconds}" aria-valuenow="0"><canvas id="overview-timeline" width="1600" height="74" aria-hidden="true"></canvas></div><div class="zoom-panel"><div class="zoom-title"><strong>ซูมละเอียด · ช่วงละ ${hop} วินาที</strong><span id="zoom-range"></span></div><canvas id="detail-timeline" width="1200" height="100" tabindex="0" role="slider" aria-label="เลือกเวลาในกราฟละเอียด ทีละ ${hop} วินาที" aria-valuemin="0" aria-valuemax="${s.recording_seconds}" aria-valuenow="0"></canvas><p>น้ำเงิน = พบกรน · เทา = ไม่พบกรน</p></div><div class="time-axis"><output id="play-time">00:00:00</output><span>${clock(s.recording_seconds)}</span></div><input class="seek" id="seek" type="range" min="0" max="${s.recording_seconds}" step="${hop}" value="0" aria-label="เลือกเวลาในไฟล์เสียง"><div id="events" class="event-buttons">${(r.analysis.snore_events||[]).slice(0,6).map(e=>`<button class="event-row" data-action="seek" data-time="${e.start_seconds}">${icon('play')}กรน · ${eventTime(e.start_seconds)}–${eventTime(e.end_seconds)}<span class="muted">${value(e.duration_seconds,2)} วิ.</span></button>`).join('')||'<p class="small muted">ไม่พบช่วงเสียงกรน</p>'}</div>${s.snore_event_count>6?'<button class="text-button" data-action="all-events">ดูทุกช่วง</button>':''}</div><details class="detail-toggle"><summary>รายละเอียดการวัด</summary><p class="small muted"><span>${isV2?'โมเดลรุ่น 2 · เพิ่มตัวอย่างเสียงหายใจ':'ผลจากโมเดลรุ่นเดิม'} · ตรวจทุก ${hop} วินาที</span></p><dl class="measurements"><dt>ระดับเสียงมัธยฐาน</dt><dd>${value(s.snore_median_rms_dbfs)} dBFS</dd><dt>ช่วงกรนยาวที่สุด</dt><dd>${value(s.longest_snore_event_seconds)} วิ.</dd><dt>คะแนนเสียงกรนรวม · เกณฑ์ทดลอง</dt><dd>${value(score.score)} / 100</dd></dl><p class="small muted">dBFS คือความดังสัมพัทธ์ในไฟล์ คะแนนรวมเป็นเกณฑ์ทดลองของโครงการ ไม่ใช่คะแนนสุขภาพหรือความเสี่ยงโรค หากข้อมูลไม่พอจะแสดง —</p>${s.activity_gate_note?'<p class="small muted">มีการตัดช่วงเสียงเบาตามระดับเสียงในไฟล์ จึงอาจพลาดเสียงกรนเบามาก ผลยังต้องตรวจฟังประกอบ</p>':''}</details><div class="export-row"><button class="secondary" data-action="export-json">${icon('download')}ผล JSON</button><button class="secondary" data-action="export-timeline">${icon('download')}Timeline CSV</button><button class="secondary" data-action="export-audio">${icon('download')}เสียง WAV</button></div><button class="text-button danger-text" data-action="delete-record">${icon('trash-2')}ลบบันทึกนี้</button></section></div>`;
}
function history(){
  const chart=records.slice(0,7).reverse();
  return `${header('ประวัติการนอน',true)}${banner()}<p class="history-subtitle">ภาพรวม ${chart.length?chart.length+' รายการล่าสุด':'การบันทึกของคุณ'}</p>${records.length?`<div class="history-layout"><section><div class="chart-card"><h3>สัดส่วนกรน</h3><div class="history-bars">${chart.map(r=>`<button class="history-bar" data-action="open-report" data-id="${r.id}" aria-label="${esc(date(r.createdAt))} ${countLabel(r)}"><span class="small">${value(pct(r),0)}%</span><span class="bar" style="--height:${Math.max(3,pct(r))}%"></span><span>${new Date(r.createdAt).getDate()}</span></button>`).join('')}</div></div><p class="storage-note">แต่ละรายการเป็นผลแยกกัน แม้บันทึกวันเดียวกัน</p><div class="export-row"><button class="secondary" data-action="export-history">${icon('download')}ทั้งหมด JSON</button><button class="secondary" data-action="export-comparison">${icon('download')}ตาราง CSV</button></div></section><section><div class="section-title"><h2>บันทึกทั้งหมด</h2><span class="record-count">${records.length} รายการ</span></div><div class="history-list">${records.map(r=>recordCard(r)).join('')}</div></section></div>`:empty()}`;
}
function profile(){return `${header('โปรไฟล์',true)}${banner()}<div class="profile-layout"><section><button class="profile-card" data-action="edit-name" aria-label="แก้ไขชื่อที่แสดง">${icon('user-round')}<div><h2>${esc(readName())}</h2><p>แตะเพื่อแก้ไขชื่อ</p></div></button></section><section><div class="profile-menu">${[['privacy','shield-check','ความเป็นส่วนตัว'],['explanation','file-text','วิธีอ่านผล'],['guide','moon','วิธีบันทึก']].map(([action,glyph,label])=>`<button class="menu-item" data-action="${action}">${icon(glyph)}<span>${label}</span>${icon('chevron-right')}</button>`).join('')}</div><button class="text-button danger-text" data-action="clear-data">${icon('trash-2')}ลบประวัติทั้งหมด</button><p class="storage-note">${records.length} รายการ · ล้างข้อมูลเว็บไซต์แล้วประวัติจะหาย</p></section></div>`;}

function prepare(){return `<section class="flow-page">${header('เตรียมก่อนบันทึก',true)}<div class="bed-illustration" aria-label="วางอุปกรณ์ข้างเตียงใกล้ศีรษะ">${icon('moon','bed-moon')}<div class="bed-pillow"></div><div class="bed-mattress"></div><div class="bed-frame"></div><div class="bed-phone"></div><p>วางบนโต๊ะข้างเตียง ใกล้ศีรษะ</p></div><div class="guide-cards">${[['mic','หันไมโครโฟนเข้าหาตัว','วางให้มั่นคง และอย่าคลุมไมโครโฟน'],['volume-2','เตรียมแบตเตอรี่ให้พอ','เปิดเว็บและหน้าจอไว้ระหว่างอัด'],['audio-lines','ลดเสียงรบกวนรอบตัว','เสียงจากคู่นอนอาจมีผลต่อการวิเคราะห์']].map(([glyph,title,text])=>`<div class="guide-card"><span class="guide-icon">${icon(glyph)}</span><div><h3>${title}</h3><p>${text}</p></div></div>`).join('')}</div><p class="flow-note">วิเคราะห์เมื่อหยุดหรือครบส่วนละ 30 นาที</p><button class="primary flow-next" data-action="show-consent">ถัดไป</button></section>`;}
function consent(){return `<section class="flow-page consent-page">${header('ความเป็นส่วนตัว',true)}<div class="consent-intro">${icon('shield-check')}<h1>ก่อนเริ่มบันทึก</h1></div><div class="white-card consent-copy"><h3>การใช้เสียง</h3><ul><li>บันทึกเสียงในห้องระหว่างที่คุณกดอัด</li><li>ใช้วิเคราะห์เสียงกรน</li><li>ดูและลบได้จากประวัติ</li><li>หากมีคู่นอน ควรแจ้งให้ทราบก่อน</li></ul></div><label class="consent-label"><input id="record-consent" type="checkbox"><span>ฉันยินยอมให้บันทึกและวิเคราะห์เสียง</span></label><p class="flow-note">วิเคราะห์ในเบราว์เซอร์บนอุปกรณ์นี้</p><button class="primary flow-next" data-action="begin-record" disabled>เริ่มบันทึก</button></section>`;}

function recording(){const active=session?.active,paused=session?.paused;return `<section class="record-screen"><header class="night-header"><span>Snoresens AI</span><span class="record-badge">${paused?'พักการบันทึก':active?'กำลังบันทึก':finishing?'กำลังวิเคราะห์':'เตรียมบันทึก'}</span></header><div class="night-moon"><div class="moon-art" aria-hidden="true"></div></div><h1>${paused?'พักการบันทึก':active?'กำลังบันทึกเสียง':finishing?'กำลังเตรียมรายงาน':'พร้อมบันทึก'}</h1><div id="record-time" class="record-timer">${clock(elapsed)}</div><p class="night-timer-note">เวลาบันทึก ไม่รวมช่วงพัก</p><div id="record-wave" class="night-wave" aria-hidden="true">${Array.from({length:46},()=>'<i></i>').join('')}</div><div class="night-info">${icon('info')}<span id="record-status">${finishing?'กำลังบันทึกและวิเคราะห์ไฟล์สุดท้าย':'วิเคราะห์หลังคุณหยุดบันทึก'}</span></div><div class="night-actions">${active?`<button class="night-pause" data-action="${paused?'resume-record':'pause-record'}">${paused?'บันทึกต่อ':'พักการบันทึก'}</button><button class="night-stop" data-action="stop-record">จบการบันทึก</button>`:`<button class="primary" data-action="begin-record" ${starting||finishing?'disabled':''}>${starting?'กำลังขอใช้ไมโครโฟน':finishing?'กำลังวิเคราะห์...':'เริ่มบันทึกเสียง'}</button>`}</div><p class="night-footnote">เปิดเว็บและหน้าจอไว้ การล็อกจออาจทำให้อัดหยุด</p></section>`;}

function render(){
  if(sourceUrl){URL.revokeObjectURL(sourceUrl);sourceUrl=null;}
  const [page,id]=location.hash.slice(1).split('/');if(id&&records.some(r=>encodeURIComponent(r.id)===id))selectedId=decodeURIComponent(id);
  content.dataset.page=page||'home';
  $('.app-body').classList.toggle('flow-mode',['prepare','consent','record'].includes(page));
  $('.app-body').classList.toggle('record-mode',page==='record');
  renderNav();content.innerHTML=({report,history,profile,prepare,consent,record:recording}[page]||home)();
  document.title=({report:'รายงาน',history:'ประวัติ',profile:'โปรไฟล์',record:'บันทึกเสียง'}[page]||'หน้าหลัก')+' · Snoresens AI';
  if(page==='report'&&current())setupPlayer();
}
function setupPlayer(){const r=current(),audio=$('#report-audio'),slider=$('#seek');if(r.audio){sourceUrl=URL.createObjectURL(r.audio);audio.src=sourceUrl;}else audio.hidden=true;
  audio.ontimeupdate=()=>{slider.value=audio.currentTime;$('#play-time').textContent=eventTime(audio.currentTime);drawZoom(audio.currentTime);$('#audio-timeline').setAttribute('aria-valuenow',audio.currentTime);};
  slider.oninput=()=>seek(Number(slider.value));const timeline=$('#audio-timeline');
  timeline.onclick=e=>seek((e.clientX-timeline.getBoundingClientRect().left)/timeline.getBoundingClientRect().width*r.analysis.summary.recording_seconds);
  timeline.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();seek(e.key==='Home'?0:e.key==='End'?r.analysis.summary.recording_seconds:audio.currentTime+(e.key==='ArrowRight'?5:-5));}};
  const overview=$('#overview-timeline'),ctx=overview.getContext('2d');ctx.fillStyle='#e7edf8';ctx.fillRect(0,0,overview.width,overview.height);ctx.fillStyle='#3157f5';
  for(const event of r.analysis.snore_events||[])ctx.fillRect(event.start_seconds/r.analysis.summary.recording_seconds*overview.width,8,event.duration_seconds/r.analysis.summary.recording_seconds*overview.width,overview.height-16);
  const zoom=$('#detail-timeline');zoom.onclick=e=>{const rect=zoom.getBoundingClientRect();seek(Number(zoom.dataset.start)+(e.clientX-rect.left)/rect.width*Number(zoom.dataset.span));};zoom.onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();seek(audio.currentTime+(e.key==='ArrowRight'?1:-1)*(r.analysis.summary.analysis_hop_seconds??1));}};drawZoom(0);
}
function seek(time){const audio=$('#report-audio');if(!audio)return;const t=Math.max(0,Math.min(current().analysis.summary.recording_seconds,time));if(audio.readyState)audio.currentTime=t;else audio.addEventListener('loadedmetadata',()=>audio.currentTime=t,{once:true});$('#seek').value=t;$('#play-time').textContent=eventTime(t);drawZoom(t);$('#audio-timeline').setAttribute('aria-valuenow',t);}
function drawZoom(time=0){
  const canvas=$('#detail-timeline');if(!canvas)return;
  const r=current(),duration=r.analysis.summary.recording_seconds,span=Math.min(10,duration),start=Math.max(0,Math.min(time-5,duration-span)),end=start+span;
  canvas.dataset.start=start;canvas.dataset.span=span;canvas.setAttribute('aria-valuenow',time);
  $('#zoom-range').textContent=eventTime(start)+'–'+eventTime(end);
  const ctx=canvas.getContext('2d'),width=canvas.width,height=canvas.height;
  ctx.fillStyle='#e7edf8';ctx.fillRect(0,0,width,height);
  ctx.fillStyle='#3157f5';
  for(const event of r.analysis.snore_events||[]){if(event.end_seconds<=start)continue;if(event.start_seconds>=end)break;ctx.fillRect((Math.max(start,event.start_seconds)-start)/span*width,8,(Math.min(end,event.end_seconds)-Math.max(start,event.start_seconds))/span*width,height-16);}
  ctx.strokeStyle='#152d5915';ctx.lineWidth=1;
  for(let second=Math.ceil(start);second<end;second++){const x=(second-start)/span*width;ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke();}
  ctx.fillStyle='#152d59';ctx.fillRect(Math.max(0,Math.min(width-3,(time-start)/span*width)),0,3,height);
}
function dialog(title,body,actions=''){modal.innerHTML=`<div class="dialog-header"><h2 id="modal-title">${title}</h2><button class="icon-button" data-action="close-modal" aria-label="ปิด">${icon('x')}</button></div><div class="dialog-body">${body}</div>${actions?`<div class="dialog-actions">${actions}</div>`:''}`;if(!modal.open)modal.showModal();}
const guideBody='<ul><li>วางอุปกรณ์ข้างเตียงให้มั่นคง ไม่คลุมไมโครโฟน</li><li>อนุญาตไมโครโฟน แล้วเปิดเว็บและหน้าจอไว้</li><li>ลองอัดสั้น ๆ ก่อนใช้งานจริง การล็อกจอหรือพักเครื่องอาจทำให้อัดหยุด</li><li>เสียงคนอื่นและเสียงรบกวนอาจมีผลต่อการวิเคราะห์</li></ul>';
async function analyze(blob,name,isSample=false,createdAt=new Date().toISOString()){
  busy=true;progress(`กำลังวิเคราะห์ ${name} ...`);
  try {
    if(blob.size>200*1024*1024)throw new Error('เลือก WAV ขนาดไม่เกิน 200 MB ต่อไฟล์');
    const analysis=await analyzeInBrowser(blob,progress);
    const s=analysis.summary;if(!s||!Number.isFinite(s.recording_seconds)||s.recording_seconds<=0||!Number.isFinite(s.detected_snore_seconds)||s.detected_snore_seconds<0||s.detected_snore_seconds>s.recording_seconds)throw new Error('ผลวิเคราะห์ไม่สมบูรณ์ กรุณาลองอีกครั้ง');
    const r={id:crypto.randomUUID(),name,createdAt,analysis,audio:blob,isSample,savedLocally:true};
    try{await saveRecord(r);}catch{r.savedLocally=false;storageUnavailable=true;toast('บันทึกประวัติบนเครื่องไม่ได้ กรุณาดาวน์โหลดผลก่อนปิดหน้าเว็บ',true);}
    records.unshift(r);selectedId=r.id;return r;
  } finally{busy=false;progress(null);}
}
function exportData(r){return {...r.analysis,name:r.name,createdAt:r.createdAt,isSample:r.isSample,audio_scores:researchScores(r.analysis),app_version:1};}
function download(name,body,type){const url=URL.createObjectURL(new Blob([body],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}
async function begin(){if(starting||session?.active||finishing||busy)return;if(!consentGranted){if(route()==='consent'&&$('#record-consent')?.checked)consentGranted=true;else{go('consent');return;}}modal.close();starting=true;elapsed=0;latestRecordingId=null;go('record');try{
    session=await startRecording({onTick:(seconds,rms)=>{elapsed=seconds;if($('#record-time'))$('#record-time').textContent=clock(seconds);const bars=$('#record-wave')?.children;if(bars?.length){for(let i=0;i<bars.length-1;i++)bars[i].style.height=bars[i+1].style.height;bars[bars.length-1].style.height=Math.max(3,Math.min(54,(rms||0)*350))+'px';}},onChunk:async(blob,part,createdAt)=>{const r=await analyze(blob,`snoresens-${createdAt.replace(/[:.]/g,'-')}-part${part}.wav`,false,createdAt);selectedId=r.id;latestRecordingId=r.id;},onError:error=>toast(error.message,true),onDone:()=>{finishing=false;session=null;if(latestRecordingId){go('report',latestRecordingId);}else{render();toast('ยังไม่มีผลวิเคราะห์ที่บันทึกสำเร็จ กรุณาลองอีกครั้ง',true);}}});
  }catch(error){toast(error.name==='NotAllowedError'?'ยังไม่ได้รับอนุญาตไมโครโฟน กรุณาอนุญาตในเบราว์เซอร์แล้วลองใหม่':error.message,true);session=null;}
  finally{starting=false;render();}}

document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-action]');if(!button||button.disabled)return;const action=button.dataset.action;
  try {
    if(action==='back'){go(route()==='consent'?'prepare':'home');return;}
    if(action==='upload'){if(busy||finishing||starting||session?.active){toast('กรุณาหยุดบันทึกหรือรอการวิเคราะห์ให้เสร็จก่อน');return;}$('#audio-file').click();return;}
    if(action==='open-report'){selectedId=button.dataset.id;go('report',selectedId);return;}
    if(action==='close-modal'){modal.close();return;}
    if(action==='start-guide'){if(!session?.active)consentGranted=false;go(session?.active?'record':'prepare');return;}
    if(action==='show-consent'){go('consent');return;}
    if(action==='begin-record'){await begin();return;}
    if(action==='pause-record'){session?.pause();render();return;}
    if(action==='resume-record'){session?.resume();render();return;}
    if(action==='stop-record'){finishing=true;session?.stop();render();return;}
    if(action==='return-record'){go('record');return;}
    if(action==='sample'){if(busy||session?.active||starting||finishing)return;busy=true;progress('กำลังเปิดเสียงตัวอย่าง...');try{const response=await fetch('/samples/test_snore_16k.wav');if(!response.ok)throw new Error('เปิดเสียงตัวอย่างไม่ได้');const r=await analyze(await response.blob(),'test_snore_16k.wav',true);go('report',r.id);}finally{busy=false;progress(null);}return;}
    if(action==='guide'){dialog('คำแนะนำก่อนบันทึก',guideBody);return;}
    if(action==='privacy'){dialog('ความเป็นส่วนตัว','<p>เสียงที่เลือกหรืออัดจะประมวลผลด้วยโมเดลบนอุปกรณ์นี้ ไม่มีการอัปโหลดเสียงไปเซิร์ฟเวอร์</p><p>เสียงและผลเก็บในเบราว์เซอร์นี้ ผู้ใช้โปรไฟล์เบราว์เซอร์เดียวกันอาจเปิดดูได้</p><p>ลบได้จากรายงานหรือโปรไฟล์ การล้างข้อมูลเว็บไซต์จะลบประวัติด้วย ไฟล์ที่ดาวน์โหลดไว้ยังอยู่</p>');return;}
    if(action==='explanation'){dialog('เข้าใจผลการวิเคราะห์','<p>ระบบรวมเสียงคล้ายกรนที่ต่อเนื่องกันเป็นช่วง จำนวนช่วงอาจไม่เท่าจำนวนครั้งที่กรนจริง</p><p>สัดส่วนกรนคิดจากเวลาที่พบกรนหารด้วยเวลาบันทึก ไม่ใช่เวลาหลับ ส่วน dBFS คือระดับเสียงสัมพัทธ์ในไฟล์</p><p>คะแนนรวมเป็นสูตรทดลองจากสัดส่วนเวลาและช่วงห่างเสียงกรน ไม่ใช่คะแนนความเสี่ยงโรค และไม่ใช้วินิจฉัยภาวะหยุดหายใจขณะหลับ</p>');return;}
    if(action==='edit-name'){dialog('แก้ไขชื่อ',`<form id="name-form" class="profile-form"><label for="display-name">ชื่อที่แสดง</label><input id="display-name" name="name" maxlength="50" value="${esc(readName())}" required><button class="primary" type="submit">บันทึก</button></form>`);$('#name-form').onsubmit=e=>{e.preventDefault();try{localStorage.setItem('snoresens-name',$('#display-name').value.trim()||'ผู้ใช้ทั่วไป');modal.close();render();toast('บันทึกแล้ว');}catch{toast('บันทึกบนเบราว์เซอร์นี้ไม่ได้',true);}};return;}
    if(action==='delete-record'||action==='clear-data'){if(session?.active||starting||finishing||busy){toast('กรุณาหยุดบันทึกและรอการวิเคราะห์ให้เสร็จก่อนลบข้อมูล');return;}const all=action==='clear-data';dialog(all?'ลบประวัติทั้งหมด?':'ลบการบันทึกนี้?',`<p>${all?'เสียงและผลวิเคราะห์ทั้งหมด':'เสียงและผลรายการนี้'}ในเบราว์เซอร์นี้จะถูกลบ ไฟล์ต้นฉบับและไฟล์ที่ดาวน์โหลดไว้ยังอยู่</p>`,`<button class="secondary" data-action="close-modal">ยกเลิก</button><button class="primary danger" data-action="${all?'confirm-clear':'confirm-delete'}">ยืนยันลบ</button>`);return;}
    if(action==='confirm-clear'){await clearRecords();records=[];selectedId=null;modal.close();render();toast('ลบข้อมูลทั้งหมดแล้ว');return;}
    if(action==='confirm-delete'){const r=current(),id=r?.id;if(!id)return;if(r.savedLocally!==false)await deleteRecord(id);records=records.filter(r=>r.id!==id);selectedId=records[0]?.id;modal.close();go('history');toast('ลบการบันทึกแล้ว');return;}
    if(action==='seek'){seek(Number(button.dataset.time));return;}
    if(action==='show-events'){$('#events')?.scrollIntoView({behavior:'smooth',block:'center'});return;}
    if(action==='all-events'){$('#events').innerHTML=current().analysis.snore_events.map(e=>`<button class="event-row" data-action="seek" data-time="${e.start_seconds}">${icon('play')}กรน · ${eventTime(e.start_seconds)}–${eventTime(e.end_seconds)} · ${value(e.duration_seconds,2)} วิ.</button>`).join('');button.remove();return;}
    if(action==='reanalyze'){if(busy||starting||finishing||session?.active)return;const r=current();if(!r?.audio){toast('ไม่มีไฟล์เสียงเดิม กรุณาอัปโหลดใหม่',true);return;}const next=await analyze(r.audio,r.name,r.isSample,r.createdAt);go('report',next.id);return;}
    if(action==='export-json'){const r=current();download(r.name+'-analysis.json',JSON.stringify(exportData(r),null,2),'application/json');return;}
    if(action==='export-timeline'){const r=current();download(r.name+'-timeline.csv','\uFEFF'+toCsv(r.analysis.timeline||[]),'text/csv;charset=utf-8');return;}
    if(action==='export-audio'){const r=current();if(r.audio)download(r.name,r.audio,'audio/wav');else toast('ไม่มีไฟล์เสียงในรายการนี้');return;}
    if(action==='export-history'){download('snoresens-results.json',JSON.stringify(records.map(exportData),null,2),'application/json');return;}
    if(action==='export-comparison'){download('snoresens-comparison.csv','\uFEFF'+toCsv(records.map(r=>({file:r.name,created_at:r.createdAt,recording_seconds:r.analysis.summary.recording_seconds,detected_snore_seconds:r.analysis.summary.detected_snore_seconds,snore_percent_of_recording:pct(r),snore_event_count:r.analysis.summary.snore_event_count,combined_snore_score:researchScores(r.analysis).combined.score,is_sample:r.isSample}))),'text/csv;charset=utf-8');}
  } catch(error){progress(null);busy=false;toast(error.message||'ทำรายการไม่สำเร็จ กรุณาลองอีกครั้ง',true);}
});
$('#audio-file').onchange=async event=>{const files=Array.from(event.target.files);event.target.value='';if(busy||session?.active||finishing||starting)return;for(const file of files){if(!file.name.toLowerCase().endsWith('.wav')){toast('เลือกไฟล์ WAV เท่านั้น',true);continue;}try{const r=await analyze(file,file.name);go('report',r.id);}catch(error){toast(error.message,true);}}};
document.addEventListener('change',event=>{if(event.target.id==='record-consent')$('[data-action="begin-record"]').disabled=!event.target.checked;});
modal.addEventListener('click',e=>{if(e.target===modal){const rect=modal.getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)modal.close();}});
window.addEventListener('hashchange',()=>{if(modal.open)modal.close();$('#toast').hidden=true;render();window.scrollTo(0,0);});
window.addEventListener('beforeunload',event=>{if(session?.active||finishing||busy){event.preventDefault();event.returnValue='';}});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&session?.active)toast('ยังบันทึกอยู่ แต่เบราว์เซอร์อาจหยุดเมื่อเครื่องพัก กรุณาเปิดอุปกรณ์ไว้',true);});
try{records=await listRecords();}catch{storageUnavailable=true;toast('อ่านประวัติบนเครื่องไม่ได้ ผลใหม่จะเก็บได้เฉพาะแท็บนี้',true);}
selectedId=records[0]?.id;render();
