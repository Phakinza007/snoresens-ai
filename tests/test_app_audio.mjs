import test from 'node:test';
import assert from 'node:assert/strict';
import {pcmWav} from '../web/snoresens/audio.mjs';

test('WAV has mono PCM16 16 kHz header, signed/clamped samples and real duration', async () => {
  const wav=pcmWav(new Float32Array([-2,-1,0,1,2]));
  const data=new DataView(await wav.arrayBuffer());
  assert.equal(wav.type,'audio/wav');
  assert.equal(new TextDecoder().decode(new Uint8Array(data.buffer,0,4)),'RIFF');
  assert.equal(data.getUint32(4,true),46);
  assert.equal(data.getUint16(22,true),1);
  assert.equal(data.getUint32(24,true),16000);
  assert.equal(data.getUint32(40,true),10);
  assert.deepEqual(Array.from({length:5},(_,i)=>data.getInt16(44+2*i,true)),[-32768,-32768,0,32767,32767]);
});
test('empty or nonfinite samples are rejected',()=>{
  assert.throws(()=>pcmWav(new Float32Array()),/empty/);
  assert.throws(()=>pcmWav(new Float32Array([NaN])),/finite/);
});
