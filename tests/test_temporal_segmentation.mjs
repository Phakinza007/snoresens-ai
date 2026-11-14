import test from 'node:test';
import assert from 'node:assert/strict';
import {analysisPlan,isSnore,eventTime,activityThreshold} from '../web/snoresens/temporal.mjs';

test('100 ms cells cover audio once including a partial last cell',()=>{
  const rows=[...analysisPlan(37600,1600)];
  assert.equal(rows.length,24);assert.equal(rows.reduce((a,r)=>a+r.length,0),37600);
  assert.equal(rows.at(-1).length,800);
  assert.equal(rows[0].contextStart,0);assert.equal(rows.at(-1).contextStart,22000);
});
test('strong context prediction cannot label digital silence as snoring',()=>{
  assert.equal(isSnore(.99,null,.44),false);assert.equal(isSnore(.99,-70,.44),false);
  assert.equal(isSnore(.9,-25,.44),true);assert.equal(isSnore(.2,-25,.44),false);
});
test('event labels retain subsecond boundaries',()=>{
  assert.equal(eventTime(5.3),'00:00:05.30');assert.equal(eventTime(65.8),'00:01:05.80');
});
test('local low-energy gaps do not inherit positive context labels',()=>{
  const levels=[...Array(10).fill(-36),...Array(5).fill(-15),...Array(10).fill(-36),...Array(5).fill(-15)];
  const floor=activityThreshold(levels);assert.equal(floor,-30);
  assert.equal(levels.filter(level=>isSnore(.99,level,.44,floor)).length,10);
  assert.equal(activityThreshold(Array(20).fill(-20)),-20);
});

test('20 ms cells keep a 20 ms gap and reuse each 100 ms model context',()=>{
  const rows=[...analysisPlan(32000)];assert.equal(rows.length,100);
  assert.equal(rows[0].length,320);
  assert.deepEqual(rows.slice(25,30).map(x=>x.contextStart),Array(5).fill(rows[25].contextStart));
  assert.equal(eventTime(.02),'00:00:00.02');
  assert.equal(eventTime(.04),'00:00:00.04');
});
