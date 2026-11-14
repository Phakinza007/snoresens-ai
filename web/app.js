const input = document.querySelector('#files');
const choose = document.querySelector('#choose');
const dropzone = document.querySelector('#dropzone');
const status = document.querySelector('#status');
const results = document.querySelector('#results');
const rows = document.querySelector('#rows');
const detail = document.querySelector('#detail');
const recordings = [];
const {timelineBins, comparisonValues, toCsv, soundReviewEntries, breathingStatusText, breathingPlotPoints, snoreScore} = window.SanorMeasurements;
const {researchScores} = window.SanorMeasurements;
let selectedIndex = 0;
let baselineId = null;
choose.addEventListener('click', () => input.click());
input.addEventListener('change', () => analyzeFiles(input.files));
dropzone.addEventListener('dragover', event => { event.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', event => { event.preventDefault(); dropzone.classList.remove('drag'); analyzeFiles(event.dataTransfer.files); });

function settingsHeaders() {
  const threshold = document.querySelector('#quiet-threshold');
  const duration = document.querySelector('#quiet-duration');
  if (!threshold.reportValidity() || !duration.reportValidity()) throw new Error('ตรวจสอบค่าการค้นหาช่วงเงียบ');
  return {'Content-Type':'audio/wav', 'X-Quiet-Threshold-Dbfs':threshold.value, 'X-Min-Quiet-Gap-Seconds':duration.value, 'X-Apnea-Research':document.querySelector('#apnea-enabled').checked ? 'true' : 'false'};
}
async function loadApneaStatus() {
  const state = document.querySelector('#apnea-status');
  const enabled = document.querySelector('#apnea-enabled');
  try {
    const response = await fetch('/api/apnea-status');
    if (!response.ok) throw new Error('ตรวจสอบสถานะไม่ได้');
    const data = await response.json();
    enabled.disabled = data.status !== 'research_only';
    state.textContent = data.status === 'not_trained' ? 'ยังไม่มีโมเดลที่ฝึกด้วยเสียงและป้ายกำกับจากการตรวจการนอนหลับ'
      : data.status === 'research_only' ? 'โมเดลวิจัยพร้อมใช้งาน · ผลเป็นคะแนนรายหน้าต่างเสียงสำหรับคัดช่วงให้ตรวจ'
      : 'โมเดลยังไม่พร้อมใช้งานกับไฟล์ของคุณ';
  } catch (_) { enabled.disabled = true; state.textContent = 'ตรวจสอบสถานะโมเดลไม่ได้ กรุณาเปิดผ่านเซิร์ฟเวอร์ Sanor'; }
}
loadApneaStatus();
async function analyzeFiles(files) {
  status.classList.remove('error');
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith('.wav')) { status.textContent = `ข้าม ${file.name}: ต้องเป็น WAV`; continue; }
    status.textContent = `กำลังวิเคราะห์ ${file.name} ...`;
    try {
      const response = await fetch('/api/analyze', {method:'POST', headers:settingsHeaders(), body:file});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'วิเคราะห์ไม่ได้');
      addRecording(file.name, data, file);
      status.textContent = `วิเคราะห์ ${file.name} แล้ว`;
    } catch (error) { status.classList.add('error'); status.textContent = `${file.name}: ${error.message}`; }
  }
  input.value = '';
}
function addRecording(name, data, source = null, metadata = {}) {
  recordings.push({...data, ...metadata, name, id:crypto.randomUUID(), sourceUrl:source ? URL.createObjectURL(source) : null});
  render(recordings.length - 1);
}
window.addSanorResult = addRecording;
document.querySelector('#load-eight-hour-demo').addEventListener('click', () => {
  status.classList.remove('error');
  try {
    const existing = recordings.findIndex(item => item.is_demo);
    if (existing >= 0) render(existing);
    else addRecording('ตัวอย่างจำลอง 8 ชั่วโมง', window.SanorMeasurements.createEightHourDemo());
    status.textContent = 'โหลดข้อมูลจำลอง 8 ชั่วโมงแล้ว · แสดงค่าทันทีโดยไม่วิเคราะห์เสียง';
    results.scrollIntoView({behavior:'auto', block:'start'});
  } catch (error) {
    status.classList.add('error');
    status.textContent = `โหลดตัวอย่างไม่ได้: ${error.message}`;
  }
});
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, action, className = 'secondary compact') {
  const node = el('button', text, className); node.type = 'button'; node.addEventListener('click', action); return node;
}
function number(value, digits = 1) { return value == null || !Number.isFinite(value) ? '—' : value.toFixed(digits); }
function clock(seconds) {
  return [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, Math.floor(seconds) % 60].map(x => String(x).padStart(2, '0')).join(':');
}
function exportable(item) {
  const {sourceUrl, id, ...data} = item;
  return {...data,audio_scores:{...researchScores(item),snore_duration:{score:snoreScore(item),maximum:100,
    formula:'100 * (1 - detected_snore_seconds / recording_seconds)',
    interpretation:'Higher means less recorded time classified as snoring; not sleep quality or health risk.',version:1}}};
}
function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const link = el('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function comparisonExports() {
  return recordings.map(item => ({file:item.name, recording_seconds:item.summary.recording_seconds,
    snore_duration_score:snoreScore(item), snore_duration_score_maximum:100,
    combined_snore_score:researchScores(item).combined.score, combined_snore_score_version:1,
    pattern_score:researchScores(item).pattern_points.score,
    pattern_total_intervals:researchScores(item).pattern_points.total_intervals,
    pattern_qualifying_intervals:researchScores(item).pattern_points.qualifying_intervals,
    stii_adapted_per_recording_hour:researchScores(item).stii_recording.score,
    pss_score:researchScores(item).pss.score, pss_status:researchScores(item).pss.status,
    snore_percent_of_recording:comparisonValues(item).percent,
    snore_minutes_per_recording_hour:comparisonValues(item).minutes_per_hour,
    snore_events_per_recording_hour:comparisonValues(item).events_per_hour,
    snore_median_rms_dbfs:comparisonValues(item).median_dbfs,
    snore_mean_rms_dbfs:comparisonValues(item).mean_dbfs, snore_max_rms_dbfs:comparisonValues(item).max_dbfs,
    median_pitch_hz:comparisonValues(item).pitch_hz, autocorrelation_period_seconds:comparisonValues(item).rhythm_period,
    louder_returns_count:comparisonValues(item).louder_returns,
    median_dominant_frequency_hz:comparisonValues(item).dominant_hz,
    median_spectral_centroid_hz:comparisonValues(item).centroid_hz,
    interval_cv:comparisonValues(item).rhythm_cv, quiet_gap_count:comparisonValues(item).quiet_gap_count,
    quiet_threshold_dbfs:item.audio_patterns?.config.quiet_threshold_dbfs,
    min_quiet_gap_seconds:item.audio_patterns?.config.min_quiet_gap_seconds,
    session_id:item.session_id ?? null, part:item.part ?? null}));
}
document.querySelector('#export-comparison').addEventListener('click', () => download('sanor-comparison.csv', '\uFEFF' + toCsv(comparisonExports()), 'text/csv;charset=utf-8'));
document.querySelector('#export-json').addEventListener('click', () => download('sanor-results.json', JSON.stringify(recordings.map(exportable), null, 2), 'application/json'));

