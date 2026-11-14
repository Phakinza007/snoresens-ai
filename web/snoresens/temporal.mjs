export const HOP_SAMPLES=320,CONTEXT_SAMPLES=15600;
export function* analysisPlan(length,hop=HOP_SAMPLES){
  for(let at=0;at<length;at+=hop){
    const size=Math.min(hop,length-at),parent=hop<1600?Math.floor(at/1600)*1600:at,
      center=parent+Math.floor(Math.min(hop<1600?1600:hop,length-parent)/2);
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
  const hundredth=Math.max(0,Math.round(seconds*100)),s=Math.floor(hundredth/100);
  return [Math.floor(s/3600),Math.floor(s/60)%60,s%60].map(n=>String(n).padStart(2,'0')).join(':')+'.'+String(hundredth%100).padStart(2,'0');
}
