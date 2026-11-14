const assert = require('node:assert/strict');
const {soundReviewEntries, breathingStatusText, breathingPlotPoints} = require('../web/measurements.js');

const item={sound_review:{events:[{sound_type:'speech',start_seconds:4,end_seconds:5,duration_seconds:1},
  {sound_type:'snore',start_seconds:1,end_seconds:3,duration_seconds:2}]}};
assert.equal(soundReviewEntries(item).length,2);
assert.equal(soundReviewEntries(item)[0].event_type,'snore');
assert.match(soundReviewEntries(item)[1].kind,/เสียงพูด/);
assert.ok(!soundReviewEntries(item)[1].kind.includes('ละเมอ'));
assert.equal(soundReviewEntries({snore_events:[{start_seconds:0,end_seconds:1,duration_seconds:1}]}).length,1);
assert.match(breathingStatusText('insufficient_signal'),/สัญญาณ/);
assert.match(breathingStatusText('insufficient_breathing_evidence'),/หายใจ/);
assert.match(breathingStatusText('estimated'),/ทดลอง/);
assert.match(breathingStatusText('unknown'),/ข้อมูล/);
const points=breathingPlotPoints({windows:[
  {start_seconds:0,duration_seconds:30,status:'estimated',breaths_per_minute:15},
  {start_seconds:30,duration_seconds:10,status:'insufficient_duration',breaths_per_minute:null}
]});
assert.deepEqual(points,[{x:15,y:15},{x:35,y:null}]);
assert.deepEqual(breathingPlotPoints({}),[]);
console.log('Sleep audio UI calculations passed');
