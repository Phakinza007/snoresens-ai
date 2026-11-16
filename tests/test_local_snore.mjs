import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {localFeatures,localWindow,localProbability} from '../web/snoresens/local-snore.mjs';
const fixtures=JSON.parse(fs.readFileSync(new URL('./fixtures/local-snore.json',import.meta.url)));
const config=JSON.parse(fs.readFileSync(new URL('../artifacts/experimental_snore_v3/verifier.json',import.meta.url)));
for(const f of fixtures)test('Python local verifier parity: '+f.name,()=>{
 const audio=Float32Array.from(f.samples),actual=localFeatures(audio);
 assert.equal(actual.length,80);
 for(let i=0;i<80;i++)assert.ok(Math.abs(actual[i]-f.features[i])<.0001,`feature ${i}: ${actual[i]} vs ${f.features[i]}`);
 assert.ok(Math.abs(localProbability(audio,config)-f.probability)<.00001);
});
test('200 ms context padding excludes artificial duration',()=>{
 assert.equal(localWindow(Float32Array.from([1,2]),0).length,3200);
 assert.deepEqual(Array.from(localWindow(Float32Array.from([1,2]),0).slice(0,4)),[1,2,0,0]);
});
