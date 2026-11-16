"""Opt-in local experiment. Never changes the deployed/default snore pipeline."""
from pathlib import Path
import sys,argparse,json,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from predict import load_wave,summarize
from local_snore import local_window,local_features
parser=argparse.ArgumentParser();parser.add_argument('wav',type=Path);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
run=subprocess.run([sys.executable,str(ROOT/'predict.py'),str(args.wav.resolve()),'--include-timeline','--no-spectral'],check=True,capture_output=True,text=True)
original=json.loads(run.stdout);rows=original['timeline'];audio=load_wave(args.wav)
config=json.loads((ROOT/'artifacts/experimental_snore_v3/verifier.json').read_text());threshold=config['threshold'];decisions=[];local=[]
for row in rows:
 if row['prediction']=='snore':
  x=local_features(local_window(audio,round((row['start_seconds']+row['duration_seconds']/2)*16000)))
  logit=float(np.dot((x-config['mean'])/config['scale'],config['weights'])+config['bias']);p=float(1/(1+np.exp(-np.clip(logit,-60,60))))
 else:p=None
 local.append(p);decisions.append(row['prediction']=='snore' and p>=threshold)
summary,events,timeline=summarize([x['snore_probability'] for x in rows],[x.get('yamnet_cough_score',0) for x in rows],[x.get('cough_probability') for x in rows],[x['duration_seconds'] for x in rows],[x['rms_dbfs'] for x in rows],original['summary']['threshold'],decisions)
for old,new,p in zip(rows,timeline,local):
 old.update(prediction=new['prediction'],v3_local_probability=p,v3_local_threshold=threshold)
summary.update(model_version='experimental-snore-v3-local-verifier',analysis_hop_seconds=.02,model_context_seconds=.975,verifier_context_seconds=.2,weakly_supervised=True,temporal_accuracy_validated=False)
result=dict(summary=summary,snore_events=events,timeline=rows,baseline_summary=original['summary'],experimental=True,limitations='200 ms positive cores inherit clip labels; no human event validation. May miss snoring. Not the deployed model.')
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
