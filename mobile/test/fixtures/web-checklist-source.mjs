// Morning checklist limited to breathing during sleep. Screening guidance only, never a diagnosis.
// Signs: witnessed breathing pauses and choking/gasping (AASM: warning signs of OSA to discuss with a doctor),
// sore/dry throat and dry mouth on waking from mouth breathing (Mayo Clinic, WebMD), plus snoring measured by the app.
// The way these are combined into levels is the project's own rule and has not been clinically validated.
export const SNORE_PERCENT=10,REPEAT_NIGHTS=3,WINDOW_NIGHTS=7;
const YN=[['yes','ใช่'],['no','ไม่ใช่']];
export const QUESTIONS=[
  {id:'sore_throat',group:'morning',label:'ตื่นมาเจ็บคอหรือคอแห้ง',options:[['none','ไม่มี'],['mild','เล็กน้อย'],['severe','มาก']]},
  {id:'dry_mouth',group:'morning',label:'ปากแห้งตอนตื่น',options:YN},
  {id:'choking',group:'warning',label:'สะดุ้งตื่นเพราะสำลัก หายใจเฮือก หรือหายใจไม่ออก',options:YN},
  {id:'witnessed',group:'warning',label:'คนข้าง ๆ เห็นว่าหยุดหายใจขณะหลับ',options:[['yes','ใช่'],['no','ไม่ใช่'],['unknown','ไม่มีคนสังเกต']]},
  {id:'congestion',group:'context',label:'เมื่อคืนคัดจมูก เป็นหวัด หรือภูมิแพ้',options:YN},
];
export const GROUPS={morning:'อาการตอนตื่น (หายใจทางปาก)',warning:'การหายใจขณะหลับ',context:'ปัจจัยที่อาจทำให้ผลคลาดเคลื่อน'};
const MOUTH=['sore_throat','dry_mouth'];
const yes=v=>v==='yes'||v==='mild'||v==='severe';

export const nightKey=r=>r.sessionId||r.id;
export function nightRecords(records,record){
  if(!record)return [];
  if(!record.sessionId)return [record];
  return records.filter(r=>r.sessionId===record.sessionId).sort((a,b)=>a.createdAt.localeCompare(b.createdAt));
}
export const morningSymptoms=(answers={})=>MOUTH.filter(id=>yes(answers[id]));
export const isComplete=answers=>QUESTIONS.every(q=>answers?.[q.id]!==undefined);
// Snoring as measured by the app for that night (detected snore time / recorded time).
export function snorePercent(night){
  const rec=night.reduce((s,r)=>s+(r.analysis?.summary?.recording_seconds||0),0);
  const snore=night.reduce((s,r)=>s+(r.analysis?.summary?.detected_snore_seconds||0),0);
  return rec>0?100*snore/rec:null;
}
// A night counts as a mouth-breathing night when it has a symptom and no blocked nose / cold / allergy.
const mouthNight=a=>morningSymptoms(a).length>0&&!yes(a?.congestion);

// history: answers of earlier nights (newest first), excluding this one.
export function evaluate(answers,{snorePct=null,history=[]}={}){
  const reasons=[],symptoms=morningSymptoms(answers),congested=yes(answers.congestion);
  const snoring=Number.isFinite(snorePct)&&snorePct>=SNORE_PERCENT;
  const recent=[answers,...history].slice(0,WINDOW_NIGHTS),symptomNights=recent.filter(mouthNight).length;
  let level='monitor';
  if(yes(answers.witnessed)){level='urgent';reasons.push('มีคนเห็นว่าหยุดหายใจขณะหลับ');}
  if(yes(answers.choking)){level='urgent';reasons.push('สะดุ้งตื่นเพราะสำลักหรือหายใจไม่ออก');}
  if(snoring&&symptoms.length&&!congested){if(level==='monitor')level='consult';reasons.push(`แอปตรวจพบกรน ${snorePct.toFixed(0)}% ของเวลาบันทึก ร่วมกับอาการหายใจทางปากตอนตื่น`);}
  if(symptomNights>=REPEAT_NIGHTS){if(level==='monitor')level='consult';reasons.push(`มีอาการหายใจทางปาก ${symptomNights} ใน ${recent.length} คืนล่าสุด`);}
  return {level,reasons,symptoms,snoring,snorePct,symptomNights,nightsConsidered:recent.length,confounder:congested};
}
