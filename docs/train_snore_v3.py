"""Fixed-design local verifier experiment; original deployed model is untouched.

Train labels on positive 200 ms cores are weak clip labels, NOT human onset labels.
Threshold uses validation only. Old test is explicitly diagnostic. Previously
unused people are a separate breathing-only robustness check, not event validation.
"""
from pathlib import Path
import sys,json,hashlib,pickle
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from local_snore import local_window,local_features,balanced_file_weights
from predict import load_wave,interpreter
from temporal_segmentation import analysis_windows,activity_threshold
from train import load_audio
OUT=ROOT/'experiments/snore-v3';OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'artifacts/snore_v2/split-manifest.json').read_text())
groups={split:{r['person_id'] for r in manifest if r['split']==split and r.get('person_id')} for split in ('train','validation','test')}
for a,b in [('train','validation'),('train','test'),('validation','test')]:
 assert not groups[a]&groups[b],'Participant leakage'
DATA=Path.home()/'.cache/kagglehub/datasets/tareqkhanemu/snoring/versions/1'
policy=dict(local_context_seconds=.2,boundary_hop_seconds=.02,model='StandardScaler + LogisticRegression(C=1, effective class/file balanced, seed=42)',positive_labels='weak: loudest 200 ms core inherits positive clip label',negative_labels='Kaggle negative clip label and full prompted breathing recordings',threshold_policy='validation-only: minimum 95% recall of v2-positive Kaggle snore cores; maximize full validation breathing rejection',production_promotion='requires independently human-timestamped validation; no automatic promotion',old_test_policy='diagnostic, previously inspected; never train or select threshold on test',design_frozen_before_test=True)
(OUT/'policy.json').write_text(json.dumps(policy,indent=2))
X=[];y=[];splits=[];weights=[];sources=[];seen={};cores=[]
for row in manifest:
 path=DATA/row['file'] if row['source']=='kaggle_snoring_v1' else ROOT/row['file']
 a=load_audio(path) if row['source']=='kaggle_snoring_v1' else load_wave(path)
 digest=hashlib.sha256(a.tobytes()).hexdigest()
 if digest in seen:assert seen[digest]==row['split'],'Cross-split duplicate'
 seen[digest]=row['split']
 if row['source']=='kaggle_snoring_v1':
  # Choose the energetic core deterministically without model/test outcomes.
  energy=np.convolve(a.astype(float)**2,np.ones(3200),mode='valid');center=int(np.argmax(energy))+1600 if len(a)>=3200 else len(a)//2
  centers=[center] if row['label'] else list(range(1600,max(1601,len(a)),3200))
  cores.append(dict(row,center=center))
 else:centers=list(range(1600,max(1601,len(a)),3200))
 for center in centers:
  X.append(local_features(local_window(a,center)));y.append(row['label']);splits.append(row['split'])
  weights.append(1/len(centers));sources.append(row['source'])
 print('features',len(X),row['split'],flush=True) if len(X)%1000<5 else None
X=np.array(X);y=np.array(y);splits=np.array(splits);weights=np.array(weights);sources=np.array(sources)
train=splits=='train';val=splits=='validation'
pipe=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000,random_state=42))
pipe.fit(X[train],y[train],logisticregression__sample_weight=balanced_file_weights(y[train],weights[train]));pickle.dump(pipe,(OUT/'verifier.pkl').open('wb'))
# Evaluate the frozen original model directly, with no private feature-cache dependency.
import tensorflow as tf
base,bi,bo=interpreter(ROOT/'artifacts/yamnet_base.tflite',[15600],[1,521])
head,hi,ho=interpreter(ROOT/'artifacts/snore_v2/snore_score_head.tflite',[1,521],[1,1])
threshold_v2=json.loads((ROOT/'artifacts/snore_v2/metrics.json').read_text())['threshold']
def original(scores):
 head.set_tensor(hi,np.asarray(scores,dtype=np.float32).reshape(1,521));head.invoke();return float(head.get_tensor(ho)[0,0])
core_lookup={r['file']:r for r in cores}
def clip_prediction(row):
 a=load_audio(DATA/row['file']);center=core_lookup[row['file']]['center'];p=float(pipe.predict_proba(local_features(local_window(a,center))[None])[0,1])
 base.set_tensor(bi,a[:15600]);base.invoke();v2=original(base.get_tensor(bo))
 return dict(file=row['file'],split=row['split'],label=row['label'],v2_probability=v2,local_probability=p)
