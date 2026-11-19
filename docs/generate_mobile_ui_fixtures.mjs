import fs from 'node:fs';
import {createRequire} from 'node:module';
import {evaluate} from '../mobile/test/fixtures/web-checklist-source.mjs';
const base={sore_throat:'none',dry_mouth:'no',choking:'no',witnessed:'unknown',congestion:'no'};
const histories=[[],[{...base,dry_mouth:'yes'},{...base,sore_throat:'mild'}],Array.from({length:8},(_,i)=>({...base,dry_mouth:i<2?'no':'yes',congestion:i===4?'yes':'no'}))];
const cases=[];
for(const sore_throat of ['none','mild','severe'])for(const dry_mouth of ['yes','no'])for(const choking of ['yes','no'])for(const witnessed of ['yes','no','unknown'])for(const congestion of ['yes','no'])for(const snorePct of [null,9.9,10,40])for(const history of histories){const answers={sore_throat,dry_mouth,choking,witnessed,congestion};cases.push({answers,snorePct,history,expected:evaluate(answers,{snorePct,history})});}
fs.writeFileSync('mobile/test/fixtures/web-checklist.json',JSON.stringify(cases));
const {researchScores}=createRequire(import.meta.url)('../web/measurements.js');
const scores=[];
for(const recording_seconds of [0,120])for(const detected_snore_seconds of [0,30,130])for(const starts of [[],[0],[0,10],[0,10.02],[0,100],[0,20,40],[20,10]]){const item={summary:{recording_seconds,detected_snore_seconds},snore_events:starts.map(start_seconds=>({start_seconds,end_seconds:start_seconds+1,duration_seconds:1}))};scores.push({item,expected:researchScores(item).combined.score});}
fs.writeFileSync('mobile/test/fixtures/web-composite.json',JSON.stringify(scores));
console.log(`Generated ${cases.length} checklist and ${scores.length} composite-score cases from web source.`);
