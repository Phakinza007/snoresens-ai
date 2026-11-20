export function pcmWav(samples) {
  if (!samples.length) throw new Error('Audio is empty');
  const buffer=new ArrayBuffer(44+samples.length*2),view=new DataView(buffer);
  const text=(at,value)=>{for(let i=0;i<value.length;i++)view.setUint8(at+i,value.charCodeAt(i));};
  text(0,'RIFF');view.setUint32(4,buffer.byteLength-8,true);text(8,'WAVE');text(12,'fmt ');
  view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
  view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);
  text(36,'data');view.setUint32(40,samples.length*2,true);
  for(let i=0;i<samples.length;i++) {
    if(!Number.isFinite(samples[i]))throw new Error('Audio samples must be finite');
    const value=Math.max(-1,Math.min(1,samples[i]));
    view.setInt16(44+i*2,Math.round(value<0?value*32768:value*32767),true);
  }
  return new Blob([buffer],{type:'audio/wav'});
}

export async function startRecording({onChunk,onError,onTick,onDone,partMillis=30*60*1000}) {
  if(!navigator.mediaDevices?.getUserMedia||!window.AudioWorkletNode)throw new Error('เบราว์เซอร์นี้ยังบันทึกเสียงไม่ได้ กรุณาใช้ Chrome ผ่าน localhost หรือ HTTPS');
  const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false}});
  let context,node,source,gain,active=true,paused=false,queue=Promise.resolve(),blocks=[],size=0,totalSamples=0,part=0,timer,wakeLock;
  let partStarted=new Date().toISOString();
  async function release(){clearInterval(timer);stream.getTracks().forEach(track=>track.stop());source?.disconnect();node?.disconnect();gain?.disconnect();await context?.close().catch(()=>{});await wakeLock?.release().catch(()=>{});}
  function emitPart(){
    if(!size)return;
    const samples=new Float32Array(size);let offset=0;
    for(const block of blocks){samples.set(block,offset);offset+=block.length;}
    blocks=[];size=0;
    const started=partStarted;partStarted=new Date().toISOString();const current=++part;
    queue=queue.then(()=>onChunk(pcmWav(samples),current,started)).catch(onError);
  }
  function stop(){if(!active)return;active=false;clearInterval(timer);node.port.postMessage('stop');}
  try {
    context=new AudioContext({sampleRate:16000});
    if(context.sampleRate!==16000)throw new Error('อุปกรณ์นี้ไม่รองรับการบันทึก 16 kHz กรุณาอัปโหลด WAV แทน');
    await context.audioWorklet.addModule('/app-assets/capture-worklet.js');
    node=new AudioWorkletNode(context,'snoresens-capture',{numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[1]});
    node.port.onmessage=event=>{
      const data=event.data;
      if(data.type==='samples'){blocks.push(data.samples);size+=data.samples.length;totalSamples+=data.samples.length;let power=0;for(const sample of data.samples)power+=sample*sample;onTick(totalSamples/16000,Math.sqrt(power/data.samples.length));}
      else if(data.type==='boundary')emitPart();
      else if(data.type==='stopped'){emitPart();release().then(()=>queue).finally(onDone);}
    };
    node.onprocessorerror=()=>{if(active){active=false;onError(new Error('ระบบรับเสียงขัดข้อง กรุณาเริ่มบันทึกใหม่'));emitPart();release().then(()=>queue).finally(onDone);}};
    source=context.createMediaStreamSource(stream);gain=context.createGain();gain.gain.value=0;
    source.connect(node);node.connect(gain);gain.connect(context.destination);await context.resume();
    timer=setInterval(()=>{if(active)node.port.postMessage('split');},partMillis);
    for(const track of stream.getAudioTracks())track.onended=()=>{if(active){onError(new Error('ไมโครโฟนหยุดทำงาน'));stop();}};
    navigator.wakeLock?.request('screen').then(lock=>{if(active)wakeLock=lock;else lock.release().catch(()=>{});}).catch(()=>{});
  } catch(error){active=false;await release();throw error;}
  return {stop,pause(){if(!active||paused)return;paused=true;node.port.postMessage('pause');stream.getAudioTracks().forEach(t=>t.enabled=false);},resume(){if(!active||!paused)return;paused=false;stream.getAudioTracks().forEach(t=>t.enabled=true);node.port.postMessage('resume');},get active(){return active;},get paused(){return paused;}};
}

// Decode a compressed file (MP3/M4A) in the browser and re-encode it as the WAV the analyzer expects:
// mono, 16 kHz, 16-bit PCM. Decoding cannot restore detail the compression already removed.
export async function toWav16k(file){
  const context=new AudioContext({sampleRate:16000});
  try{
    let decoded;
    try{decoded=await context.decodeAudioData(await file.arrayBuffer());}
    catch{throw new Error(`เปิดไฟล์ ${file.name} ไม่ได้ ลองแปลงเป็น WAV ก่อนอัปโหลด`);}
    const samples=new Float32Array(decoded.length);
    for(let c=0;c<decoded.numberOfChannels;c++){const channel=decoded.getChannelData(c);for(let i=0;i<samples.length;i++)samples[i]+=channel[i]/decoded.numberOfChannels;}
    return pcmWav(samples);
  }finally{await context.close().catch(()=>{});}
}
