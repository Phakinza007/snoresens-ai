const pptxgen = require('pptxgenjs');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const sharp = require('sharp');
const lu = require('react-icons/lu');
const fs = require('fs');
const { applyTheme } = require(process.env.APPLY_THEME_JS || './apply_theme.js');

const M = JSON.parse(fs.readFileSync(require('path').join(__dirname, '../../../results/model-comparison/metrics.json'), 'utf8'));
const OUT = process.argv[2] || 'SnoresensAI-Final.pptx';

const THEME = {
  name: 'Snoresens Night',
  headFontFace: 'Tahoma', bodyFontFace: 'Tahoma',
  colors: {
    dk1: '15233F', lt1: 'FFFFFF', dk2: '1B2E5A', lt2: 'EEF2FB',
    accent1: '3157F5', accent2: 'F2A93B', accent3: '2F9A8B', accent4: 'C7445A', accent5: '8EA6D8', accent6: '6B7A99',
    hlink: '3157F5', folHlink: '6B4FD8',
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5
pres.title = 'Snoresens AI — INT182 Final';
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ---------- layouts ----------
pres.defineSlideMaster({
  title: 'DARK_TITLE', background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.8, y: 2.2, w: 8.6, h: 1.6, fontSize: 44, bold: true, color: C.background1, valign: 'bottom', align: 'left', margin: 0 }, text: '' } },
    { placeholder: { options: { name: 'body', type: 'body', x: 0.8, y: 3.95, w: 8.6, h: 1.4, fontSize: 18, color: C.accent5, valign: 'top', align: 'left', margin: 0 }, text: '' } },
  ],
});
pres.defineSlideMaster({
  title: 'CONTENT', background: { color: C.background1 },
  margin: [0.5, 0.6, 0.7, 0.6],
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.4, w: 12.1, h: 0.8, fontSize: 30, bold: true, color: C.text2, valign: 'middle', align: 'left', margin: 0 }, text: '' } },
    { text: { text: 'Snoresens AI · INT182 Final', options: { x: 0.6, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: C.accent6, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, align: 'right' },
});

// ---------- helpers ----------
const iconCache = {};
async function iconPng(name, color) {
  const key = name + color;
  if (!iconCache[key]) {
    const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(lu[name], { color: '#' + color, size: 256, strokeWidth: 2 }));
    iconCache[key] = 'image/png;base64,' + (await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer()).toString('base64');
  }
  return iconCache[key];
}
async function iconCircle(slide, name, x, y, d, bg, fg, objectName) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { type: 'none' }, objectName: objectName + ' circle' });
  const p = d * 0.25;
  slide.addImage({ data: await iconPng(name, fg), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, altText: objectName, objectName: objectName + ' icon' });
}
function card(slide, x, y, w, h, fill, objectName) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { type: 'none' }, objectName });
}
function text(slide, t, o) { slide.addText(t, { isTextBox: true, margin: 0, valign: 'top', color: C.text1, fontSize: 14, ...o }); }
const pct = v => (v * 100).toFixed(2) + '%';
const content = (title, section) => { const s = pres.addSlide({ masterName: 'CONTENT', sectionTitle: section }); s.addText(title, { placeholder: 'title' }); return s; };

