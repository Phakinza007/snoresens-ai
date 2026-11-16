// Experimental 200 ms verifier. Must match local_snore.py; scores are not calibrated confidence.
export function localWindow(audio,center){
  const start=Math.max(0,Math.min(Math.floor(center)-1600,audio.length-3200)),x=new Float32Array(3200);
  x.set(audio.subarray(start,Math.min(audio.length,start+3200)));return x;
}
const bands=Array.from({length:40},(_,i)=>{
  const lo=Math.exp(Math.log(40)+i*(Math.log(7600)-Math.log(40))/40),hi=Math.exp(Math.log(40)+(i+1)*(Math.log(7600)-Math.log(40))/40);
  return Array.from({length:257},(_,k)=>k).filter(k=>k*16000/512>=lo&&k*16000/512<hi);
});
function fft(re,im){
  for(let i=1,j=0;i<512;i++){let bit=256;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j)[re[i],re[j]]=[re[j],re[i]];}
  for(let size=2;size<=512;size*=2){const angle=-2*Math.PI/size;
    for(let at=0;at<512;at+=size)for(let j=0;j<size/2;j++){
      const a=at+j,b=a+size/2,c=Math.cos(angle*j),s=Math.sin(angle*j),r=re[b]*c-im[b]*s,q=re[b]*s+im[b]*c;
      re[b]=re[a]-r;im[b]=im[a]-q;re[a]+=r;im[a]+=q;
    }
  }
}
export function localFeatures(audio){
  const x=Float64Array.from(audio),mean=x.reduce((a,b)=>a+b,0)/x.length;let peak=0;
  for(let i=0;i<x.length;i++){x[i]-=mean;peak=Math.max(peak,Math.abs(x[i]));}
  if(peak>0)for(let i=0;i<x.length;i++)x[i]/=peak;
  const logs=Array.from({length:40},()=>[]);
  for(let at=0;at+400<=x.length;at+=160){
    const re=new Float64Array(512),im=new Float64Array(512);
    for(let i=0;i<400;i++)re[i]=x[at+i]*(.5-.5*Math.cos(2*Math.PI*i/400))/200;
    fft(re,im);
    const powers=bands.map(ids=>ids.reduce((sum,k)=>sum+re[k]*re[k]+im[k]*im[k],0)),total=powers.reduce((a,b)=>a+b,0)+1e-12;
    powers.forEach((v,i)=>logs[i].push(Math.log(Math.max(v/total,1e-8))));
  }
  const means=logs.map(a=>a.reduce((s,x)=>s+x,0)/a.length),std=logs.map((a,i)=>Math.sqrt(a.reduce((s,x)=>s+(x-means[i])**2,0)/a.length));
  return Float32Array.from([...means,...std]);
}
export function localProbability(audio,config){
  const f=localFeatures(audio);let z=config.bias;
  for(let i=0;i<80;i++)z+=(f[i]-config.mean[i])/config.scale[i]*config.weights[i];
  return 1/(1+Math.exp(-Math.max(-60,Math.min(60,z))));
}
