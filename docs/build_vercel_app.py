"""Refresh the Vercel static UI from local sources without touching credentials."""
from pathlib import Path
import json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'deployments/snoresens-vercel/dist'
shutil.copytree(ROOT/'web/snoresens',target/'app-assets',dirs_exist_ok=True)
shutil.copy2(ROOT/'web/measurements.js',target/'measurements.js')
html=(ROOT/'web/snoresens/index.html').read_text().replace('  <script src="/measurements.js" defer></script>',
    '  <script src="/vendor/tf-core.min.js" defer></script>\n  <script src="/vendor/tf-backend-cpu.min.js" defer></script>\n  <script src="/vendor/tf-tflite.min.js" defer></script>\n  <script src="/measurements.js" defer></script>')
(target/'index.html').write_text(html)
app=(ROOT/'web/snoresens/app.mjs').read_text()
old="""    const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'audio/wav'},body:blob});
    const analysis=await response.json();if(!response.ok)throw new Error(analysis.error||'วิเคราะห์เสียงไม่ได้');"""
assert old in app
app="import {analyzeInBrowser} from './browser-inference.mjs';\n"+app.replace(old,'    const analysis=await analyzeInBrowser(blob,progress);')
app=app.replace('วิเคราะห์ด้วยเซิร์ฟเวอร์ Sanor บนเครื่องนี้','วิเคราะห์ในเบราว์เซอร์บนอุปกรณ์นี้').replace('เสียงที่อัปโหลดหรืออัดจะประมวลผลผ่านเซิร์ฟเวอร์ Sanor บนเครื่องนี้ ไม่ได้ส่งไปบริการวิเคราะห์ภายนอก','เสียงที่เลือกหรืออัดจะประมวลผลด้วยโมเดลบนอุปกรณ์นี้ ไม่มีการอัปโหลดเสียงไปเซิร์ฟเวอร์')
app=re.sub(r'<a class="text-button" href="/lab".*?</a>','',app)
(target/'app-assets/app.mjs').write_text(app)
heads=json.loads((target/'models/heads.json').read_text())
heads['snore']=json.loads((ROOT/'artifacts/snore_v2/browser-head.json').read_text())
metrics=json.loads((ROOT/'artifacts/snore_v2/metrics.json').read_text())
heads.update(snore_threshold=metrics['threshold'],model_version=metrics['version'])
(target/'models/heads.json').write_text(json.dumps(heads,separators=(',',':')))
(target/'models/model-info.json').write_text(json.dumps(dict(version=metrics['version'],threshold=metrics['threshold'],decision_hop_seconds=.02,model_hop_seconds=.1,segmentation_version="micro-20ms-v1",model_context_seconds=.975,temporal_accuracy_validated=False,classifier_test_reports=metrics['v2'],limitations=metrics['limitations'],activity_gate='Experimental local energy gate; may miss soft snoring; clip classification metrics are not temporal event accuracy.'),indent=2))
print('Vercel UI/model metadata refreshed from local sources; browser inference runtime preserved.')
