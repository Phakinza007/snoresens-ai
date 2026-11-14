// Hosted version: use the unchanged YAMNet TFLite base and exported trained heads.
// Audio stays in the browser. Single-thread WASM also works without cross-origin isolation.
let ready;
import {analysisPlan,isSnore,activityThreshold} from './temporal.mjs';
const round=(value,digits=3)=>Number(value.toFixed(digits));
function denseHead(scores,head){
  const hidden=new Float64Array(head.bias);
  for(let i=0;i<521;i++)for(let j=0;j<64;j++)hidden[j]+=scores[i]*head.kernel[i*64+j];
  let output=head.output_bias;
  for(let j=0;j<64;j++)output+=Math.max(0,hidden[j])*head.output_kernel[j];
  return 1/(1+Math.exp(-output));
}
async function loadModels(notify){
  if(!ready)ready=(async()=>{
    notify('กำลังโหลดโมเดลลงอุปกรณ์ครั้งแรก...');
    await tf.setBackend('cpu');await tf.ready();tflite.setWasmPath('/vendor/');
    const response=await fetch('/models/heads.json');if(!response.ok)throw new Error('โหลดโมเดลไม่สำเร็จ กรุณาลองใหม่');
    const heads=await response.json();
    const base=await tflite.loadTFLiteModel('/models/yamnet_base.tflite',{numThreads:1});
    return {base,heads};
  })().catch(error=>{ready=null;throw error;});
  return ready;
}
async function decode(blob){
  const buffer=await blob.arrayBuffer(),view=new DataView(buffer);
  const text=(start,n)=>new TextDecoder().decode(new Uint8Array(buffer,start,n));
  if(buffer.byteLength<44||text(0,4)!=='RIFF'||text(8,4)!=='WAVE')throw new Error('รองรับไฟล์ WAV เท่านั้น');
  let format,channelCount,rate,bits,start,size;
  for(let at=12;at+8<=buffer.byteLength;){
    const tag=text(at,4),length=view.getUint32(at+4,true),data=at+8;
    if(data+length>buffer.byteLength)throw new Error('ข้อมูลใน WAV ไม่ครบ');
    if(tag==='fmt '&&length>=16){format=view.getUint16(data,true);channelCount=view.getUint16(data+2,true);rate=view.getUint32(data+4,true);bits=view.getUint16(data+14,true);}
    if(tag==='data'){start=data;size=length;break;}
    at=data+length+(length%2);
  }
  if(start===undefined||!size)throw new Error('ไฟล์เสียงไม่มีข้อมูล');
  // Preserve PCM16/16kHz values exactly; avoid a 48kHz round-trip before inference.
  if(format===1&&bits===16&&rate===16000&&channelCount>=1){
    const samples=new Float32Array(Math.floor(size/(channelCount*2)));
    for(let i=0;i<samples.length;i++){let x=0;for(let c=0;c<channelCount;c++)x+=view.getInt16(start+(i*channelCount+c)*2,true)/32768;samples[i]=x/channelCount;}
    return samples;
  }
  const context=new AudioContext({sampleRate:16000});
  try{const decoded=await context.decodeAudioData(buffer);const samples=new Float32Array(decoded.length);for(let c=0;c<decoded.numberOfChannels;c++){const channel=decoded.getChannelData(c);for(let i=0;i<samples.length;i++)samples[i]+=channel[i]/decoded.numberOfChannels;}return samples;}
  finally{await context.close();}
}
function percentile(values,p){if(!values.length)return null;const a=[...values].sort((x,y)=>x-y),at=(a.length-1)*p;return a[Math.floor(at)]+(a[Math.ceil(at)]-a[Math.floor(at)])*(at%1);}
export async function analyzeInBrowser(blob,notify=()=>{}){
  const samples=await decode(blob);if(!samples.length)throw new Error('ไฟล์เสียงไม่มีข้อมูล');
  const {base,heads}=await loadModels(notify);const timeline=[],events=[],levels=[];let snoreSeconds=0,start=null,meanRmsSum=0,maxRms=0;
  const cells=[...analysisPlan(samples.length)];
  const local=cells.map(cell=>{let power=0;for(let i=cell.at;i<cell.at+cell.length;i++)power+=samples[i]*samples[i];const rms=Math.sqrt(power/cell.length);return {rms,dbfs:rms>0?20*Math.log10(rms):null};});
  const parentLevels=[...analysisPlan(samples.length,1600)].map(cell=>{let power=0;for(let i=cell.at;i<cell.at+cell.length;i++)power+=samples[i]*samples[i];return power>0?10*Math.log10(power/cell.length):null;});
  const floor=activityThreshold(parentLevels);
  let frame=0,cachedContext=-1,cachedScores;
  for(const cell of cells){
    const {at,contextStart}=cell,segment=samples.subarray(at,at+cell.length),seconds=segment.length/16000;
    const input=new Float32Array(15600);input.set(samples.subarray(contextStart,Math.min(samples.length,contextStart+15600)));
    const tensor=contextStart===cachedContext?null:tf.tensor1d(input);let raw;
    try{
      if(tensor){raw=base.predict(tensor);const output=Array.isArray(raw)?raw[0]:raw.dataSync?raw:Object.values(raw)[0];cachedScores=Float32Array.from(output.dataSync());cachedContext=contextStart;}
      const scores=cachedScores,probability=denseHead(scores,heads.snore),cough=denseHead(scores,heads.cough);
      const {rms,dbfs}=local[frame];
      const parentDbfs=parentLevels[Math.floor(at/1600)],parentPass=Number.isFinite(parentDbfs)&&parentDbfs>=floor;
      const positive=parentPass&&isSnore(probability,dbfs,heads.snore_threshold,floor);
      timeline.push({start_seconds:round(at/16000),duration_seconds:round(seconds),snore_probability:round(probability,6),cough_probability:round(cough,6),yamnet_cough_score:round(scores[42],6),yamnet_breathing_score:round(scores[36],6),yamnet_snoring_score:round(scores[38],6),rms_dbfs:dbfs===null?null:round(dbfs,2),prediction:positive?'snore':'non_snore',activity_floor_dbfs:round(floor,2),activity_pass:parentPass&&dbfs!==null&&dbfs>=floor,parent_rms_dbfs:parentDbfs===null?null:round(parentDbfs,2),analysis_hop_seconds:.02,context_start_seconds:round(contextStart/16000),context_end_seconds:round(Math.min(samples.length,contextStart+15600)/16000)});
      if(positive){snoreSeconds+=seconds;meanRmsSum+=rms*seconds;maxRms=Math.max(maxRms,rms);if(dbfs!==null)levels.push(dbfs);if(start===null)start=at/16000;}
      else if(start!==null){events.push({start_seconds:round(start),end_seconds:round(at/16000),duration_seconds:round(at/16000-start)});start=null;}
    }finally{tensor?.dispose();if(raw)tf.dispose(raw);}
    if(frame++%50===0){notify(`วิเคราะห์ละเอียด ${round((at+segment.length)/16000,1)}/${round(samples.length/16000,1)} วินาที`);await new Promise(resolve=>setTimeout(resolve,0));}
  }
  const duration=samples.length/16000;
  if(start!==null)events.push({start_seconds:round(start),end_seconds:round(duration),duration_seconds:round(duration-start)});
  const mean=snoreSeconds?meanRmsSum/snoreSeconds:null;
  return {summary:{recording_seconds:round(duration),detected_snore_seconds:round(snoreSeconds),snore_percent_of_recording:round(snoreSeconds/duration*100,2),snore_event_count:events.length,longest_snore_event_seconds:Math.max(0,...events.map(e=>e.duration_seconds)),snore_median_rms_dbfs:levels.length?round(percentile(levels,.5),2):null,snore_p95_rms_dbfs:levels.length?round(percentile(levels,.95),2):null,snore_mean_rms:mean,snore_max_rms:snoreSeconds?maxRms:null,snore_mean_rms_dbfs:mean>0?round(20*Math.log10(mean),2):null,snore_max_rms_dbfs:maxRms>0?round(20*Math.log10(maxRms),2):null,threshold:heads.snore_threshold,model_version:heads.model_version,analysis_hop_seconds:.02,model_hop_seconds:.1,segmentation_version:'micro-20ms-v1',model_context_seconds:.975,activity_floor_dbfs:round(floor,2),activity_gate_note:'Experimental 20 ms boundary and 100 ms parent energy gate; may miss soft snoring. Not a breathing classifier.',interpretation:'Audio snore estimate only; not medical severity.',level_note:'Relative digital dBFS; not calibrated dB SPL.'},snore_events:events,timeline,inference:{runtime:'TFLite WASM + exported trained Dense heads',model_version:heads.model_version,decision_hop_seconds:.02,model_hop_seconds:.1,segmentation_version:'micro-20ms-v1',context_seconds:.975,activity_gate:'max(-60, P20 + min(6,(P95-P20)/2)) dBFS over finite 100 ms parents >= -80; 20 ms cells must also pass',temporal_accuracy_validated:false,device:'browser',audio_uploaded:false,advanced_python_analysis_available:false}};
}
