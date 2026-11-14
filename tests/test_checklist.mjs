import test from 'node:test';
import assert from 'node:assert/strict';
import {QUESTIONS,evaluate,morningSymptoms,riskFactors,bmi,snorePercent,nightRecords,isComplete} from '../web/snoresens/checklist.mjs';

const none=Object.fromEntries(QUESTIONS.map(q=>[q.id,q.id==='sore_throat'?'none':'no']));
const ans=over=>({...none,...over});

test('every question has a unique id and at least two options',()=>{
  assert.equal(new Set(QUESTIONS.map(q=>q.id)).size,QUESTIONS.length);
  for(const q of QUESTIONS)assert.ok(q.options.length>=2,q.id);
  assert.equal(isComplete(none),true);assert.equal(isComplete({sore_throat:'none'}),false);
});
test('no symptoms and no risk factors → monitor',()=>{
  const r=evaluate(none);assert.equal(r.level,'monitor');assert.deepEqual(r.reasons,[]);assert.equal(r.score,0);
});
test('each red flag alone → urgent',()=>{
  for(const id of ['witnessed','choking','drowsy_driving','chest'])assert.equal(evaluate(ans({[id]:'yes'})).level,'urgent',id);
  assert.equal(evaluate(ans({witnessed:'unknown'})).level,'monitor');
});
test('morning symptoms counted; mild sore throat counts',()=>{
  assert.deepEqual(morningSymptoms(ans({sore_throat:'mild',headache:'yes'})),['sore_throat','headache']);
  assert.deepEqual(morningSymptoms(ans({confounder:'yes',sleepy_day:'yes'})),[]);
});
test('AASM rule: sleepiness + snoring + hypertension → consult',()=>{
  const opts={profile:{hypertension:true},snorePct:25};
  assert.equal(evaluate(ans({sleepy_day:'yes'}),opts).level,'consult');
  // Without sleepiness, two signs are not enough.
  assert.equal(evaluate(none,opts).level,'monitor');
  // App snoring below the threshold does not count, but a reported loud snorer does.
  assert.equal(evaluate(ans({sleepy_day:'yes'}),{profile:{hypertension:true},snorePct:5}).level,'monitor');
  assert.equal(evaluate(ans({sleepy_day:'yes'}),{profile:{hypertension:true,snoreReported:true},snorePct:5}).level,'consult');
});
test('repeated symptomatic mornings (≥3 of last 7) → consult',()=>{
  const sym=ans({sore_throat:'mild',dry_mouth:'yes'});
  assert.equal(evaluate(sym,{history:[sym]}).level,'monitor');
  const r=evaluate(sym,{history:[sym,none,sym]});assert.equal(r.level,'consult');assert.equal(r.symptomNights,3);assert.equal(r.nightsConsidered,4);
  // Only the last 7 nights count.
  assert.equal(evaluate(sym,{history:[none,none,none,none,none,none,sym,sym]}).level,'monitor');
});
test('risk factors use BMI > 30, neck ≥ 40 cm, age > 50, male',()=>{
  const profile={age:55,sex:'male',heightCm:170,weightKg:90,neckCm:41,hypertension:false};
  assert.equal(bmi(profile),31.1);
  const {factors,score,profileComplete}=riskFactors(none,profile,null);
  assert.deepEqual([factors.age,factors.male,factors.bmi,factors.neck,factors.pressure],[true,true,true,true,false]);
  assert.equal(score,4);assert.equal(profileComplete,true);
  assert.equal(evaluate(none,{profile}).level,'monitor');
  assert.equal(evaluate(none,{profile,snorePct:30}).level,'consult');
  assert.equal(riskFactors(none,{},null).profileComplete,false);
  assert.equal(bmi({heightCm:0,weightKg:70}),null);
});
test('night snore percent combines all parts of a session',()=>{
  const part=(sec,snore,id,createdAt)=>({id,sessionId:'s',createdAt,analysis:{summary:{recording_seconds:sec,detected_snore_seconds:snore}}});
  const a=part(1800,180,'a','2026-11-14T01:00:00Z'),b=part(1800,540,'b','2026-11-14T00:30:00Z');
  assert.equal(snorePercent(nightRecords([a,b,{id:'x',sessionId:'t',createdAt:''}],a)),20);
  assert.equal(snorePercent([]),null);
});