clip_rows=[clip_prediction(row) for row in manifest if row['source']=='kaggle_snoring_v1' and row['split']!='test']
def file_rows(row):
 a=load_wave(ROOT/row['file']);parent=[]
 for at in range(0,len(a),1600):
  e=np.mean(a[at:at+1600].astype(float)**2);parent.append(10*np.log10(e) if e>0 else None)
 floor=activity_threshold(parent);last=-1;p=0;rows=[]
 for at,cell,context,offset in analysis_windows(a):
  if offset!=last:
   base.set_tensor(bi,context);base.invoke();p=original(base.get_tensor(bo));last=offset
  energy=np.mean(cell.astype(float)**2);level=10*np.log10(energy) if energy>0 else None
  active=level is not None and level>=floor and parent[at//1600] is not None and parent[at//1600]>=floor
  old=p>=threshold_v2 and active
  lp=float(pipe.predict_proba(local_features(local_window(a,at+len(cell)//2))[None])[0,1]) if old else 0
  rows.append(dict(start=at/16000,duration=len(cell)/16000,v2_positive=bool(old),local_probability=lp))
 return dict(file=row['file'],split=row['split'],seconds=len(a)/16000,rows=rows)
validation=[file_rows(r) for r in manifest if r['source']=='coswara_breathing' and r['split']=='validation']
positive=[r['local_probability'] for r in clip_rows if r['split']=='validation' and r['label']==1 and r['v2_probability']>=threshold_v2]
choices=np.arange(.01,.991,.01)
valid=[float(t) for t in choices if np.mean(np.array(positive)>=t)>=.95]
# Increasing gate threshold monotonically rejects more breathing; tie keeps recall.
def score(t):
 fp=sum(x['duration'] for r in validation for x in r['rows'] if x['v2_positive'] and x['local_probability']>=t)
 return (-fp,float(np.mean(np.array(positive)>=t)),-t)
t=float(max(valid,key=score)) if valid else 0.
(OUT/'threshold.json').write_text(json.dumps(dict(threshold=t,validation_positive_cores=len(positive),policy=policy),indent=2))
print('FROZEN threshold',t,flush=True)
# Test evaluation starts here, after threshold is frozen.
clip_rows.extend(clip_prediction(row) for row in manifest if row['source']=='kaggle_snoring_v1' and row['split']=='test')
legacy=[file_rows(r) for r in manifest if r['source']=='coswara_breathing' and r['split']=='test']
known={r['person_id'] for r in manifest if r.get('person_id')}
fresh_paths=[p for p in (ROOT/'data/coswara/Extracted_data').rglob('breathing-*.wav') if p.parent.name not in known]
fresh=[file_rows(dict(file=str(p.relative_to(ROOT)),split='fresh_breathing')) for p in sorted(fresh_paths)]
def report(records):
 return dict(files=len(records),seconds=sum(r['seconds'] for r in records),v2_false_seconds=sum(x['duration'] for r in records for x in r['rows'] if x['v2_positive']),candidate_false_seconds=sum(x['duration'] for r in records for x in r['rows'] if x['v2_positive'] and x['local_probability']>=t),files_with_candidate_false=sum(any(x['v2_positive'] and x['local_probability']>=t for x in r['rows']) for r in records))
clips={}
for split in ['validation','test']:
 r=[x for x in clip_rows if x['split']==split];actual=[x['label'] for x in r];v2=[x['v2_probability']>=threshold_v2 for x in r];v3=[a and x['local_probability']>=t for a,x in zip(v2,r)]
 clips[split]=dict(v2_matrix=confusion_matrix(actual,v2).tolist(),candidate_matrix=confusion_matrix(actual,v3).tolist())
metrics=dict(policy=policy,threshold=t,training_windows=int(train.sum()),validation_windows=int(val.sum()),clip_core_diagnostics=clips,validation_breathing=report(validation),legacy_breathing_diagnostic=report(legacy),fresh_breathing_robustness=report(fresh),fresh_people=len({p.parent.name for p in fresh_paths}),production_changed=False)
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2));(OUT/'breathing-rows.json').write_text(json.dumps(validation+legacy+fresh));(OUT/'clip-predictions.json').write_text(json.dumps(clip_rows,indent=2))
scaler=pipe.named_steps['standardscaler'];lr=pipe.named_steps['logisticregression']
(OUT/'verifier.json').write_text(json.dumps(dict(feature_version='relative-logbands-200ms-v1',mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),weights=lr.coef_[0].tolist(),bias=float(lr.intercept_[0]),threshold=t)))
print(json.dumps(metrics,indent=2),flush=True)

z=(X[val]-scaler.mean_)/scaler.scale_;portable=1/(1+np.exp(-np.clip(z@lr.coef_[0]+lr.intercept_[0],-60,60)))
assert np.max(np.abs(portable-pipe.predict_proba(X[val])[:,1]))<1e-6
print('Portable verifier parity passed',flush=True)