function render(selected) {
  selectedIndex = Math.max(0, Math.min(selected, recordings.length - 1));
  results.hidden = recordings.length === 0;
  if (!recordings.length) { detail.replaceChildren(); return; }
  document.querySelector('#count').textContent = `${recordings.length} ไฟล์`;
  const baseline = document.querySelector('#baseline'); baseline.replaceChildren(new Option('ไม่เปรียบเทียบค่าต่าง', ''));
  recordings.forEach(item => baseline.add(new Option(item.name, item.id)));
  baseline.value = baselineId ?? '';
  const base = recordings.find(item => item.id === baselineId);
  rows.replaceChildren();
  recordings.forEach((item, index) => {
    const s = item.summary, v = comparisonValues(item);
    const tr = el('tr'); if (index === selectedIndex) tr.classList.add('selected');
    const nameCell = el('td'); nameCell.append(button(item.name, () => render(index), 'file-link')); tr.append(nameCell);
    const values = [`${number(s.recording_seconds / 60)} นาที`, `${number(v.percent)}%`, `${number(researchScores(item).combined.score)} / 100`, number(v.minutes_per_hour), number(v.events_per_hour), number(v.median_dbfs), number(v.dominant_hz, 0), number(v.rhythm_cv, 2), v.quiet_gap_count ?? '—'];
    if (base) {
      const b = comparisonValues(base);
      values.push(`${number(v.percent - b.percent)} จุด % / ${v.median_dbfs == null || b.median_dbfs == null ? '—' : number(v.median_dbfs - b.median_dbfs)} dB`);
    } else values.push('—');
    for (const text of values) tr.append(el('td', text));
    rows.append(tr);
  });
  renderDetail(recordings[selectedIndex]);
  renderSessions();
}
document.querySelector('#baseline').addEventListener('change', event => { baselineId = event.target.value || null; render(selectedIndex); });