(async () => {
  // ===== 1. Title =====
  pres.addSection({ title: 'เปิด' });
  let s = pres.addSlide({ masterName: 'DARK_TITLE', sectionTitle: 'เปิด' });
  s.addText('Snoresens AI', { placeholder: 'title' });
  s.addText('ตรวจจับเสียงกรนจากเสียงในห้องนอนด้วย AI\nพร้อมรายงานย้อนฟัง และเช็กลิสต์อาการตอนเช้า', { placeholder: 'body' });
  s.addShape(pres.shapes.OVAL, { x: 9.6, y: 1.5, w: 2.9, h: 2.9, fill: { color: C.accent2 }, line: { type: 'none' }, objectName: 'moon' });
  s.addShape(pres.shapes.OVAL, { x: 10.5, y: 1.15, w: 2.6, h: 2.6, fill: { color: C.text2 }, line: { type: 'none' }, objectName: 'moon shadow' });
  text(s, 'INT182 · Final Project · 17 พฤศจิกายน 2569', { x: 0.8, y: 6.3, w: 8, h: 0.4, fontSize: 14, color: C.accent5 });
  s.addNotes('แนะนำทีมและโปรเจกต์: เว็บที่ฟังเสียงตอนนอน แล้วบอกว่าช่วงไหนกรน ใช้ AI รันบนเครื่องผู้ใช้ ไม่ส่งเสียงขึ้นเซิร์ฟเวอร์');

  // ===== 2. Problem =====
  s = content('ปัญหาและคำถามที่ต้องการตอบ', 'เปิด');
  const qs = [
    ['LuMoon', 'คนกรนส่วนใหญ่ไม่รู้ตัว', 'ไม่รู้ว่ากรนบ่อยแค่ไหน ช่วงไหน\nและนานเท่าไร ต้องพึ่งคนข้าง ๆ บอก'],
    ['LuStethoscope', 'การตรวจการนอนหลับเข้าถึงยาก', 'Sleep test ต้องไปโรงพยาบาล\nค่าใช้จ่ายสูง หลายคนจึงไม่เริ่มตรวจ'],
    ['LuTarget', 'คำถามของโปรเจกต์', 'ใช้เสียงจากไมค์มือถือหรือคอม\nแยก “กรน / ไม่กรน” ได้แม่นแค่ไหน\nและบอกได้ไหมว่าควรพบแพทย์'],
  ];
  for (let i = 0; i < qs.length; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.6, 3.8, 4.6, i === 2 ? HEX.dk2 : HEX.lt2, 'problem card ' + (i + 1));
    await iconCircle(s, qs[i][0], x + 0.35, 1.95, 0.9, i === 2 ? HEX.accent2 : HEX.lt1, i === 2 ? HEX.dk2 : HEX.accent1, 'problem ' + (i + 1));
    text(s, qs[i][1], { x: x + 0.35, y: 3.1, w: 3.1, h: 0.9, fontSize: 20, bold: true, color: i === 2 ? C.background1 : C.text2 });
    text(s, qs[i][2], { x: x + 0.35, y: 4.05, w: 3.1, h: 2.0, fontSize: 15, color: i === 2 ? C.background2 : C.text1 });
  }
  s.addNotes('เล่าปัญหา: คนกรนไม่รู้ตัว การตรวจในโรงพยาบาลเข้าถึงยาก จึงอยากมีเครื่องมือคัดกรองเบื้องต้นจากเสียง คำถามหลักคือ AI แยกกรนได้แม่นแค่ไหน และตอบได้ไหมว่าควรไปพบแพทย์');

  // ===== 3. Pipeline =====
  pres.addSection({ title: 'AI pipeline' });
  s = content('AI / DS pipeline: จากเสียงสู่รายงาน', 'AI pipeline');
  const steps = [
    ['LuMic', '1. รับเสียง', 'อัดในเว็บ\nหรืออัปโหลด WAV\nแบ่งไฟล์ทุก 30 นาที'],
    ['LuWaves', '2. เตรียมเสียง', 'mono 16 kHz\nหน้าต่าง 0.975 วิ\nเลื่อนทุก 0.1 วิ'],
    ['LuBrain', '3. YAMNet', 'โมเดลของ Google\nฝึกจาก AudioSet\n(ตรึงน้ำหนัก)\n→ 521 ค่า'],
    ['LuCpu', '4. Classifier', 'Dense head\nที่ทีมฝึกเอง\n→ ความน่าจะ\nเป็นกรน'],
    ['LuFilter', '5. ตัดสินผล', 'threshold 0.44\n+ activity gate\nตัดช่วงเงียบ'],
    ['LuChartColumn', '6. รายงาน', 'รวมเป็นช่วงกรน\ntimeline\nย้อนฟัง · export'],
  ];
  for (let i = 0; i < steps.length; i++) {
    const x = 0.6 + i * 2.1;
    card(s, x, 1.7, 1.85, 3.6, i === 2 || i === 3 ? HEX.dk2 : HEX.lt2, 'step card ' + (i + 1));
    const dark = i === 2 || i === 3;
    await iconCircle(s, steps[i][0], x + 0.5, 1.95, 0.85, dark ? HEX.accent2 : HEX.lt1, dark ? HEX.dk2 : HEX.accent1, 'step ' + (i + 1));
    text(s, steps[i][1], { x: x + 0.15, y: 3.0, w: 1.55, h: 0.5, fontSize: 16, bold: true, align: 'center', color: dark ? C.background1 : C.text2 });
    text(s, steps[i][2], { x: x + 0.15, y: 3.55, w: 1.55, h: 1.7, fontSize: 12, align: 'center', color: dark ? C.background2 : C.text1 });
  }
  card(s, 0.6, 5.6, 12.1, 1.15, HEX.lt2, 'pipeline note');
  await iconCircle(s, 'LuShieldCheck', 0.85, 5.78, 0.8, HEX.lt1, HEX.accent3, 'privacy');
  text(s, [{ text: 'ประมวลผลบนอุปกรณ์ผู้ใช้: ', options: { bold: true, color: C.text2 } }, { text: 'เว็บออนไลน์รันโมเดล TFLite ในเบราว์เซอร์ (≈ 4.3 MB) ไม่อัปโหลดเสียง\nหลังได้รายงาน ผู้ใช้ทำเช็กลิสต์อาการตอนเช้าเพื่อคัดกรองเบื้องต้น' }], { x: 1.85, y: 5.82, w: 10.6, h: 0.8, fontSize: 15, valign: 'middle' });
  s.addNotes('ไล่ pipeline ซ้ายไปขวา: กล่องสีเข้มคือส่วน AI โมเดล YAMNet ใช้สกัดคุณลักษณะเสียง 521 ค่า แล้ว Dense head ที่ทีมฝึกเองตัดสินว่ากรนไหม ตรวจทุก 0.1 วินาที แล้วรวมเป็นช่วงกรนในรายงาน');

  // ===== 4. Datasets =====
  pres.addSection({ title: 'ข้อมูล' });
  s = content('Dataset มาจากไหน', 'ข้อมูล');
  const ds = [
    ['LuDatabase', 'Kaggle Snoring Dataset (v1)', 'Tareq Khan, 2019 · ใช้เป็นข้อมูลหลัก', 'กรน 500 คลิป (เด็ก ผู้ใหญ่ชาย/หญิง) + ไม่กรน 500 คลิป จาก 10 หมวดเสียงรอบเตียง เช่น ทารกร้อง นาฬิกา ประตู ฝน ทีวี คนคุย · คลิปละ 1 วินาที · ลบเสียงซ้ำ 9 → 991 คลิป'],
    ['LuWind', 'Coswara — เสียงหายใจ', 'IISc Bangalore · ตัวอย่างลบเพิ่ม (รุ่น 2)', 'เสียงหายใจ 58 คลิปจากคนละกลุ่มกัน ใช้สอนโมเดลว่า “หายใจ ≠ กรน” หลังพบว่ารุ่นแรกนับหายใจเป็นกรน 6/14 คลิป'],
    ['LuFlaskConical', 'Coswara — เสียงไอ', 'งานทดลองแยกจากงานกรน', '186 ไฟล์ / 32 คน แยกคนระหว่างชุดฝึกและทดสอบ\nใช้ฝึกตัวคัดช่วงเสียงไอ'],
    ['LuBrain', 'YAMNet (Google, AudioSet)', 'โมเดลสำเร็จรูป ไม่ได้ฝึกใหม่', 'ฝึกจาก AudioSet 2 ล้านคลิป 521 หมวดเสียง ทีมใช้เป็นตัวสกัด feature แล้วฝึกเฉพาะส่วนตัดสินผล'],
  ];
  for (let i = 0; i < ds.length; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 1.55 + Math.floor(i / 2) * 2.7;
    card(s, x, y, 5.95, 2.5, HEX.lt2, 'dataset card ' + (i + 1));
    await iconCircle(s, ds[i][0], x + 0.3, y + 0.3, 0.75, i === 0 ? HEX.accent1 : HEX.lt1, i === 0 ? HEX.lt1 : HEX.accent1, 'dataset ' + (i + 1));
    text(s, ds[i][1], { x: x + 1.25, y: y + 0.28, w: 4.5, h: 0.45, fontSize: 18, bold: true, color: C.text2 });
    text(s, ds[i][2], { x: x + 1.25, y: y + 0.72, w: 4.5, h: 0.35, fontSize: 12, color: C.accent6 });
    text(s, ds[i][3], { x: x + 0.3, y: y + 1.2, w: 5.4, h: 1.2, fontSize: 13 });
  }
  s.addNotes('แหล่งข้อมูลหลักคือ Kaggle Snoring Dataset ของ Tareq Khan มีกรนกับไม่กรนอย่างละ 500 คลิป ไม่กรนเป็นเสียงรอบเตียง 10 หมวด รุ่น 2 เพิ่มเสียงหายใจจาก Coswara เพราะรุ่นแรกนับหายใจเป็นกรน ส่วน YAMNet เป็นโมเดลสำเร็จรูปของ Google ที่ใช้สกัด feature');

  // ===== 5. Train/Val/Test =====
  s = content('Train / Validation / Test แยกตาม class', 'ข้อมูล');
  s.addImage({ path: 'chart-split.png', x: 0.6, y: 1.45, w: 7.2, h: 5.3, altText: 'กราฟแท่งซ้อน จำนวนคลิปกรนและไม่กรนในชุด Train 725, Validation 161, Test 163', objectName: 'split chart' });
  card(s, 8.1, 1.45, 4.6, 2.55, HEX.lt2, 'split rules');
  text(s, 'วิธีแบ่งข้อมูล', { x: 8.4, y: 1.65, w: 4.0, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
  text(s, [
    { text: 'Kaggle แบ่ง 70/15/15 รักษาสัดส่วน class (seed 42)', options: { bullet: true, breakLine: true } },
    { text: 'Coswara แยกตามคน ไม่มีคนเดียวกันข้ามชุด', options: { bullet: true, breakLine: true } },
    { text: 'ตรวจ SHA-256 ทุกคลิป: ไม่มีคลิปซ้ำข้ามชุด', options: { bullet: true, breakLine: true } },
    { text: 'เลือก threshold จาก validation เท่านั้น', options: { bullet: true } },
  ], { x: 8.4, y: 2.1, w: 4.1, h: 1.85, fontSize: 13, paraSpaceAfter: 4 });
  s.addTable([
    [{ text: 'งานไอ (ทดลอง)', options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 } } }, { text: 'ไม่ไอ', options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, align: 'center' } }, { text: 'ไอ', options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, align: 'center' } }],
    ['Train (18 คน)', { text: '68', options: { align: 'center' } }, { text: '36', options: { align: 'center' } }],
    ['Validation (7 คน)', { text: '26', options: { align: 'center' } }, { text: '14', options: { align: 'center' } }],
    ['Test (7 คน)', { text: '28', options: { align: 'center' } }, { text: '14', options: { align: 'center' } }],
  ], { x: 8.1, y: 4.25, w: 4.6, colW: [2.4, 1.1, 1.1], fontSize: 13, color: HEX.dk1, fontFace: 'Tahoma', border: { type: 'solid', pt: 0.75, color: 'DDE3EE' }, rowH: 0.42, objectName: 'cough split table' });
  text(s, 'รวมงานกรน: Train 725 · Validation 161 · Test 163', { x: 8.1, y: 6.15, w: 4.6, h: 0.5, fontSize: 13, bold: true, color: C.accent1 });
  s.addNotes('ชุดฝึกงานกรนคือ Kaggle 693 คลิป (กรน 350 ไม่กรน 343) บวกเสียงหายใจ 32 คลิป รวม 725 ส่วน validation ใช้เลือกค่า threshold และ hyperparameter ส่วน test ใช้วัดผลครั้งเดียวตอนท้าย');

  // ===== 6. Training set =====
  s = content('Training set คืออะไร', 'ข้อมูล');
  const stats = [['725', 'คลิปในชุดฝึก', 'Kaggle 693 + หายใจ 32'], ['1 วินาที', 'ต่อคลิป', 'mono 16 kHz (15,600 samples)'], ['521', 'feature ต่อคลิป', 'คะแนนหมวดเสียงจาก YAMNet'], ['2', 'class', '1 = กรน · 0 = ไม่กรน']];
  for (let i = 0; i < stats.length; i++) {
    const x = 0.6 + i * 3.05;
    card(s, x, 1.55, 2.85, 2.3, i === 0 ? HEX.dk2 : HEX.lt2, 'stat ' + (i + 1));
    text(s, stats[i][0], { x: x + 0.25, y: 1.75, w: 2.4, h: 0.9, fontSize: 40, bold: true, color: i === 0 ? C.accent2 : C.accent1 });
    text(s, stats[i][1], { x: x + 0.25, y: 2.7, w: 2.4, h: 0.4, fontSize: 15, bold: true, color: i === 0 ? C.background1 : C.text2 });
    text(s, stats[i][2], { x: x + 0.25, y: 3.12, w: 2.4, h: 0.6, fontSize: 12, color: i === 0 ? C.background2 : C.accent6 });
  }
  card(s, 0.6, 4.15, 12.1, 2.55, HEX.lt2, 'training detail');
  text(s, 'สิ่งที่โมเดลเรียนรู้จากชุดฝึก', { x: 0.9, y: 4.35, w: 11.5, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
  text(s, [
    { text: 'Input: คะแนน 521 หมวดเสียงที่ YAMNet ให้กับคลิป 1 วินาที (เช่น Snoring, Breathing, Speech, Rain)', options: { bullet: true, breakLine: true } },
    { text: 'Output: ความน่าจะเป็นว่าเป็นเสียงกรน → ตัดสินด้วย threshold ที่เลือกจาก validation', options: { bullet: true, breakLine: true } },
    { text: 'ฝึกเฉพาะ Dense(64, ReLU) → Dropout 0.2 → Dense(1, sigmoid) · ให้น้ำหนักเสียงหายใจ ×10 · early stopping', options: { bullet: true, breakLine: true } },
    { text: 'ข้อจำกัด: Kaggle ไม่มีรหัสผู้พูด จึงยังพิสูจน์ไม่ได้ว่าใช้ได้กับคนที่ไม่เคยเห็น', options: { bullet: true } },
  ], { x: 0.9, y: 4.8, w: 11.5, h: 1.8, fontSize: 14, paraSpaceAfter: 4 });
  s.addNotes('Training set คือข้อมูลที่โมเดลใช้เรียนรู้ ในงานนี้คือ 725 คลิป คลิปละ 1 วินาที แต่ละคลิปถูกแปลงเป็นตัวเลข 521 ค่าด้วย YAMNet แล้วโมเดลเรียนรู้ว่าแบบไหนคือกรน');

  // ===== 7. Model comparison =====
  pres.addSection({ title: 'ผลโมเดล' });
  s = content('เปรียบเทียบ 7 โมเดลบนชุดทดสอบเดียวกัน', 'ผลโมเดล');
  const order = ['Logistic Regression', 'Random Forest', 'Decision Tree', 'SVM (RBF)', 'k-NN', 'Dense head v2 (web)', 'Dense head v1 (old)'];
  const th = t => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, align: 'center' } });
  const rows = [[th('โมเดล'), th('Val Acc'), th('Test Acc'), th('Precision'), th('Recall'), th('F1'), th('AUC'), th('พลาด')]];
  for (const k of order) {
    const r = M.models[k], t = r.test, cm = t.confusion_matrix, best = k === M.best_by_validation;
    const label = k === 'Dense head v2 (web)' ? 'Dense head v2 (เว็บใช้)' : k === 'Dense head v1 (old)' ? 'Dense head v1 (รุ่นเดิม)*' : k;
    const o = best ? { bold: true, fill: { color: 'FDF0D8' } } : {};
    rows.push([{ text: (best ? '★ ' : '') + label, options: { ...o } }, ...[r.validation_accuracy, t.accuracy, t.precision, t.recall, t.f1].map(v => ({ text: pct(v), options: { ...o, align: 'center' } })), { text: t.roc_auc.toFixed(3), options: { ...o, align: 'center' } }, { text: String(cm[0][1] + cm[1][0]) + '/149', options: { ...o, align: 'center' } }]);
  }
  s.addTable(rows, { x: 0.6, y: 1.45, w: 12.1, colW: [3.3, 1.2, 1.2, 1.3, 1.2, 1.2, 1.1, 1.6], fontSize: 14, color: HEX.dk1, fontFace: 'Tahoma', border: { type: 'solid', pt: 0.75, color: 'DDE3EE' }, rowH: 0.46, valign: 'middle', objectName: 'model comparison table' });
  text(s, 'ทุกโมเดลใช้ feature 521 ค่าจาก YAMNet ชุดเดียวกัน · Train 693 / Val 149 / Test 149 (Kaggle) · เลือก hyperparameter และ “โมเดลที่ดีที่สุด” จาก validation แล้วเปิด test ครั้งเดียว', { x: 0.6, y: 5.35, w: 12.1, h: 0.65, fontSize: 13, color: C.accent6 });
  text(s, '* รุ่นเดิมฝึกบน split ที่ไม่มีรายชื่อไฟล์บันทึกไว้ อาจเคยเห็นคลิปชุดทดสอบนี้ จึงไม่นำมาจัดอันดับ', { x: 0.6, y: 6.05, w: 12.1, h: 0.4, fontSize: 12, color: C.accent6 });
  s.addNotes('เทียบ Logistic Regression, Random Forest, Decision Tree, SVM, k-NN และ Dense head ของเรา บนข้อมูลชุดเดียวกัน Logistic Regression ได้ validation สูงสุดจึงเป็นโมเดลที่ดีที่สุด test 98.66% พลาด 2 จาก 149 คลิป ความต่างระหว่างโมเดลอยู่ที่ 2–5 คลิป ถือว่าใกล้กันมาก เพราะ feature จาก YAMNet ดีอยู่แล้ว');

  // ===== 8. Confusion matrix =====
  s = content('Confusion matrix: โมเดลที่ดีที่สุด เทียบกับโมเดลที่เว็บใช้', 'ผลโมเดล');
  function cmGrid(sl, x, y, cm, title, sub, emphasize) {
    card(sl, x, y, 5.95, 5.25, emphasize ? HEX.dk2 : HEX.lt2, title + ' card');
    text(sl, title, { x: x + 0.35, y: y + 0.25, w: 5.3, h: 0.45, fontSize: 18, bold: true, color: emphasize ? C.background1 : C.text2 });
    text(sl, sub, { x: x + 0.35, y: y + 0.7, w: 5.3, h: 0.4, fontSize: 13, color: emphasize ? C.accent5 : C.accent6 });
    const gx = x + 1.85, gy = y + 1.65, cw = 1.75, ch = 1.25;
    text(sl, 'ทำนาย: ไม่กรน', { x: gx, y: gy - 0.4, w: cw, h: 0.35, fontSize: 12, align: 'center', color: emphasize ? C.background2 : C.text1 });
    text(sl, 'ทำนาย: กรน', { x: gx + cw + 0.1, y: gy - 0.4, w: cw, h: 0.35, fontSize: 12, align: 'center', color: emphasize ? C.background2 : C.text1 });
    text(sl, 'จริง: ไม่กรน', { x: x + 0.3, y: gy + 0.4, w: 1.45, h: 0.45, fontSize: 12, align: 'right', color: emphasize ? C.background2 : C.text1 });
    text(sl, 'จริง: กรน', { x: x + 0.3, y: gy + ch + 0.5, w: 1.45, h: 0.45, fontSize: 12, align: 'right', color: emphasize ? C.background2 : C.text1 });
    const cells = [[cm[0][0], true, 'TN'], [cm[0][1], false, 'FP'], [cm[1][0], false, 'FN'], [cm[1][1], true, 'TP']];
    cells.forEach(([v, ok, tag], i) => {
      const cx = gx + (i % 2) * (cw + 0.1), cy = gy + Math.floor(i / 2) * (ch + 0.1);
      sl.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: cy, w: cw, h: ch, rectRadius: 0.08, fill: { color: ok ? HEX.accent1 : (v ? 'F6D3D9' : 'F4F6FA') }, line: { type: 'none' }, objectName: title + ' ' + tag });
      text(sl, [{ text: String(v), options: { fontSize: 32, bold: true, breakLine: true } }, { text: tag, options: { fontSize: 11 } }], { x: cx, y: cy + 0.15, w: cw, h: ch - 0.2, align: 'center', color: ok ? C.background1 : (v ? C.accent4 : C.accent6) });
    });
    return gy + 2 * ch + 0.25;
  }
  const lr = M.models[M.best_by_validation].test, v2 = M.models['Dense head v2 (web)'].test;
  let yb = cmGrid(s, 0.6, 1.45, lr.confusion_matrix, '★ Logistic Regression (ดีที่สุด)', `Test accuracy ${pct(lr.accuracy)} · Recall กรน ${pct(lr.recall)}`, true);
  text(s, 'ไม่มีการทักผิดว่ากรน (FP = 0) · พลาดกรน 2 คลิป', { x: 0.95, y: yb, w: 5.3, h: 0.4, fontSize: 13, color: C.background2 });
  yb = cmGrid(s, 6.75, 1.45, v2.confusion_matrix, 'Dense head v2 (โมเดลที่เว็บใช้)', `Test accuracy ${pct(v2.accuracy)} · Recall กรน ${pct(v2.recall)}`, false);
  text(s, 'เว็บใช้ตัวนี้เพราะฝึกกับเสียงหายใจด้วย\nนับหายใจเป็นกรน 6/14 → 0/14', { x: 7.1, y: yb, w: 5.4, h: 0.6, fontSize: 13, color: C.text1 });
  s.addNotes('ซ้ายคือโมเดลที่ดีที่สุดตาม validation: ถูก 147 จาก 149 คลิป ไม่มีการทักผิดว่ากรน พลาดกรน 2 คลิป ขวาคือโมเดลที่เว็บใช้จริง พลาดมากกว่า 3 คลิปบน Kaggle แต่เราเลือกใช้เพราะฝึกกับเสียงหายใจด้วย ซึ่งเป็นปัญหาจริงที่เจอตอนใช้งาน Logistic Regression ยังไม่เคยฝึกกับเสียงหายใจ จึงเป็นงานต่อไปที่จะเทียบบนชุดหายใจด้วย');

  // ===== 9. Accuracy chart =====
  s = content('ทุกโมเดลอยู่ในช่วง 96–99%: feature จาก YAMNet ทำงานหนักที่สุด', 'ผลโมเดล');
  s.addImage({ path: 'chart-accuracy.png', x: 0.6, y: 1.45, w: 8.2, h: 5.3, altText: 'กราฟแท่ง test accuracy และ F1 ของ 6 โมเดล อยู่ระหว่าง 96.6 ถึง 98.7 เปอร์เซ็นต์', objectName: 'accuracy chart' });
  card(s, 9.1, 1.45, 3.6, 5.3, HEX.lt2, 'takeaways');
  text(s, 'อ่านผลอย่างไร', { x: 9.4, y: 1.7, w: 3.1, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
  text(s, [
    { text: 'ต่างกันแค่ 2–5 คลิปจาก 149\nชุดทดสอบเล็ก จึงยังสรุปไม่ได้ว่าโมเดลไหนเหนือกว่าอย่างมีนัยสำคัญ', options: { bullet: true, breakLine: true } },
    { text: 'k-NN มี recall สูงสุด (74/75) แต่ทักผิด 3 คลิป', options: { bullet: true, breakLine: true } },
    { text: 'Decision Tree ลึกแค่ 3 ชั้นก็ได้ 98.66%', options: { bullet: true, breakLine: true } },
    { text: 'ROC ทั้ง 7 โมเดลอยู่ใน results/model-comparison/', options: { bullet: true } },
  ], { x: 9.4, y: 2.2, w: 3.1, h: 4.4, fontSize: 13, paraSpaceAfter: 8 });
  s.addNotes('กราฟนี้ย้ำว่าโมเดลทั้งหมดใกล้กัน แกนเริ่ม 90% เพื่อให้เห็นความต่าง ซึ่งจริง ๆ ต่างกันแค่ไม่กี่คลิป ข้อสรุปคือ feature จาก YAMNet ดีมาก ส่วน classifier เลือกแบบไหนก็ได้ผลใกล้กัน');

  // ===== 10. Features =====
  pres.addSection({ title: 'ระบบ' });
  s = content('ฟีเจอร์ของระบบ: เสร็จแล้ว และยังไม่เสร็จ', 'ระบบ');
  const feat = [
    ['done', 'ตรวจกรน / ไม่กรน ทุก 0.1 วินาที (โมเดลรุ่น 2)'],
    ['done', 'อัดเสียงในเว็บ แบ่งไฟล์ทุก 30 นาที · อัปโหลด WAV'],
    ['done', 'รายงาน: สัดส่วนกรน · ช่วงกรน · timeline · ซูม · ย้อนฟัง'],
    ['done', 'ประวัติในเบราว์เซอร์ · export JSON / CSV / WAV'],
    ['done', 'เว็บออนไลน์บน Vercel รันโมเดลในเบราว์เซอร์'],
    ['done', 'เช็กลิสต์อาการตอนเช้า + คำแนะนำพบแพทย์ (ยังไม่ merge/deploy)'],
    ['part', 'ตัวคัดช่วงเสียงไอ (ทดลอง · ยังนับจำนวนครั้งไม่ได้)'],
    ['part', 'เครื่องมือ lab: ช่วงเงียบ ความถี่ จังหวะ เทียบหลายคืน'],
    ['todo', 'โมเดลภาวะหยุดหายใจ: มีเครื่องมือ แต่ยังไม่มีข้อมูล sleep lab มาฝึก'],
    ['todo', 'แอปมือถือ Flutter: เขียนโค้ดแล้ว ยังไม่ได้ build / ทดสอบบนเครื่องจริง'],
    ['todo', 'ทดสอบอัดทั้งคืน 8 ชม. และในห้องนอนจริง'],
    ['todo', 'วัดความดังเป็น dB จริง · แยกเสียงคู่นอน'],
  ];
  const ST = { done: ['เสร็จ', HEX.accent3, 'LuCircleCheck'], part: ['บางส่วน', HEX.accent2, 'LuCircleAlert'], todo: ['ยังไม่เสร็จ', HEX.accent4, 'LuCircleX'] };
  for (let i = 0; i < feat.length; i++) {
    const col = Math.floor(i / 6), row = i % 6, x = 0.6 + col * 6.15, y = 1.45 + row * 0.86;
    const [st, label] = feat[i], [chip, color, ic] = ST[st];
    card(s, x, y, 5.95, 0.74, HEX.lt2, 'feature ' + (i + 1));
    s.addImage({ data: await iconPng(ic, color), x: x + 0.2, y: y + 0.19, w: 0.36, h: 0.36, altText: chip, objectName: 'feature ' + (i + 1) + ' status icon' });
    text(s, label, { x: x + 0.7, y: y + 0.07, w: 3.85, h: 0.6, fontSize: 13, valign: 'middle' });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 4.65, y: y + 0.2, w: 1.1, h: 0.34, rectRadius: 0.17, fill: { color }, line: { type: 'none' }, objectName: 'feature ' + (i + 1) + ' chip' });
    text(s, chip, { x: x + 4.65, y: y + 0.2, w: 1.1, h: 0.34, fontSize: 11, bold: true, align: 'center', valign: 'middle', color: C.background1 });
  }
  s.addNotes('สรุปฟีเจอร์: สีเขียวทำเสร็จและทดสอบแล้ว สีเหลืองทำได้บางส่วนหรือเป็นงานทดลอง สีแดงยังไม่เสร็จ โดยเฉพาะโมเดลภาวะหยุดหายใจที่ต้องใช้ข้อมูลจาก sleep lab ซึ่งเรายังไม่มี');

  // ===== 11. Checklist =====
  s = content('เช็กลิสต์ตอนเช้า: ตอบว่า “ควรไปพบแพทย์ไหม”', 'ระบบ');
  card(s, 0.6, 1.45, 5.1, 5.3, HEX.lt2, 'checklist questions');
  await iconCircle(s, 'LuClipboardCheck', 0.9, 1.7, 0.75, HEX.lt1, HEX.accent1, 'checklist');
  text(s, '5 ข้อ เฉพาะการหายใจ', { x: 1.85, y: 1.85, w: 3.7, h: 0.45, fontSize: 17, bold: true, color: C.text2 });
  text(s, [
    { text: 'ตื่นมาเจ็บคอ / คอแห้ง', options: { bullet: true, breakLine: true } },
    { text: 'ปากแห้งตอนตื่น', options: { bullet: true, breakLine: true } },
    { text: 'สะดุ้งตื่นเพราะสำลัก / หายใจไม่ออก', options: { bullet: true, breakLine: true } },
    { text: 'มีคนเห็นหยุดหายใจขณะหลับ', options: { bullet: true, breakLine: true } },
    { text: 'คัดจมูก / หวัด / ภูมิแพ้ (ใช้อธิบายผล)', options: { bullet: true, breakLine: true } },
    { text: '“กรน” ใช้ผลจากโมเดล ≥ 10% ของเวลาบันทึก', options: { bullet: true } },
  ], { x: 0.9, y: 2.65, w: 4.6, h: 3.9, fontSize: 14, paraSpaceAfter: 6 });
  const lv = [
    [HEX.accent4, 'ควรพบแพทย์', 'มีคนเห็นหยุดหายใจ หรือสะดุ้งตื่นเพราะสำลัก ข้อใดข้อหนึ่ง (สัญญาณเตือนตาม AASM)'],
    [HEX.accent2, 'แนะนำปรึกษาแพทย์', 'แอปตรวจพบกรน + เจ็บคอหรือปากแห้ง (หายใจทางปาก) ตั้งแต่คืนแรก · หรือหายใจทางปาก ≥ 3 ใน 7 คืน · ไม่นับคืนที่คัดจมูก'],
    [HEX.accent3, 'ติดตามอาการต่อ', 'ยังไม่เข้าเกณฑ์ ทำเช็กลิสต์ทุกเช้าเพื่อดูแนวโน้ม'],
  ];
  for (let i = 0; i < lv.length; i++) {
    const y = 1.45 + i * 1.62;
    card(s, 6.0, y, 6.7, 1.45, HEX.lt2, 'level ' + (i + 1));
    s.addShape(pres.shapes.OVAL, { x: 6.3, y: y + 0.32, w: 0.4, h: 0.4, fill: { color: lv[i][0] }, line: { type: 'none' }, objectName: 'level dot ' + (i + 1) });
    text(s, lv[i][1], { x: 6.9, y: y + 0.25, w: 5.6, h: 0.45, fontSize: 17, bold: true, color: C.text2 });
    text(s, lv[i][2], { x: 6.9, y: y + 0.7, w: 5.6, h: 0.7, fontSize: 12 });
  }
  text(s, 'คัดกรองเบื้องต้น ไม่ใช่การวินิจฉัย · เกณฑ์รวมชุดนี้ยังไม่ผ่านการตรวจสอบทางคลินิก', { x: 6.0, y: 6.35, w: 6.7, h: 0.4, fontSize: 12, color: C.accent6 });
  s.addNotes('ฟีเจอร์ที่ตอบคำถามว่าควรไปพบแพทย์ไหม หลังจบการบันทึกผู้ใช้ตอบ 5 ข้อที่เกี่ยวกับการหายใจขณะหลับ แล้วใช้ร่วมกับผลกรนจากโมเดล ติ๊กแล้วมีผลตั้งแต่คืนแรก แบ่งผลเป็น 3 ระดับ ย้ำว่าเป็นการคัดกรอง ไม่ใช่การวินิจฉัย');

  // ===== 12. Test cases =====
  pres.addSection({ title: 'ทดสอบ' });
  s = content('System test cases: ทดสอบอย่างไร และผลเป็นอย่างไร', 'ทดสอบ');
  const pass = { text: 'ผ่าน', options: { bold: true, color: HEX.accent3, align: 'center' } };
  const partial = { text: 'บางส่วน', options: { bold: true, color: 'B7791F', align: 'center' } };
  const tc = [
    [th('#'), th('กรณีทดสอบ'), th('วิธีทดสอบ'), th('ผลที่ได้'), th('สถานะ')],
    ['1', 'คลิปกรน / ไม่กรน ที่ไม่เคยเห็น', 'Test set Kaggle 149 คลิป', 'LR 98.66% · Dense v2 96.64%', pass],
    ['2', 'เสียงหายใจ (คนนอกชุดฝึก)', 'Coswara 14 คลิป แยกคน', 'นับเป็นกรน 6/14 → 0/14', pass],
    ['3', 'ไฟล์หายใจเต็ม 14 ไฟล์', 'รันทั้ง pipeline', 'เวลาที่นับผิด 58.5 → 4.6 วิ · ยังเหลือ 8/14 ไฟล์', partial],
    ['4', 'เงียบสนิท / noise 6 วิ', 'สร้างไฟล์ควบคุม', 'กรน 0 วินาทีทั้งสองไฟล์', pass],
    ['5', 'เดโม 45 วิ (กรนสลับเงียบ)', 'Python เทียบกับ browser', 'ช่วงกรนตรงกันทุกจุด', pass],
    ['6', 'ไฟล์ผิดรูปแบบ / ไฟล์ว่าง', 'อัปโหลดผ่าน API และเว็บ', 'แจ้ง error ผลเดิมไม่หาย', pass],
    ['7', 'เว็บครบ flow', 'Chrome อัตโนมัติ 28 checks', 'อัปโหลด · timeline · seek · export ผ่านทั้งหมด', pass],
    ['8', 'อัด → จบ → เช็กลิสต์ → ผล', 'Chrome + ไมค์จำลอง', 'ผล 3 ระดับถูกตามเกณฑ์', pass],
    ['9', 'Unit tests', 'Python + Node', 'Python 52 · JavaScript 19 ผ่าน', pass],
  ];
  s.addTable(tc, { x: 0.6, y: 1.4, w: 12.1, colW: [0.5, 3.4, 3.1, 3.9, 1.2], fontSize: 13, color: HEX.dk1, fontFace: 'Tahoma', border: { type: 'solid', pt: 0.75, color: 'DDE3EE' }, rowH: 0.47, valign: 'middle', objectName: 'test case table' });
  text(s, 'ยังไม่ได้ทดสอบ: ห้องนอนจริง · อัดทั้งคืน · มือถือจริง · เสียงแตร/มอเตอร์ไซค์ · คู่นอนกรน', { x: 0.6, y: 6.35, w: 12.1, h: 0.4, fontSize: 13, bold: true, color: C.accent4 });
  s.addNotes('ไล่กรณีทดสอบหลัก ทั้งความแม่นยำโมเดล กรณีที่ระบบไม่ควรทักว่ากรน เช่น เงียบและเสียงหายใจ และการทดสอบเว็บแบบอัตโนมัติ บรรทัดล่างคือสิ่งที่ยังไม่ได้ทดสอบ ซึ่งจะเป็นงานต่อไป');

  // ===== 13. How to test =====
  s = content('ทดสอบซ้ำได้เอง: ทำอย่างไร', 'ทดสอบ');
  const how = [
    ['LuGlobe', 'ลองบนเว็บ', 'เปิด snoresens-ai-int182.vercel.app → “ลองวิเคราะห์เสียงตัวอย่าง” หรืออัปโหลด WAV → ดู timeline และกดฟังช่วงกรน'],
    ['LuChartBar', 'เทียบโมเดล', '.venv/bin/python docs/compare_snore_models.py --data <โฟลเดอร์ Kaggle>  → ตรวจ SHA-256 ทุกคลิป แล้วสร้างตาราง confusion matrix และ ROC'],
    ['LuClipboardCheck', 'รัน automated tests', '.venv/bin/python -m unittest discover -s tests  ·  node --test tests/*.mjs tests/*.cjs'],
    ['LuMic', 'ทดสอบด้วยเสียงจริง', 'อัด 10–15 นาที วางเครื่องใกล้เตียง กดจบแล้วทำเช็กลิสต์ เทียบช่วงที่ระบบตรวจพบกับการฟังเอง'],
  ];
  for (let i = 0; i < how.length; i++) {
    const y = 1.45 + i * 1.33;
    card(s, 0.6, y, 12.1, 1.15, HEX.lt2, 'how ' + (i + 1));
    await iconCircle(s, how[i][0], 0.85, y + 0.2, 0.75, HEX.lt1, HEX.accent1, 'how ' + (i + 1));
    text(s, how[i][1], { x: 1.85, y: y + 0.15, w: 2.6, h: 0.85, fontSize: 17, bold: true, valign: 'middle', color: C.text2 });
    text(s, how[i][2], { x: 4.5, y: y + 0.12, w: 8.0, h: 0.9, fontSize: 13, valign: 'middle' });
  }
  s.addNotes('ใครก็ทดสอบซ้ำได้ 4 ทาง: ลองบนเว็บ รันสคริปต์เปรียบเทียบโมเดลซึ่งตรวจ hash ทุกคลิปก่อน รัน unit tests และอัดเสียงจริงแล้วฟังเทียบ');

  // ===== 14. Answer =====
  pres.addSection({ title: 'สรุป' });
  s = pres.addSlide({ masterName: 'DARK_TITLE', sectionTitle: 'สรุป' });
  text(s, 'ตอบปัญหาได้ไหม?', { x: 0.8, y: 0.6, w: 11.7, h: 0.8, fontSize: 36, bold: true, color: C.background1 });
  const ans = [
    [HEX.accent3, 'ได้', 'แยก “กรน / ไม่กรน” จากคลิปเสียง', 'Test 96.6–98.7% บนคลิปที่ไม่เคยเห็น\nและไม่นับหายใจเป็นกรน (0/14)'],
    [HEX.accent2, 'บางส่วน', 'บอกว่ากรนช่วงไหน นานเท่าไร ทั้งคืน', 'ตรวจทุก 0.1 วิ แต่ยังไม่ได้ยืนยัน\nกับห้องนอนจริงและการอัดทั้งคืน'],
    [HEX.accent4, 'ยังไม่ได้', 'วินิจฉัยภาวะหยุดหายใจขณะหลับ', 'ต้องใช้ข้อมูล sleep lab\nตอนนี้ใช้เช็กลิสต์คัดกรอง\nแล้วแนะนำให้พบแพทย์แทน'],
  ];
  for (let i = 0; i < ans.length; i++) {
    const x = 0.8 + i * 3.95;
    card(s, x, 1.7, 3.7, 4.0, '24396B', 'answer ' + (i + 1));
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.3, y: 2.0, w: 1.5, h: 0.5, rectRadius: 0.25, fill: { color: ans[i][0] }, line: { type: 'none' }, objectName: 'answer chip ' + (i + 1) });
    text(s, ans[i][1], { x: x + 0.3, y: 2.0, w: 1.5, h: 0.5, fontSize: 15, bold: true, align: 'center', valign: 'middle', color: C.background1 });
    text(s, ans[i][2], { x: x + 0.3, y: 2.75, w: 3.1, h: 1.0, fontSize: 18, bold: true, color: C.background1 });
    text(s, ans[i][3], { x: x + 0.3, y: 3.85, w: 3.1, h: 1.7, fontSize: 14, color: C.accent5 });
  }
  text(s, 'งานต่อไป: เก็บเสียงห้องนอนจริงพร้อมป้ายเวลา · เทียบ Logistic Regression บนเสียงหายใจ · ทดสอบอัดทั้งคืนบนมือถือ', { x: 0.8, y: 6.05, w: 11.7, h: 0.7, fontSize: 15, color: C.background2 });
  s.addNotes('สรุปคำตอบ: ได้สำหรับการแยกกรนจากคลิปเสียง ได้บางส่วนสำหรับการใช้ทั้งคืนในห้องนอนจริงที่ยังไม่ได้ทดสอบ และยังไม่ได้สำหรับการวินิจฉัยโรค ซึ่งตอนนี้ใช้เช็กลิสต์เพื่อแนะนำให้พบแพทย์แทน');

  // ===== 15. References =====
  s = content('References', 'สรุป');
  const refs = [
    'T. H. Khan, “A deep learning model for snoring detection and vibration notification using a smart wearable gadget,” Electronics 8(9):987, 2019 — Kaggle: tareqkhanemu/snoring',
    'Coswara-Data, Indian Institute of Science (IISc): github.com/iiscleap/Coswara-Data',
    'YAMNet, Google / TensorFlow Hub (trained on AudioSet): tfhub.dev/google/yamnet/1',
    'American Academy of Sleep Medicine (AASM), sleepeducation.org — warning signs of obstructive sleep apnea',
    'Mayo Clinic, “Obstructive sleep apnea — Symptoms and causes”; WebMD, “Symptoms of OSA” (dry mouth / sore throat from mouth breathing)',
    'เสียงตัวอย่าง: “Tongue base snoring,” Langenbergstefan, Wikimedia Commons, CC BY-SA 3.0',
  ];
  text(s, refs.map((r, i) => ({ text: r, options: { bullet: { type: 'number' }, breakLine: i < refs.length - 1 } })), { x: 0.6, y: 1.4, w: 12.1, h: 4.3, fontSize: 13, paraSpaceAfter: 6 });
  card(s, 0.6, 5.85, 12.1, 0.95, HEX.lt2, 'links');
  await iconCircle(s, 'LuGithub', 0.8, 5.97, 0.7, HEX.lt1, HEX.dk2, 'github');
  text(s, [
    { text: 'GitHub: ', options: { bold: true } }, { text: 'github.com/Phakinza007/snoresens-ai', options: { hyperlink: { url: 'https://github.com/Phakinza007/snoresens-ai' }, color: C.accent1, breakLine: true } },
    { text: 'เว็บ: ', options: { bold: true } }, { text: 'snoresens-ai-int182.vercel.app', options: { hyperlink: { url: 'https://snoresens-ai-int182.vercel.app' }, color: C.accent1 } },
  ], { x: 1.7, y: 5.95, w: 10.8, h: 0.8, fontSize: 14, valign: 'middle' });
  s.addNotes('หน้าอ้างอิงเป็นหน้าสุดท้ายตามข้อกำหนด พร้อมลิงก์ GitHub และเว็บที่อาจารย์เปิดตรวจได้');

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log('wrote', OUT);
})();
