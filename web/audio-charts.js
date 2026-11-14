/* Bounded canvas plots; raw measurements remain in JSON/CSV exports. */
(function(root) {
  function sampledPitch(rows, seconds, limit = 600) {
    if (!rows.length || seconds <= 0) return [];
    const count = Math.min(limit, rows.length);
    const bins = Array.from({length:count}, () => ({sum:0,count:0}));
    for (const row of rows) {
      if (!Number.isFinite(row.pitch_hz)) continue;
      const index = Math.max(0,Math.min(count-1,Math.floor(row.start_seconds / seconds * count)));
      bins[index].sum += row.pitch_hz; bins[index].count++;
    }
    return bins.map((bin,i) => ({x:(i+0.5)*seconds/count,y:bin.count ? bin.sum/bin.count : null}));
  }
  function spectralColor(value) {
    if (!Number.isFinite(value)) return [237,240,233];
    const stops = [[17,24,39],[34,94,168],[65,182,196],[255,255,217]];
    const position = Math.max(0,Math.min(1,(value+110)/90))*3;
    const index = Math.min(2,Math.floor(position)), fraction = position-index;
    return stops[index].map((v,i) => Math.round(v+(stops[index+1][i]-v)*fraction));
  }
  function drawSpectrogram(canvas, data) {
    const matrix = data.values_db, height = matrix.length, width = matrix[0]?.length ?? 0;
    if (!height || !width) return;
    const buffer = document.createElement('canvas'); buffer.width=width;buffer.height=height;
    const context = buffer.getContext('2d'), pixels = context.createImageData(width,height);
    for (let f=0;f<height;f++) for(let t=0;t<width;t++) {
      const rgb=spectralColor(matrix[f][t]), offset=((height-1-f)*width+t)*4;
      pixels.data.set([...rgb,255],offset);
    }
    context.putImageData(pixels,0,0);
    const output=canvas.getContext('2d');output.imageSmoothingEnabled=false;
    output.drawImage(buffer,0,0,canvas.width,canvas.height);
  }
  function drawSeries(canvas, points, maxX, minY, maxY) {
    const ctx=canvas.getContext('2d');ctx.fillStyle='#edf0e9';ctx.fillRect(0,0,canvas.width,canvas.height);
    if (!(maxX>0) || !(maxY>minY)) return;
    const y=value => canvas.height-(value-minY)/(maxY-minY)*canvas.height;
    ctx.strokeStyle='#b6c6bc';ctx.lineWidth=1;
    for(const value of [minY,(minY+maxY)/2,maxY]) {ctx.beginPath();ctx.moveTo(0,y(value));ctx.lineTo(canvas.width,y(value));ctx.stroke();}
    ctx.strokeStyle='#247f69';ctx.lineWidth=3;ctx.beginPath();let active=false;
    for(const point of points) {
      if (!Number.isFinite(point.y)) {active=false;continue;}
      const x=point.x/maxX*canvas.width, level=y(Math.max(minY,Math.min(maxY,point.y)));
      if(active)ctx.lineTo(x,level);else ctx.moveTo(x,level);active=true;
    }
    ctx.stroke();
    ctx.fillStyle='#247f69';
    for(const point of points) if(Number.isFinite(point.y)) {
      ctx.beginPath();ctx.arc(point.x/maxX*canvas.width,y(Math.max(minY,Math.min(maxY,point.y))),2,0,Math.PI*2);ctx.fill();
    }
  }
  const api={sampledPitch,spectralColor,drawSpectrogram,drawSeries};
  if(typeof module!=='undefined')module.exports=api;else root.SanorAudioCharts=api;
})(typeof window==='undefined'?globalThis:window);