function renderDetail(item) {
  detail.replaceChildren();
  const head = el('div', null, 'detail-heading'); head.append(el('h3', item.name));
  head.append(button('ลบผลนี้', () => {
    if (item.sourceUrl) URL.revokeObjectURL(item.sourceUrl);
    recordings.splice(recordings.indexOf(item), 1);
    if (baselineId === item.id) baselineId = null;
    render(selectedIndex);
  })); detail.append(head);
  if (item.is_demo) detail.append(el('p', item.fixture_note));
  const research=researchScores(item), cards=el('div',null,'research-score-grid');
  const totalCard=el('section',null,'snore-score');
  totalCard.append(el('h4','คะแนนเสียงกรนรวม · เกณฑ์ทดลอง'),
    el('p',research.combined.score===null ? 'ข้อมูลไม่พอให้คะแนนรวม' : `${number(research.combined.score)} / 100`,'snore-score-value'),
    el('p','คะแนนเวลากรน × 50% + คะแนนช่วงห่างกรน × 50% · PSS ยังไม่นับรวม'));
  if(research.combined.score!==null) {
    totalCard.append(el('p',`เริ่ม 100 · หักด้านเวลากรน ${number(50*item.summary.detected_snore_seconds/item.summary.recording_seconds)} คะแนน · หักด้านช่วงห่าง ${number(50*research.pattern_points.qualifying_intervals/research.pattern_points.total_intervals)} คะแนน`));
  } else totalCard.append(el('p','ต้องมีข้อมูลครบทั้งสองหมวดและช่วงกรนอย่างน้อย 2 ช่วง ไม่ปรับน้ำหนักเพื่อชดเชยข้อมูลที่ขาด'));
  totalCard.append(el('p','น้ำหนัก 50/50 และสูตรคะแนนเป็นเกณฑ์ทดลองของโครงการ ยังไม่ได้รับการยืนยันทางการแพทย์ ไม่ใช่คะแนนคุณภาพการนอนหรือความเสี่ยงโรค'));
  detail.append(totalCard);
  const scoreDetails=el('details');scoreDetails.append(el('summary','ดูเกณฑ์และคะแนนแต่ละส่วน'));
  for(const [title,value,description,key] of [
    ['คะแนนเวลากรน',research.duration_points.score,
      `เริ่ม 100 หักตามเปอร์เซ็นต์เวลากรน · พบกรน ${number(research.snore_burden.score)}% จึงหัก ${number(research.snore_burden.score)} คะแนน · คะแนนสูงคือพบกรนกินเวลาน้อยกว่า`,'snore_burden'],
    ['คะแนนช่วงห่างกรน',research.pattern_points.score,
      `เริ่ม 100 หักตามเปอร์เซ็นต์ช่วงห่างที่มากกว่า 10 แต่น้อยกว่า 100 วินาที · ${research.pattern_points.qualifying_intervals ?? '—'} จาก ${research.pattern_points.total_intervals ?? '—'} ช่วง · วัดจากจุดเริ่มถึงจุดเริ่มครั้งถัดไป คะแนนสูงคือมีช่วงเข้าเงื่อนไขนี้น้อยกว่า ไม่ได้แปลว่าจังหวะสม่ำเสมอ`,'stii_recording'],
    ['คะแนนเสียงรบกวน · PSS',null,
      'ยังคำนวณไม่ได้: ต้องวัดความดัง N₅ (sone) และความหยาบของเสียงเฉลี่ย (asper) จากเสียงที่สอบเทียบแล้ว ค่า RMS/dBFS ใช้แทนไม่ได้ จึงยังไม่มีคะแนนและไม่นับเป็น 0','pss']
  ]) {
    const card=el('section',null,'snore-score');
    card.append(el('h4',title),el('p',value===null ? 'ยังไม่มีคะแนน' : `${number(value)} / 100`,'snore-score-value'),el('p',description));
    const source=el('a','งานวิจัยของตัวชี้วัด');source.href=research[key].source;source.target='_blank';source.rel='noopener noreferrer';
    card.append(source);cards.append(card);
  }
  scoreDetails.append(cards);
  scoreDetails.append(el('p',`STII ดัดแปลง: ${number(research.stii_recording.score,2)} ช่วง/ชั่วโมงบันทึก · งานต้นฉบับหารด้วยชั่วโมงหลับ ระบบนี้ใช้ช่วงเสียงที่โมเดลตรวจพบและเวลาบันทึก จึงไม่ใช่ AHI`));
  detail.append(scoreDetails);
  const p = item.audio_patterns, rhythm = p?.rhythm_summary;
  const metrics = el('dl', null, 'audio-metrics');
  for (const [label, value] of [
    ['เวลาที่พบกรน', `${number(item.summary.detected_snore_seconds / 60)} นาที`],
    ['ช่วงกรนยาวที่สุด', `${number(item.summary.longest_snore_event_seconds)} วินาที`],
    ['ความดังเฉลี่ย RMS / สูงสุดรายหน้าต่าง', `${number(item.summary.snore_mean_rms_dbfs)} / ${number(item.summary.snore_max_rms_dbfs)} dBFS`],
    ['ความดังมัธยฐาน / P95', `${number(item.summary.snore_median_rms_dbfs)} / ${number(item.summary.snore_p95_rms_dbfs)} dBFS`],
    ['ความถี่เด่น / จุดศูนย์กลางสเปกตรัม', `${number(p?.frequency_summary?.median_dominant_frequency_hz, 0)} / ${number(p?.frequency_summary?.median_spectral_centroid_hz, 0)} Hz`],
    ['Pitch/F0 มัธยฐาน', `${number(p?.frequency_summary?.median_pitch_hz, 0)} Hz`],
    ['คาบจาก Autocorrelation', p?.rhythm_autocorrelation?.dominant_period_seconds == null ? 'ยังไม่พบคาบที่ชัดเจน' : `${number(p.rhythm_autocorrelation.dominant_period_seconds)} วินาที · ความสัมพันธ์ ${number(p.rhythm_autocorrelation.autocorrelation_strength, 2)}`],
    ['กลับมากรนดังขึ้นหลังช่วงเงียบ', `${(p?.post_gap_loudness ?? []).filter(item => item.is_louder).length} ช่วง (เพิ่มอย่างน้อย ${p?.config.louder_return_threshold_db ?? 3} dB)`],
    ['ระยะเริ่มช่วงกรนเฉลี่ย', rhythm?.mean_start_interval_seconds == null ? 'ไม่มีช่วงต่อเนื่องให้เทียบ' : `${number(rhythm.mean_start_interval_seconds)} วินาที`],
    ['ความแปรผันของระยะเริ่มช่วง (CV)', rhythm?.interval_cv == null ? 'ต้องมีช่วงกรนอย่างน้อย 3 ช่วง' : number(rhythm.interval_cv, 3)],
  ]) { metrics.append(el('dt', label), el('dd', value)); }
  detail.append(metrics);
  if (p) detail.append(el('p', `ช่วงเงียบ: ไม่เกิน ${p.config.quiet_threshold_dbfs} dBFS ต่อเนื่องอย่างน้อย ${p.config.min_quiet_gap_seconds} วินาที ระหว่างช่วงกรน · ความถี่คำนวณเฉพาะหน้าต่างที่พบกรน`));
  const apnea = item.apnea_research;
  if (apnea) {
    const text = apnea.enabled ? `วิเคราะห์เสียงด้วยโมเดลวิจัยแล้ว · ${number(apnea.scored_seconds / 60)} นาทีที่มีข้อมูลพอให้ประเมิน · ดูช่วงให้ตรวจด้านล่าง`
      : apnea.status === 'not_trained' ? 'การวิเคราะห์ภาวะหยุดหายใจจากเสียง: ยังไม่ได้ฝึกโมเดล'
      : 'โมเดลการหายใจยังไม่ได้วิเคราะห์ไฟล์นี้';
    detail.append(el('p', text, 'apnea-result'));
  }
  const audio = el('audio'); audio.controls = true; audio.preload = 'metadata';
  if (item.sourceUrl) { audio.src = item.sourceUrl; detail.append(audio); }
  else detail.append(el('p', 'ไม่มีไฟล์เสียงสำหรับเล่นในผลนี้'));
  const seconds = item.summary.recording_seconds;
  const seek = time => {
    const target = Math.max(0, Math.min(seconds, time));
    if (item.sourceUrl) {
      if (audio.readyState > 0) audio.currentTime = target;
      else audio.addEventListener('loadedmetadata', () => { audio.currentTime = target; }, {once:true});
    }
    slider.value = target; position.textContent = clock(target);
  };
  const bins = timelineBins(item.timeline ?? [], seconds);
  for (const kind of ['snore', 'level']) {
    detail.append(el('h4', kind === 'snore' ? 'ช่วงเสียงกรน · สีเขียว' : 'ความดังสัมพัทธ์ (dBFS) · ช่วงต่ำสุด–สูงสุด'));
    const canvas = el('canvas', null, 'audio-track'); canvas.width = 1400; canvas.height = kind === 'snore' ? 60 : 140;
    canvas.setAttribute('aria-label', kind === 'snore' ? 'ภาพรวมช่วงเสียงกรน ใช้แถบเลื่อนด้านล่างเพื่อเลือกเวลา' : 'ความดังตั้งแต่ -90 ถึง 0 dBFS ค่าที่ต่ำกว่า -90 ถูกจำกัดเฉพาะการแสดงผล');
    const ctx = canvas.getContext('2d'); ctx.fillStyle = '#edf0e9'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    const width = canvas.width / (bins.length || 1);
    bins.forEach((bin, i) => {
      if (kind === 'snore' && bin.snore) { ctx.fillStyle = '#247f69'; ctx.fillRect(i * width, 0, Math.ceil(width), canvas.height); }
      if (kind === 'level' && bin.max !== null) {
        const y = value => Math.max(0, Math.min(1, -value / 90)) * canvas.height;
        ctx.fillStyle = '#3e6d88'; ctx.fillRect(i * width, y(bin.max), Math.ceil(width), Math.max(2, y(bin.min) - y(bin.max)));
      }
    });
    canvas.addEventListener('click', event => seek((event.clientX - canvas.getBoundingClientRect().left) / canvas.getBoundingClientRect().width * seconds));
    detail.append(canvas);
  }
  const soundEvents = soundReviewEntries(item);
  detail.append(el('h4','ประเภทเสียงตามเวลา · รุ่นทดลอง'));
  if(item.sound_review) {
    detail.append(el('p','สีแต่ละแถวคือช่วงที่ระบบคัดไว้ให้ตรวจฟัง อาจซ้อนทับกัน จำนวนช่วงไม่ใช่จำนวนครั้งที่ไอหรือจำนวนลมหายใจ เสียงพูดอาจมาจากผู้ตื่นอยู่หรือคนอื่น'));
    const labels={snore:'กรน',cough:'เสียงคล้ายไอ',speech:'เสียงพูด',breathing:'เสียงคล้ายหายใจ'};
    const colors={snore:'#247f69',cough:'#a65b28',speech:'#7156a5',breathing:'#287c9b'};
    for(const kind of Object.keys(labels)) {
      const category=item.sound_review.categories.find(row=>row.sound_type===kind);
      detail.append(el('p',`${labels[kind]} · ${number(category?.detected_seconds)} วินาที · ${category?.review_segment_count ?? 0} ช่วงให้ตรวจ`, 'sound-track-label'));
      const canvas=el('canvas',null,'sound-track');canvas.width=1400;canvas.height=32;
      canvas.setAttribute('role','img');canvas.setAttribute('aria-label',`${labels[kind]}ตามเวลา ใช้แถบเลื่อนเลือกเวลา`);
      const ctx=canvas.getContext('2d');ctx.fillStyle='#edf0e9';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.fillStyle=colors[kind];
      for(const event of soundEvents.filter(row=>row.event_type===kind)) ctx.fillRect(event.start_seconds/seconds*canvas.width,0,Math.max(1,event.duration_seconds/seconds*canvas.width),canvas.height);
      canvas.addEventListener('click',event=>seek((event.clientX-canvas.getBoundingClientRect().left)/canvas.getBoundingClientRect().width*seconds));
      detail.append(canvas);
    }
  } else detail.append(el('p','ผลนี้ยังไม่มีการคัดประเภทเสียงเพิ่มเติม วิเคราะห์ไฟล์ใหม่เพื่อรับข้อมูล หรือใช้ตัวอย่างจำลอง'));
  detail.append(el('h4','อัตราหายใจจากเสียง · รุ่นทดลอง'));
  const breathing=item.breathing_rate;
  if(breathing) {
    detail.append(el('p',`มัธยฐาน ${number(breathing.median_breaths_per_minute)} ครั้ง/นาที · ประเมินได้ ${number(breathing.estimated_seconds/60)} นาที (${number(breathing.coverage_percent)}% ของเวลาบันทึก) · ช่องว่างหมายถึงประเมินไม่ได้ ไม่ใช่หยุดหายใจ`));
    detail.append(el('p','ประมาณรอบความดังเฉพาะช่วงที่มีเสียงคล้ายหายใจและจังหวะชัด ยังไม่ผ่านการตรวจสอบอัตราหายใจจริง เสียงเครื่องจักรเป็นจังหวะอาจทำให้ผลผิดได้'));
    const points=breathingPlotPoints(breathing);
    if(points.some(point=>point.y!==null)) {
      const canvas=el('canvas',null,'measurement-track');canvas.width=1200;canvas.height=180;
      canvas.setAttribute('role','img');canvas.setAttribute('aria-label','อัตราหายใจประมาณ 6 ถึง 30 ครั้งต่อนาที ช่องว่างคือช่วงประเมินไม่ได้');
      window.SanorAudioCharts.drawSeries(canvas,points,seconds,6,30);
      canvas.addEventListener('click',event=>seek((event.clientX-canvas.getBoundingClientRect().left)/canvas.getBoundingClientRect().width*seconds));
      detail.append(el('p','แกนตั้ง 6–30 ครั้ง/นาที · แกนนอนเวลาในไฟล์'),canvas);
    }
    const review=el('details',null,'frequency-details');review.append(el('summary','ดูผลอัตราหายใจราย 30 วินาทีและเหตุผลที่ไม่มีค่า'));
    const list=el('div',null,'event-list'),nav=el('div',null,'toolbar');let page=0;
    const windows=breathing.windows ?? [];
    function showWindows() {
      list.replaceChildren();nav.replaceChildren();
      for(const row of windows.slice(page*20,(page+1)*20)) list.append(button(`${clock(row.start_seconds)}–${clock(row.start_seconds+row.duration_seconds)} · ${number(row.breaths_per_minute)} ครั้ง/นาที · ${breathingStatusText(row.status)}`,()=>seek(row.start_seconds),'event-button'));
      if(!windows.length)list.append(el('p','ยังไม่มีข้อมูลหน้าต่างเสียง'));
      const back=button('ก่อนหน้า',()=>{page--;showWindows();});back.disabled=page===0;
      const next=button('ถัดไป',()=>{page++;showWindows();});next.disabled=(page+1)*20>=windows.length;
      nav.append(back,el('span',`${page+1} / ${Math.max(1,Math.ceil(windows.length/20))}`),next);
    }
    showWindows();review.append(list,nav,button('ดาวน์โหลดอัตราหายใจ CSV',()=>download(`${item.name}-breathing.csv`,'\uFEFF'+toCsv(windows),'text/csv;charset=utf-8')));detail.append(review);
  } else detail.append(el('p','ผลนี้ยังไม่มีการประมาณอัตราหายใจ วิเคราะห์ไฟล์ใหม่เพื่อรับข้อมูล'));
  const charts = window.SanorAudioCharts;
  const extra = el('details', null, 'frequency-details');
  extra.append(el('summary', 'ดู Spectrogram, Pitch และจังหวะเสียง'));
  const spec = p?.spectrogram;
  if (spec?.status === 'available') {
    extra.append(el('h4', 'Spectrogram · ความถี่ตามเวลา'));
    const canvas = el('canvas', null, 'spectrogram-track');canvas.width=1200;canvas.height=300;
    canvas.setAttribute('role','img');canvas.setAttribute('aria-label','Spectrogram ความถี่สูงอยู่ด้านบน กดเพื่อเลือกเวลา หรือใช้แถบเลื่อน');
    charts.drawSpectrogram(canvas,spec);
    canvas.addEventListener('click',event=>seek((event.clientX-canvas.getBoundingClientRect().left)/canvas.getBoundingClientRect().width*seconds));
    const topHz = spec.frequencies_hz[spec.frequencies_hz.length-1];
    extra.append(el('p', `ด้านบน ${number(topHz/1000,1)} kHz · ด้านล่าง 0 Hz · สีเข้ม −110 ถึงสีอ่อน −20 dBFS/Hz · กดกราฟเพื่อเลือกเวลา`),canvas);
    const specAxis=el('div',null,'axis');specAxis.append(el('span','00:00:00'),el('span',clock(seconds)));extra.append(specAxis);
  } else extra.append(el('p','Spectrogram ไม่ได้รวมอยู่ในผลนี้ หรือไฟล์สั้นเกินไป'));
  const pitchPoints = charts.sampledPitch(item.timeline ?? [],seconds);
  extra.append(el('h4','Pitch/F0 · ค่าประมาณเฉพาะเสียงที่มีคาบชัดเจน'));
  if(pitchPoints.some(point=>point.y!==null)) {
    const canvas=el('canvas',null,'measurement-track');canvas.width=1200;canvas.height=180;
    canvas.setAttribute('role','img');canvas.setAttribute('aria-label','Pitch ตามเวลา ตั้งแต่ 50 ถึง 1000 Hz ช่องว่างหมายถึงไม่มีค่าประมาณที่เชื่อถือได้');
    charts.drawSeries(canvas,pitchPoints,seconds,50,1000);
    canvas.addEventListener('click',event=>seek((event.clientX-canvas.getBoundingClientRect().left)/canvas.getBoundingClientRect().width*seconds));
    extra.append(el('p','แกนตั้ง 50–1000 Hz · แกนนอนคือเวลาในไฟล์ · ช่องว่างหมายถึงไม่มีค่า Pitch'),canvas);
  } else extra.append(el('p','ไม่มีหน้าต่างเสียงที่ให้ค่า Pitch ชัดเจน'));
  const ac=p?.rhythm_autocorrelation;
  extra.append(el('h4','Autocorrelation · ความซ้ำของรูปแบบความดังเสียงกรน'));
  if(ac?.lags_seconds?.length) {
    const canvas=el('canvas',null,'measurement-track');canvas.width=1200;canvas.height=180;
    canvas.setAttribute('role','img');canvas.setAttribute('aria-label','Autocorrelation แกนนอนคือระยะเลื่อนเวลา แกนตั้งคือความสัมพันธ์ตั้งแต่ -1 ถึง 1');
    const points=ac.lags_seconds.map((x,i)=>({x,y:ac.correlation[i]}));
    charts.drawSeries(canvas,points,ac.lags_seconds[ac.lags_seconds.length-1],-1,1);
    extra.append(el('p',`แกนนอน: ระยะเลื่อน 0–${number(ac.lags_seconds[ac.lags_seconds.length-1])} วินาที · แกนตั้ง: ความสัมพันธ์ −1 ถึง 1`),canvas);
  } else extra.append(el('p','เสียงสั้นเกินไปหรือไม่มีความเปลี่ยนแปลงพอสำหรับ Autocorrelation'));
  const localRhythm=p?.rhythm_timeline ?? [];
  extra.append(el('h4','คาบเสียงกรนที่เปลี่ยนตามเวลา'));
  if(localRhythm.some(row=>row.dominant_period_seconds!==null)) {
    const canvas=el('canvas',null,'measurement-track');canvas.width=1200;canvas.height=180;
    canvas.setAttribute('role','img');canvas.setAttribute('aria-label','คาบเสียงกรนตามเวลา ประเมินครั้งละ 60 วินาที เลื่อนครั้งละ 30 วินาที');
    const points=localRhythm.map(row=>({x:row.start_seconds+row.duration_seconds/2,y:row.dominant_period_seconds}));
    charts.drawSeries(canvas,points,seconds,1,15);
    extra.append(el('p','แกนตั้ง: คาบ 1–15 วินาที · แกนนอน: เวลาในไฟล์ · หน้าต่าง 60 วินาที เลื่อนครั้งละ 30 วินาที'),canvas);
  } else extra.append(el('p','ยังไม่มีช่วงที่ให้ค่าคาบเสียงชัดเจน'));
  detail.append(extra);
  const axis = el('div', null, 'axis'); axis.append(el('span', '00:00:00'), el('span', clock(seconds))); detail.append(axis);
  const sliderLabel = el('label', 'เลือกเวลาในไฟล์', 'seek-label');
  const slider = el('input'); slider.type = 'range'; slider.min = 0; slider.max = seconds; slider.step = 0.1; slider.value = 0;
  const position = el('output', '00:00:00'); sliderLabel.append(slider, position); detail.append(sliderLabel);
  slider.addEventListener('input', () => seek(Number(slider.value)));
  audio.addEventListener('timeupdate', () => { slider.value = audio.currentTime; position.textContent = clock(audio.currentTime); });
  const exports = el('div', null, 'toolbar');
  exports.append(button('ดาวน์โหลด timeline CSV', () => download(`${item.name}-timeline.csv`, '\uFEFF' + toCsv(item.timeline ?? []), 'text/csv;charset=utf-8')),
    button('ดาวน์โหลดผล JSON', () => download(`${item.name}-analysis.json`, JSON.stringify(exportable(item), null, 2), 'application/json')));
  detail.append(exports);
  const entries = [...soundEvents, ...(p?.quiet_gaps ?? []).map(event => ({...event,event_type:'quiet',kind:'ช่วงเงียบ'})), ...(p?.post_gap_loudness ?? []).filter(item => item.is_louder).map(event => ({...event,event_type:'return',kind:`กลับมากรนดังขึ้น +${number(event.rise_db)} dB`})), ...(apnea?.review_segments ?? []).map(event => ({...event,event_type:'apnea',duration_seconds:event.end_seconds-event.start_seconds,kind:'ช่วงให้ตรวจ · โมเดลการหายใจ'}))].sort((a,b) => a.start_seconds - b.start_seconds);
  const filterLabel=el('label','ประเภทช่วงเสียง '),eventFilter=el('select');
  for(const [value,label] of [['','ทั้งหมด'],['snore','กรน'],['cough','เสียงคล้ายไอ'],['speech','เสียงพูด'],['breathing','เสียงคล้ายหายใจ'],['quiet','ช่วงเงียบ'],['return','กลับมาดังขึ้น'],['apnea','ช่วงให้ตรวจจากโมเดลวิจัย']])eventFilter.add(new Option(label,value));
  filterLabel.append(eventFilter);
  const list = el('div', null, 'event-list'); const navigation = el('div', null, 'toolbar');
  let page = 0;
  function renderEvents() {
    list.replaceChildren(); navigation.replaceChildren();
    const filtered=entries.filter(event=>!eventFilter.value || event.event_type===eventFilter.value);
    if (!filtered.length) { list.append(el('p', 'ไม่มีช่วงเสียงที่ตรงตัวกรอง')); return; }
    for (const event of filtered.slice(page * 30, (page + 1) * 30)) {
      const control = button(`${event.kind} · ${clock(event.start_seconds)}–${clock(event.end_seconds)} · ${number(event.duration_seconds)} วินาที`, () => seek(event.start_seconds), 'event-button');
      list.append(control);
    }
    const back = button('ก่อนหน้า', () => { page--; renderEvents(); }); back.disabled = page === 0;
    const next = button('ถัดไป', () => { page++; renderEvents(); }); next.disabled = (page + 1) * 30 >= filtered.length;
    navigation.append(back, el('span', `${page + 1} / ${Math.ceil(filtered.length / 30)} · ${filtered.length} ช่วง`), next);
  }
  eventFilter.addEventListener('change',()=>{page=0;renderEvents();});
  detail.append(el('h4', 'เลือกช่วงเพื่อฟัง'), filterLabel, list, navigation); renderEvents();
}
function renderSessions() {
  const box = document.querySelector('#sessions'); box.replaceChildren();
  const sessions = new Map();
  for (const item of recordings) if (item.session_id && item.part != null) {
    if (!sessions.has(item.session_id)) sessions.set(item.session_id, []);
    sessions.get(item.session_id).push(item);
  }
  for (const [id, parts] of sessions) {
    if (parts.length < 2) continue;
    const action = button(`รวมเซสชัน ${parts.length} ไฟล์ · ${clock(parts.reduce((sum, p) => sum + p.summary.recording_seconds, 0))}`, async () => {
      action.disabled = true;
      try {
        const response = await fetch('/api/session-summary', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(parts.map(exportable))});
        const data = await response.json(); if (!response.ok) throw new Error(data.error);
        const total = data.summary;
        const text = el('p', `รวมเวลาที่บันทึก ${number(total.recording_seconds / 60)} นาที · พบกรน ${number(total.snore_percent_of_recording)}% · ${total.snore_event_count} ช่วง · ${data.session_continuous ? 'ข้อมูลต่อเนื่อง' : 'ไม่นับระยะข้ามรอยต่อที่ไม่ได้ยืนยัน'}`);
        box.append(text, button('ดาวน์โหลดผลเซสชัน JSON', () => download(`sanor-session-${id}.json`, JSON.stringify(data, null, 2), 'application/json')));
      } catch (error) { status.textContent = `รวมเซสชันไม่ได้: ${error.message}`; action.disabled = false; }
    }); box.append(action);
  }
}
window.addEventListener('pagehide', event => { if (event.persisted) return; for (const item of recordings) if (item.sourceUrl) URL.revokeObjectURL(item.sourceUrl); });
// Record independent 30-minute files so a browser interruption loses at most one part.
const recordStart = document.querySelector('#record-start');
const recordStop = document.querySelector('#record-stop');
const recordStatus = document.querySelector('#record-status');
const recordTime = document.querySelector('#record-time');
const recordLight = document.querySelector('#record-light');
const PART_MS = 30 * 60 * 1000;
let microphone, recorder, destination, night, partTimer, clockTimer, wakeLock;
let analysisQueue = Promise.resolve();

