"""Build an isolated static v3 test app using the deployed checklist UI as its base."""
from pathlib import Path
import shutil,json,subprocess,re
ROOT=Path(__file__).resolve().parents[1];target=ROOT/'deployments/snoresens-v3-preview';dist=target/'dist';target.mkdir(exist_ok=True)
base=ROOT/'deployments/snoresens-vercel'
shutil.copytree(base/'dist',dist,dirs_exist_ok=True)
for name in ['vercel.json','.vercelignore']:shutil.copy2(base/name,target/name)
for name in ['app.mjs','checklist.mjs','style.css']:
 content=subprocess.check_output(['git','show',f'origin/deploy/risk-assessment-20ms:deployments/snoresens-vercel/dist/app-assets/{name}'],cwd=ROOT)
 (dist/'app-assets'/name).write_bytes(content)
shutil.copy2(ROOT/'web/snoresens/local-snore.mjs',dist/'app-assets/local-snore.mjs')
shutil.copy2(ROOT/'artifacts/experimental_snore_v3/verifier.json',dist/'models/local-verifier.json')
runtime=(base/'dist/app-assets/browser-inference.mjs').read_text()
runtime="import {localWindow,localProbability} from './local-snore.mjs';\n"+runtime
runtime=runtime.replace('return {base,heads};',"const verifier=await(await fetch('/models/local-verifier.json')).json();return {base,heads,verifier};")
runtime=runtime.replace('const {base,heads}=await loadModels(notify);','const {base,heads,verifier}=await loadModels(notify);')
runtime=runtime.replace('const positive=parentPass&&isSnore(probability,dbfs,heads.snore_threshold,floor);',"const baseline=parentPass&&isSnore(probability,dbfs,heads.snore_threshold,floor);\n      const localScore=baseline?localProbability(localWindow(samples,at+Math.floor(cell.length/2)),verifier):null;\n      const positive=baseline&&localScore>=verifier.threshold;")
runtime=runtime.replace("prediction:positive?'snore':'non_snore'","v2_prediction:baseline?'snore':'non_snore',v3_local_probability:localScore,v3_local_threshold:verifier.threshold,prediction:positive?'snore':'non_snore'")
runtime=runtime.replace('model_version:heads.model_version',"model_version:'experimental-snore-v3-local-verifier',weakly_supervised:true,verifier_context_seconds:.2")
(dist/'app-assets/browser-inference.mjs').write_text(runtime)
app=(dist/'app-assets/app.mjs').read_text()
app=app.replace("${isV2?'โมเดลรุ่น 2 · เพิ่มตัวอย่างเสียงหายใจ':'ผลจากโมเดลรุ่นเดิม'}", "${s.model_version==='experimental-snore-v3-local-verifier'?'รุ่นทดลอง 3 · ตัวตรวจเสียงเฉพาะจุด':isV2?'โมเดลรุ่น 2 · เพิ่มตัวอย่างเสียงหายใจ':'ผลจากโมเดลรุ่นเดิม'}")
app=re.sub(r'function banner\(\)\{return (.*?);\}',lambda m:"function banner(){return '<div class=\"experiment-banner\">รุ่นทดลอง 3 · อาจตัดเสียงกรนบางช่วงออก · ยังไม่ยืนยันขอบเขตจากคนฟัง</div>'+ ("+m.group(1)+");}",app)
(dist/'app-assets/app.mjs').write_text(app)
with (dist/'app-assets/style.css').open('a') as f:f.write('\n.experiment-banner{background:#fff1d8;border:1px solid #ead2a4;border-radius:14px;padding:12px 16px;margin-bottom:20px;font-size:13px;line-height:1.7;color:#614416}\n')
info=json.loads((dist/'models/model-info.json').read_text());info.update(version='experimental-snore-v3-local-verifier',weakly_supervised=True,verifier_context_seconds=.2,verifier_threshold=json.loads((dist/'models/local-verifier.json').read_text())['threshold'],temporal_accuracy_validated=False)
(dist/'models/model-info.json').write_text(json.dumps(info,indent=2))
(dist/'build-info.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),ui_base='deploy/risk-assessment-20ms',experimental=True),indent=2))
for name in ('vercel.json','.vercelignore'):shutil.copy2(ROOT/'deployments/snoresens-vercel'/name,target/name)
print('Isolated v3 test app built. Original static app untouched.')
