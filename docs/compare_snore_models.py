"""Compare classic ML baselines with the Dense heads on the same snore/non-snore split.

Uses the Kaggle part of artifacts/snore_v2/split-manifest.json (train 693 / validation 149 / test 149),
verifies every clip by SHA-256, extracts 521 YAMNet class scores with artifacts/yamnet_base.tflite,
tunes each model's hyperparameters on validation only, and touches test once at the end.

Usage: .venv/bin/python docs/compare_snore_models.py --data "/path/to/folder containing 'Snoring Dataset'"
"""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import confusion_matrix,accuracy_score,precision_score,recall_score,f1_score,roc_auc_score,roc_curve
from train import load_audio,extract_mobile_scores
from predict import interpreter

parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=Path.home()/'.cache/kagglehub/datasets/tareqkhanemu/snoring/versions/1')
args=parser.parse_args()
OUT=ROOT/'results/model-comparison';OUT.mkdir(parents=True,exist_ok=True)
manifest=[r for r in json.loads((ROOT/'artifacts/snore_v2/split-manifest.json').read_text()) if r['source']=='kaggle_snoring_v1']

cache=OUT/'features.npz'
if cache.exists():features=np.load(cache)['features']
else:
    clips=[]
    for r in manifest:
        a=load_audio(args.data/r['file'])
        if hashlib.sha256(a.tobytes()).hexdigest()!=r['audio_sha256']:raise SystemExit(f"SHA-256 mismatch: {r['file']}")
        clips.append(a)
    features=extract_mobile_scores(ROOT/'artifacts/yamnet_base.tflite',np.stack(clips));np.savez_compressed(cache,features=features)
y=np.array([r['label'] for r in manifest]);split=np.array([r['split'] for r in manifest])
tr,va,te=(np.flatnonzero(split==s) for s in ['train','validation','test'])
print('split',{s:dict(n=int(np.sum(split==s)),snore=int(np.sum(y[split==s]==1)),not_snore=int(np.sum(y[split==s]==0))) for s in ['train','validation','test']})

grids={
 'Logistic Regression':[dict(C=c) for c in [.01,.1,1,10]],
 'Decision Tree':[dict(max_depth=d,min_samples_leaf=l) for d in [3,5,10,None] for l in [1,5]],
 'k-NN':[dict(n_neighbors=k,weights=w) for k in [1,3,5,7,11,15] for w in ['uniform','distance']],
 'Random Forest':[dict(n_estimators=300,max_depth=d,min_samples_leaf=l) for d in [None,10] for l in [1,3]],
 'SVM (RBF)':[dict(C=c,probability=True) for c in [.1,1,10]],
}
def build(name,p):
    if name=='Logistic Regression':return make_pipeline(StandardScaler(),LogisticRegression(max_iter=5000,random_state=42,**p))
    if name=='Decision Tree':return DecisionTreeClassifier(random_state=42,**p)
    if name=='k-NN':return make_pipeline(StandardScaler(),KNeighborsClassifier(**p))
    if name=='Random Forest':return RandomForestClassifier(random_state=42,n_jobs=-1,**p)
    return make_pipeline(StandardScaler(),SVC(random_state=42,**p))

def summary(prob,cut,idx):
    pred=(prob>=cut).astype(int);t=y[idx]
    return dict(accuracy=accuracy_score(t,pred),precision=precision_score(t,pred,zero_division=0),recall=recall_score(t,pred,zero_division=0),f1=f1_score(t,pred,zero_division=0),
                roc_auc=roc_auc_score(t,prob),confusion_matrix=confusion_matrix(t,pred,labels=[0,1]).tolist())

results={};probs={}
for name,grid in grids.items():
    scored=[]
    for p in grid:
        m=build(name,p).fit(features[tr],y[tr]);vp=m.predict_proba(features[va])[:,1]
        scored.append((accuracy_score(y[va],vp>=.5),f1_score(y[va],vp>=.5),p))
    va_acc,va_f1,best=max(scored,key=lambda s:(s[0],s[1]))
    m=build(name,best).fit(features[tr],y[tr]);tp=m.predict_proba(features[te])[:,1]
    results[name]=dict(params={k:v for k,v in best.items() if k!='probability'},threshold=.5,validation_accuracy=va_acc,validation_f1=va_f1,test=summary(tp,.5,te),trained_on='train 693 (this split)')
    probs[name]=tp;print(name,best,'val',round(va_acc,4),'test',round(results[name]['test']['accuracy'],4),flush=True)

def head(path,cut,label,note):
    it,i,o=interpreter(path,[1,521],[1,1])
    def run(idx):
        out=[]
        for f in features[idx]:it.set_tensor(i,f.reshape(1,521).astype(np.float32));it.invoke();out.append(float(it.get_tensor(o)[0,0]))
        return np.array(out)
    vp,tp=run(va),run(te)
    results[label]=dict(params='Dense(64,ReLU)→Dropout(0.2)→Dense(1,sigmoid)',threshold=cut,validation_accuracy=accuracy_score(y[va],vp>=cut),validation_f1=f1_score(y[va],vp>=cut),test=summary(tp,cut,te),trained_on=note)
    probs[label]=tp;print(label,'val',round(results[label]['validation_accuracy'],4),'test',round(results[label]['test']['accuracy'],4))
metrics_v2=json.loads((ROOT/'artifacts/snore_v2/metrics.json').read_text())
head(ROOT/'artifacts/snore_v2/snore_score_head.tflite',metrics_v2['threshold'],'Dense head v2 (web)','train 725 = this train split + 32 breathing clips')
head(ROOT/'artifacts/snore_score_head.tflite',.63,'Dense head v1 (old)','original split unknown; may overlap this validation/test')

# Best = highest validation accuracy among models trained on this split (v1 excluded: its training split is unknown).
eligible={k:v for k,v in results.items() if not k.startswith('Dense head v1')}
best=max(eligible,key=lambda k:(eligible[k]['validation_accuracy'],eligible[k]['validation_f1']))
(OUT/'metrics.json').write_text(json.dumps(dict(features='521 YAMNet class scores (yamnet_base.tflite), 15,600-sample first-second window',
  split={s:dict(n=int(np.sum(split==s)),snore=int(np.sum(y[split==s]==1)),not_snore=int(np.sum(y[split==s]==0))) for s in ['train','validation','test']},
  selection='Hyperparameters and best model chosen by validation accuracy (tie: validation F1); test evaluated once.',best_by_validation=best,models=results),indent=2,default=float))
import csv
with (OUT/'test-predictions.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['file','label','audio_sha256',*probs]);[w.writerow([manifest[i]['file'],y[i],manifest[i]['audio_sha256'],*[round(float(probs[k][j]),6) for k in probs]]) for j,i in enumerate(te)]

import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':12})
fig,ax=plt.subplots(figsize=(7,7))
for name,p in probs.items():
    fpr,tpr,_=roc_curve(y[te],p);ax.plot(fpr,tpr,lw=2.5 if name==best else 1.4,label=f"{name} (AUC {results[name]['test']['roc_auc']:.3f})")
ax.plot([0,1],[0,1],'--',color='#999',lw=1);ax.set_xlabel('False positive rate');ax.set_ylabel('True positive rate (snore recall)');ax.set_title('ROC on test set (149 clips)');ax.legend(loc='lower right',fontsize=9);fig.tight_layout();fig.savefig(OUT/'roc-test.png',dpi=200)
print('best by validation:',best,json.dumps(results[best]['test'],default=float))
