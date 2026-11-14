import test from 'node:test';
import assert from 'node:assert/strict';
import {QUESTIONS,evaluate,morningSymptoms,snorePercent,nightRecords,isComplete} from '../web/snoresens/checklist.mjs';

const none=Object.fromEntries(QUESTIONS.map(q=>[q.id,q.id==='sore_throat'?'none':'no']));
const ans=over=>({...none,...over});

test('only breathing-related questions, each with unique id and ≥ 2 options',()=>{
  assert.deepEqual(QUESTIONS.map(q=>q.id),['sore_throat','dry_mouth','choking','witnessed','congestion']);
  for(const q of QUESTIONS)assert.ok(q.options.length>=2,q.id);
  assert.equal(isComplete(none),true);assert.equal(isComplete({sore_throat:'none'}),false);
});
test('nothing ticked and no snoring → monitor',()=>{
  const r=evaluate(none);assert.equal(r.level,'monitor');assert.deepEqual(r.reasons,[]);
});
test('witnessed apnea or choking alone → urgent',()=>{
  assert.equal(evaluate(ans({witnessed:'yes'})).level,'urgent');
  assert.equal(evaluate(ans({choking:'yes'})).level,'urgent');
  assert.equal(evaluate(ans({witnessed:'unknown'})).level,'monitor');
});
test('mouth-breathing symptoms: sore/dry throat (mild counts) and dry mouth',()=>{
  assert.deepEqual(morningSymptoms(ans({sore_throat:'mild',dry_mouth:'yes'})),['sore_throat','dry_mouth']);
  assert.deepEqual(morningSymptoms(ans({congestion:'yes'})),[]);
});
test('first night: app snoring + one mouth-breathing symptom → consult',()=>{
  assert.equal(evaluate(ans({dry_mouth:'yes'}),{snorePct:25}).level,'consult');
  assert.equal(evaluate(ans({sore_throat:'mild'}),{snorePct:10}).level,'consult');
  // below the snoring threshold, or no symptom, stays monitor
  assert.equal(evaluate(ans({dry_mouth:'yes'}),{snorePct:9.9}).level,'monitor');
  assert.equal(evaluate(none,{snorePct:80}).level,'monitor');
  // blocked nose / cold / allergy explains the symptom → not escalated
  const r=evaluate(ans({dry_mouth:'yes',congestion:'yes'}),{snorePct:25});
  assert.equal(r.level,'monitor');assert.equal(r.confounder,true);
});
test('repeated mouth breathing on ≥ 3 of last 7 nights → consult even without snoring',()=>{
  const sym=ans({dry_mouth:'yes'});
  assert.equal(evaluate(sym,{history:[sym]}).level,'monitor');
  const r=evaluate(sym,{history:[sym,none,sym]});assert.equal(r.level,'consult');assert.equal(r.symptomNights,3);
  // congested nights do not count toward repetition
  const cold=ans({dry_mouth:'yes',congestion:'yes'});
  assert.equal(evaluate(sym,{history:[cold,cold]}).level,'monitor');
  // only the last 7 nights
  assert.equal(evaluate(sym,{history:[none,none,none,none,none,none,sym,sym]}).level,'monitor');
});
test('urgent outranks consult and keeps both reasons',()=>{
  const r=evaluate(ans({witnessed:'yes',dry_mouth:'yes'}),{snorePct:30});
  assert.equal(r.level,'urgent');assert.equal(r.reasons.length,2);
});
test('night snore percent combines all parts of a session',()=>{
  const part=(sec,snore,id,createdAt)=>({id,sessionId:'s',createdAt,analysis:{summary:{recording_seconds:sec,detected_snore_seconds:snore}}});
  const a=part(1800,180,'a','2026-11-14T01:00:00Z'),b=part(1800,540,'b','2026-11-14T00:30:00Z');
  assert.equal(snorePercent(nightRecords([a,b,{id:'x',sessionId:'t',createdAt:''}],a)),20);
  assert.equal(snorePercent([]),null);
});
