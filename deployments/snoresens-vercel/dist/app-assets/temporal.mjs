export const HOP_SAMPLES=1600,CONTEXT_SAMPLES=15600;
export function* analysisPlan(length){
  for(let at=0;at<length;at+=HOP_SAMPLES){
    const size=Math.min(HOP_SAMPLES,length-at),center=at+Math.floor(size/2);
    const contextStart=Math.max(0,Math.min(center-CONTEXT_SAMPLES/2,length-CONTEXT_SAMPLES));
    yield {at,length:size,contextStart};
  }
}
export const isSnore=(probability,dbfs,threshold,floor=-60)=>probability>=threshold&&Number.isFinite(dbfs)&&dbfs>=floor;
export function activityThreshold(levels){
  const a=levels.filter(x=>Number.isFinite(x)&&x>=-80).sort((x,y)=>x-y);
  if(a.length<5)return -60;
  const q=p=>{const at=(a.length-1)*p;return a[Math.floor(at)]+(a[Math.ceil(at)]-a[Math.floor(at)])*(at%1);};
  const low=q(.2),high=q(.95);return Math.max(-60,low+Math.min(6,(high-low)/2));
}
export function eventTime(seconds){
  const tenth=Math.max(0,Math.round(seconds*10)),s=Math.floor(tenth/10);
  return [Math.floor(s/3600),Math.floor(s/60)%60,s%60].map(n=>String(n).padStart(2,'0')).join(':')+'.'+tenth%10;
}
