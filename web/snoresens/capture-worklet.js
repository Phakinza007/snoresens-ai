// Capture mono PCM, including digital silence, without compressed-container timestamps.
class SnoresensCapture extends AudioWorkletProcessor {
  constructor() {
    super();this.buffer=new Float32Array(4096);this.used=0;this.running=true;this.paused=false;
    this.port.onmessage=event=>{
      if(event.data==='pause'){this.flush();this.paused=true;}
      if(event.data==='resume')this.paused=false;
      if(event.data==='split'||event.data==='stop'){
        this.flush();this.port.postMessage({type:event.data==='stop'?'stopped':'boundary'});
        if(event.data==='stop')this.running=false;
      }
    };
  }
  flush(){if(this.used){const samples=this.buffer.slice(0,this.used);this.port.postMessage({type:'samples',samples},[samples.buffer]);this.used=0;}}
  process(inputs,outputs) {
    if(!this.running)return false;
    if(this.paused)return true;
    const channels=inputs[0];const length=outputs[0]?.[0]?.length||128;
    for(let i=0;i<length;i++){
      let sample=0;
      if(channels.length){for(const channel of channels)sample+=channel[i]||0;sample/=channels.length;}
      this.buffer[this.used++]=sample;
      if(this.used===this.buffer.length)this.flush();
    }
    return true;
  }
}
registerProcessor('snoresens-capture',SnoresensCapture);