recordStart.addEventListener('click', startNight);
recordStop.addEventListener('click', stopNight);
window.addEventListener('beforeunload', event => {
  if (night?.active) { event.preventDefault(); event.returnValue = ''; }
});
document.addEventListener('visibilitychange', () => {
  if (night?.active && document.hidden) recordStatus.textContent = 'ยังอัดอยู่ แต่เบราว์เซอร์อาจหยุดเมื่อเครื่องพัก กรุณาเปิดคอมพิวเตอร์ไว้';
});

async function startNight() {
  recordStatus.classList.remove('error');
  if (!window.MediaRecorder || !navigator.mediaDevices?.getUserMedia || !window.showDirectoryPicker) {
    showRecordError('ต้องใช้ Chrome บนคอมพิวเตอร์และเปิดเว็บผ่าน localhost เพื่ออัดและบันทึกไฟล์');
    return;
  }
  recordStart.disabled = true;
  try {
    destination = await window.showDirectoryPicker({id: 'sanor-recordings', mode: 'readwrite'});
    microphone = await navigator.mediaDevices.getUserMedia({audio: {
      channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: false,
    }});
    night = {id:crypto.randomUUID(), analysisHeaders:settingsHeaders(), active: true, started: Date.now(), part: 0, folder: destination};
    microphone.getAudioTracks().forEach(track => track.addEventListener('ended', () => {
      if (night?.active) { showRecordError('ไมโครโฟนหยุดทำงาน การอัดสิ้นสุดแล้ว'); stopNight(); }
    }));
    recordStop.disabled = false;
    recordLight.classList.add('on');
    clockTimer = setInterval(updateClock, 1000);
    updateClock();
    startPart();
    navigator.wakeLock?.request('screen').then(lock => { wakeLock = lock; }).catch(() => {});
    recordStatus.textContent = 'กำลังอัด · จะบันทึก WAV ไฟล์ใหม่ทุก 30 นาที';
  } catch (error) {
    microphone?.getTracks().forEach(track => track.stop());
    microphone = null;
    night = null;
    clearInterval(clockTimer);
    clearTimeout(partTimer);
    recordStop.disabled = true;
    recordLight.classList.remove('on');
    recordStart.disabled = false;
    showRecordError(`เริ่มอัดไม่ได้: ${error.message}`);
  }
}

