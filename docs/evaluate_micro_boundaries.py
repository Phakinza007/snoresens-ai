"""Regression evaluation on the existing 14 held-out breathing files. Requires local data."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];baseline=json.loads((root/'results/segmentation-debug/full-breathing-v1-v2.json').read_text());rows=[]
for row in baseline:
 p=subprocess.run([str(root/'.venv/bin/python'),'predict.py',row['file'],'--no-spectral'],capture_output=True,text=True,check=True,cwd=root)
 new=json.loads(p.stdout)['summary']
 rows.append(dict(file=row['file'],recording_seconds=row['recording_seconds'],v2_100ms_seconds=row['v2_snore_seconds'],micro20_seconds=new['detected_snore_seconds']))
 print(len(rows),rows[-1]['micro20_seconds'],flush=True)
(root/'results/segmentation-debug/full-breathing-micro20.json').write_text(json.dumps(dict(rows=rows,before_seconds=round(sum(x['v2_100ms_seconds'] for x in rows),3),after_seconds=round(sum(x['micro20_seconds'] for x in rows),3)),indent=2))
