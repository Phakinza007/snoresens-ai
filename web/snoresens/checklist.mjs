// Morning symptom checklist + baseline risk factors. Screening guidance only, never a diagnosis.
// Sources: AASM 2017 diagnostic guideline (sleepiness + 2 of snoring / witnessed apnea-choking / hypertension),
// STOP-Bang risk factors (Chung et al.) with the Asian BMI > 30 modification (Banhiran et al. 2014),
// morning symptoms listed by Mayo Clinic and Sleep Foundation.
export const SNORE_PERCENT=10,SYMPTOM_NIGHT_MIN=2,REPEAT_NIGHTS=3,WINDOW_NIGHTS=7;
const YN=[['yes','ใช่'],['no','ไม่ใช่']];
export const QUESTIONS=[
  {id:'sore_throat',group:'morning',label:'ตื่นมาเจ็บคอหรือคอแห้ง',options:[['none','ไม่มี'],['mild','เล็กน้อย'],['severe','มาก']]},
  {id:'dry_mouth',group:'morning',label:'ปากแห้งตอนตื่น',options:YN},
  {id:'headache',group:'morning',label:'ปวดหัวตอนตื่น',options:YN},
  {id:'unrefreshed',group:'morning',label:'ตื่นแล้วยังรู้สึกไม่สดชื่น',options:YN},
  {id:'nocturia',group:'morning',label:'ตื่นไปปัสสาวะกลางดึก 2 ครั้งขึ้นไป',options:YN},
  {id:'sleepy_day',group:'day',label:'ช่วงนี้ง่วงมากตอนกลางวัน หรือเผลอหลับระหว่างทำกิจกรรม',options:YN},
  {id:'choking',group:'warning',label:'สะดุ้งตื่นเพราะสำลัก หายใจเฮือก หรือหายใจไม่ออก',options:YN},
  {id:'witnessed',group:'warning',label:'คนข้าง ๆ เห็นว่าหยุดหายใจขณะหลับ',options:[['yes','ใช่'],['no','ไม่ใช่'],['unknown','ไม่มีคนสังเกต']]},
  {id:'drowsy_driving',group:'warning',label:'เผลอหลับหรือเกือบหลับขณะขับรถ',options:YN},
  {id:'chest',group:'warning',label:'เจ็บหน้าอก หรือใจสั่นผิดปกติตอนตื่น',options:YN},
  {id:'confounder',group:'context',label:'เมื่อวานเป็นหวัด ภูมิแพ้ หรือดื่มแอลกอฮอล์ก่อนนอน',options:YN},
];
export const GROUPS={morning:'อาการตอนตื่นนอน',day:'ช่วงกลางวัน',warning:'อาการที่ต้องระวัง',context:'ปัจจัยที่อาจทำให้ผลคลาดเคลื่อน'};
const MORNING=['sore_throat','dry_mouth','headache','unrefreshed','nocturia'];
const yes=v=>v==='yes'||v==='mild'||v==='severe';

export const nightKey=r=>r.sessionId||r.id;
export function nightRecords(records,record){
  if(!record)return [];
  if(!record.sessionId)return [record];
  return records.filter(r=>r.sessionId===record.sessionId).sort((a,b)=>a.createdAt.localeCompare(b.createdAt));
}
export function morningSymptoms(answers={}){return MORNING.filter(id=>yes(answers[id]));}
export const isComplete=answers=>QUESTIONS.every(q=>answers?.[q.id]!==undefined);

export function bmi(profile){
  const h=Number(profile?.heightCm)/100,w=Number(profile?.weightKg);
  return h>0.5&&h<2.5&&w>20&&w<350?Math.round(w/(h*h)*10)/10:null;
}
// Snoring as measured by the app for that night (detected snore time / recorded time).
export function snorePercent(night){
  const rec=night.reduce((s,r)=>s+(r.analysis?.summary?.recording_seconds||0),0);
  const snore=night.reduce((s,r)=>s+(r.analysis?.summary?.detected_snore_seconds||0),0);
  return rec>0?100*snore/rec:null;
}

// One point per STOP-Bang risk factor; uses BMI > 30 (Asian modification) and neck ≥ 40 cm.
export function riskFactors(answers={},profile={},snorePct=null){
  const b=bmi(profile);
  const f={
    snoring:(Number.isFinite(snorePct)&&snorePct>=SNORE_PERCENT)||profile.snoreReported===true,
    tired:yes(answers.sleepy_day)||yes(answers.unrefreshed),
    observed:yes(answers.witnessed)||yes(answers.choking),
    pressure:profile.hypertension===true,
    bmi:b!==null&&b>30,
    age:Number(profile.age)>50,
    neck:Number(profile.neckCm)>=40,
    male:profile.sex==='male',
  };
  return {factors:f,score:Object.values(f).filter(Boolean).length,profileComplete:['age','sex','hypertension','heightCm','weightKg','neckCm'].every(k=>profile[k]!==undefined&&profile[k]!==''&&profile[k]!==null)};
}

// history: checklist answers of earlier nights (newest first), excluding this one.
export function evaluate(answers,{profile={},snorePct=null,history=[]}={}){
  const reasons=[],symptoms=morningSymptoms(answers),{factors,score,profileComplete}=riskFactors(answers,profile,snorePct);
  const urgent=[['witnessed','มีคนเห็นว่าหยุดหายใจขณะหลับ'],['choking','สะดุ้งตื่นเพราะสำลักหรือหายใจไม่ออก'],['drowsy_driving','เผลอหลับหรือเกือบหลับขณะขับรถ'],['chest','เจ็บหน้าอกหรือใจสั่นผิดปกติ']].filter(([id])=>yes(answers[id])).map(([,t])=>t);
  const recent=[answers,...history].slice(0,WINDOW_NIGHTS);
  const symptomNights=recent.filter(a=>morningSymptoms(a).length>=SYMPTOM_NIGHT_MIN).length;
  const aasm=factors.tired&&[factors.snoring,factors.observed,factors.pressure].filter(Boolean).length>=2;
  let level='monitor';
  if(urgent.length){level='urgent';reasons.push(...urgent);}
  if(aasm){if(level==='monitor')level='consult';reasons.push('ง่วงหรือไม่สดชื่น ร่วมกับกรน หยุดหายใจ/สำลัก หรือความดันสูงอย่างน้อย 2 ข้อ');}
  if(symptomNights>=REPEAT_NIGHTS){if(level==='monitor')level='consult';reasons.push(`มีอาการตอนเช้าตั้งแต่ ${SYMPTOM_NIGHT_MIN} ข้อขึ้นไป ${symptomNights} ใน ${recent.length} คืนล่าสุด`);}
  if(score>=5){if(level==='monitor')level='consult';reasons.push(`มีปัจจัยเสี่ยง ${score} จาก 8 ข้อ`);}
  else if(score>=3)reasons.push(`มีปัจจัยเสี่ยง ${score} จาก 8 ข้อ (ระดับปานกลาง)`);
  return {level,reasons,symptoms,symptomNights,nightsConsidered:recent.length,score,factors,profileComplete,confounder:yes(answers.confounder)};
}