function startPart() {
  const supported = ['audio/webm;codecs=opus', 'audio/mp4'].find(type => MediaRecorder.isTypeSupported(type));
  recorder = new MediaRecorder(microphone, supported ? {mimeType: supported} : undefined);
  const parts = [];
  const started = Date.now();
  recorder.ondataavailable = event => { if (event.data.size) parts.push(event.data); };
  recorder.onerror = event => { showRecordError(`อัดเสียงขัดข้อง: ${event.error?.message || 'ไม่ทราบสาเหตุ'}`); stopNight(); };
  recorder.onstop = () => {
    clearTimeout(partTimer);
    const blob = new Blob(parts, {type: recorder.mimeType});
    const session = night;
    const part = ++session.part;
    if (session.active) startPart();
    else microphone?.getTracks().forEach(track => track.stop());
    if (blob.size) {
      analysisQueue = analysisQueue.then(() => saveAndAnalyze(blob, started, part, session)).catch(error => showRecordError(`ไฟล์ที่ ${part}: ${error.message}`));
    }
    if (!session.active) analysisQueue.finally(() => { recordStart.disabled = false; });
  };
  recorder.start(1000);
  partTimer = setTimeout(() => { if (recorder.state === 'recording') recorder.stop(); }, PART_MS);
}

function stopNight() {
  if (!night?.active) return;
  night.active = false;
  clearInterval(clockTimer);
  clearTimeout(partTimer);
  recordStart.disabled = true;
  recordStop.disabled = true;
  recordLight.classList.remove('on');
  wakeLock?.release().catch(() => {});
  if (recorder?.state === 'recording') recorder.stop();
  else microphone?.getTracks().forEach(track => track.stop());
  recordStatus.textContent = 'หยุดอัดแล้ว · กำลังบันทึกและวิเคราะห์ไฟล์สุดท้าย';
}

function updateClock() {
  const seconds = Math.floor((Date.now() - night.started) / 1000);
  recordTime.textContent = [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60]
    .map(value => String(value).padStart(2, '0')).join(':');
}

async function saveAndAnalyze(blob, started, part, session) {
  recordStatus.textContent = `กำลังแปลงและบันทึกไฟล์ที่ ${part} ...`;
  const context = new AudioContext();
  let decoded;
  try { decoded = await context.decodeAudioData(await blob.arrayBuffer()); }
  finally { await context.close(); }
  const wav = encodeWav16k(decoded);
  const name = `sanor_${new Date(started).toISOString().replace(/[:.]/g, '-')}_part${String(part).padStart(3, '0')}.wav`;
  try {
    const file = await session.folder.getFileHandle(name, {create: true});
    const writer = await file.createWritable();
    await writer.write(wav);
    await writer.close();
  } catch (error) {
    const link = document.createElement('a');
    const url = URL.createObjectURL(wav);
    link.href = url; link.download = name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    showRecordError(`บันทึกลงโฟลเดอร์ไม่ได้ ดาวน์โหลด ${name} แทน: ${error.message}`);
  }
  recordStatus.textContent = `บันทึก ${name} แล้ว · กำลังวิเคราะห์...`;
  const response = await fetch('/api/analyze', {method: 'POST', headers: session.analysisHeaders, body: wav});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'วิเคราะห์เสียงไม่ได้');
  window.addSanorResult(name, data, wav, {session_id:session.id, part, contiguous_with_previous:false});
  recordStatus.textContent = session.active ? `อัดต่อเนื่อง · วิเคราะห์ไฟล์ที่ ${part} แล้ว` : `อัดเสร็จ · วิเคราะห์ไฟล์ที่ ${part} แล้ว`;
}

function encodeWav16k(buffer) {
  const length = Math.floor(buffer.duration * 16000);
  const bytes = new ArrayBuffer(44 + length * 2);
  const view = new DataView(bytes);
  const writeText = (offset, value) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
  writeText(0, 'RIFF'); view.setUint32(4, bytes.byteLength - 8, true); writeText(8, 'WAVE');
  writeText(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); writeText(36, 'data');
  view.setUint32(40, length * 2, true);
  const channels = Array.from({length: buffer.numberOfChannels}, (_, i) => buffer.getChannelData(i));
  for (let i = 0; i < length; i++) {
    const position = i * buffer.sampleRate / 16000;
    const left = Math.floor(position), right = Math.min(left + 1, buffer.length - 1), fraction = position - left;
    let sample = 0;
    for (const channel of channels) sample += channel[left] * (1 - fraction) + channel[right] * fraction;
    sample = Math.max(-1, Math.min(1, sample / channels.length));
    view.setInt16(44 + i * 2, sample < 0 ? sample * 32768 : sample * 32767, true);
  }
  return new Blob([bytes], {type: 'audio/wav'});
}

function showRecordError(message) {
  recordStatus.textContent = message;
  recordStatus.classList.add('error');
}
