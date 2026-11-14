"""Evaluate the existing cough test split and chart saved snore results.

Run from project root with .venv/bin/python docs/prepare_phase3_evidence.py.
Never trains, tunes thresholds, or overwrites model artifacts.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from train_cough import collect, split_people, extract_scores
from predict import interpreter

OUT = ROOT/'results/phase3-evidence'
SLIDES = ROOT/'exports/phase3-evidence'
OUT.mkdir(parents=True, exist_ok=True)
SLIDES.mkdir(parents=True, exist_ok=True)
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'artifacts').iterdir() if p.is_file()}
saved = {name:json.loads((ROOT/'artifacts'/name).read_text()) for name in ['metrics.json','mobile_metrics.json','cough_metrics.json']}

paths,y,groups=collect(ROOT/'data/coswara/Extracted_data',ROOT/'data/coswara/annotations')
train,val,test=split_people(y,groups)
old=saved['cough_metrics.json']
relative=[str(paths[i].relative_to(ROOT)) for i in test]
assert relative == old['test_files'], 'Reconstructed test list differs; do not silently evaluate another split'
scores,_=extract_scores([paths[i] for i in test],ROOT/'artifacts/yamnet_base.tflite')
head,head_in,head_out=interpreter(ROOT/'artifacts/cough_score_head.tflite',[1,521],[1,1])
probs=[]
for score in scores:
    head.set_tensor(head_in,score.reshape(1,521).astype(np.float32));head.invoke()
    probs.append(float(head.get_tensor(head_out)[0,0]))
probs=np.array(probs)
pred=probs >= old['threshold']
report=classification_report(y[test],pred,output_dict=True,zero_division=0)
cm=confusion_matrix(y[test],pred,labels=[0,1]).tolist()
fpr,tpr,thresholds=roc_curve(y[test],probs)
new=dict(date='2026-11-14',model='Existing cough TFLite head',threshold=old['threshold'],threshold_policy='Frozen saved validation threshold; no fitting or tuning',
    train=len(train),validation=len(val),test=len(test),people=len(set(groups)),samples=len(paths),
    test_list_matches_saved=True,confusion_matrix=cm,report=report,auc=float(roc_auc_score(y[test],probs)),
    matches_saved_confusion_matrix=cm==old['test_confusion_matrix'],
    limitation='Prompted cough vs breathing/counting, participant-disjoint split; no bedroom/snore negatives or event timestamps.')
(OUT/'cough-reevaluation.json').write_text(json.dumps(new,indent=2))
with (OUT/'cough-test-predictions.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['file','person_id','true_label','probability','predicted_label','audio_sha256'])
    for i,prob,decision in zip(test,probs,pred):writer.writerow([str(paths[i].relative_to(ROOT)),groups[i],int(y[i]),float(prob),int(decision),hashlib.sha256(paths[i].read_bytes()).hexdigest()])
split=[]
for name,ids in [('train',train),('validation',val),('test',test)]:
    for i in ids:split.append(dict(file=str(paths[i].relative_to(ROOT)),person_id=groups[i],label=int(y[i]),split=name))
(OUT/'cough-split-manifest.json').write_text(json.dumps(split,indent=2))

audit=dict(date='2026-11-14',snore=dict(status='Cannot reproduce original test evaluation from current local evidence',
    model_files_present=['yamnet_base.tflite','snore_head.keras','snore_score_head.keras','snore_score_head.tflite'],
    dataset_991_clips_found=False,test_files_manifest_present=(ROOT/'artifacts/test_files.json').exists(),
    seed_in_current_train_script=42,missing=['Original labeled snoring dataset/version','Saved original test file list and audio hashes','Frozen original preprocessing/split provenance'],
    note='Seed 42 alone does not prove original file ordering or exact original split. Current train.py metric schema also differs from saved metrics.json. Downloading a current copy would not by itself verify the original split.'),
    cough=dict(status='Reevaluated existing TFLite on matching saved 42-file test list',samples=len(paths),people=len(set(groups)),train=len(train),validation=len(val),test=len(test),
        exact_test_path_list_matches=True,person_sets_disjoint=not bool(set(groups[train])&set(groups[test]) or set(groups[val])&set(groups[test]) or set(groups[train])&set(groups[val])),
        source_audio_hashes_recorded_now=True,original_audio_hashes_available=False),
    artifact_sha256_before=hashes)
assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'artifacts').iterdir() if p.is_file()}
audit['model_artifacts_unchanged']=True
(OUT/'data-audit.json').write_text(json.dumps(audit,indent=2))

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
NAVY='#0E1633';TEAL='#247F69'
def finish(fig,name):
    fig.savefig(SLIDES/f'{name}.png',dpi=180,facecolor='white')
    fig.savefig(SLIDES/f'{name}.svg',facecolor='white')
    plt.close(fig)

def draw_matrix(ax,matrix,title,classes):
    matrix=np.array(matrix)
    ax.imshow(matrix,cmap='GnBu',vmin=0,vmax=max(75,int(matrix.max())))
    for i in range(2):
        for j in range(2):
            ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=35,fontweight='bold',color='white' if matrix[i,j]>40 else NAVY)
    ax.set_xticks([0,1],classes);ax.set_yticks([0,1],classes)
    ax.set_xlabel('Predicted class',labelpad=12);ax.set_ylabel('Actual class',labelpad=12)
    ax.set_title(title,pad=18,fontsize=16,fontweight='bold')
    for spine in ax.spines.values():spine.set_visible(False)

fig,ax=plt.subplots(figsize=(12,6.75));fig.subplots_adjust(left=.22,right=.82,bottom=.20,top=.78)
draw_matrix(ax,saved['mobile_metrics.json']['confusion_matrix'],'Web model: 146 / 149 correct (97.99%)',['Non-snore','Snore'])
fig.text(.05,.93,'SANOR / SNORE CLASSIFICATION',fontsize=21,fontweight='bold',color=NAVY)
fig.text(.05,.055,'Saved evaluation • test n = 149 • threshold = 0.63\nRandom clip split; no participant IDs or bedroom validation.',fontsize=12,color='#444444')
finish(fig,'01-web-snore-confusion-matrix')

fig,axes=plt.subplots(1,2,figsize=(12,6.75));fig.subplots_adjust(left=.13,right=.95,bottom=.23,top=.76,wspace=.55)
draw_matrix(axes[0],saved['metrics.json']['confusion_matrix'],'Embedding head · 100.00%',['Non-snore','Snore'])
draw_matrix(axes[1],saved['mobile_metrics.json']['confusion_matrix'],'Score head / web · 97.99%',['Non-snore','Snore'])
fig.text(.05,.93,'SAVED SNORE MODEL COMPARISON',fontsize=23,fontweight='bold',color=NAVY)
fig.text(.05,.055,'Each saved report: test n = 149 (74 non-snore / 75 snore).\nOriginal split manifest is missing: exact sample identity across models is not independently verified.',fontsize=12,color='#444444')
finish(fig,'02-snore-confusion-matrices')

comparison=[]
for name,key,feature,threshold in [('Embedding head','metrics.json','1024-D embeddings',.36),('Score head (web)','mobile_metrics.json','521 class scores',.63)]:
    m=saved[key];r=m['report']['1']
    comparison.append(dict(model=name,features=feature,train=m['train'],validation=m['validation'],test=m['test'],accuracy_pct=100*m['report']['accuracy'],snore_precision_pct=100*r['precision'],snore_recall_pct=100*r['recall'],snore_f1_pct=100*r['f1-score'],roc_auc=m['auc'],threshold=m['threshold'],evidence='Saved evaluation; not rerun',source='artifacts/'+key))
with (SLIDES/'snore-model-comparison.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=comparison[0].keys());w.writeheader();w.writerows(comparison)
fig,ax=plt.subplots(figsize=(12,6.75));ax.axis('off')
columns=['Model','Features','Accuracy','Precision¹','Recall¹','F1¹','AUC','Decision\nthreshold']
cell=[[r['model'],r['features'],f"{r['accuracy_pct']:.2f}%",f"{r['snore_precision_pct']:.2f}%",f"{r['snore_recall_pct']:.2f}%",f"{r['snore_f1_pct']:.2f}%",f"{r['roc_auc']:.3f}",f"{r['threshold']:.2f}"] for r in comparison]
table=ax.table(cellText=cell,colLabels=columns,cellLoc='center',colWidths=[.18,.20,.12,.11,.10,.10,.08,.10],bbox=[0,.30,1,.40])
table.auto_set_font_size(False);table.set_fontsize(12)
for (r,c),cell_obj in table.get_celld().items():
    cell_obj.set_edgecolor('white');cell_obj.set_linewidth(3)
    cell_obj.set_facecolor(NAVY if r==0 else '#E8F1EE' if r==2 else '#F2F4F7')
    if r==0:cell_obj.set_text_props(color='white',weight='bold')
fig.text(.055,.88,'TWO SNORE CLASSIFIERS, ONE DEPLOYED IN THE WEB',fontsize=21,fontweight='bold',color=NAVY)
fig.text(.055,.15,'¹ Positive class = snore. Values are saved test results, not fresh measurements.\nTrain / validation / test = 693 / 149 / 149 in both reports. Exact shared split is unverified.\nThese are model variants, not evidence of improvement after Phase 2.',fontsize=12,color='#444444')
finish(fig,'03-snore-model-comparison-table')

fig,ax=plt.subplots(figsize=(12,6.75));fig.subplots_adjust(left=.22,right=.82,bottom=.20,top=.78)
draw_matrix(ax,cm,f"Cough head: {sum(np.diag(cm))} / 42 correct ({report['accuracy']*100:.2f}%)",['Other','Cough'])
fig.text(.05,.93,'SUPPLEMENTARY TASK / COUGH REEVALUATION',fontsize=21,fontweight='bold',color=NAVY)
fig.text(.05,.055,'Rerun 14 Nov 2026 • saved threshold = 0.51 • same saved test path list\nParticipant-disjoint prompted clips; not a snore-model comparison or bedside validation.',fontsize=12,color='#444444')
finish(fig,'04-cough-reevaluation-confusion-matrix')
fig,ax=plt.subplots(figsize=(10,6.75));fig.subplots_adjust(left=.13,bottom=.21,top=.80)
ax.plot(fpr,tpr,color=TEAL,lw=3,label=f"Cough head (AUC = {new['auc']:.3f})")
ax.plot([0,1],[0,1],color='#A0A0A0',ls='--',label='Chance')
ax.set(xlim=(0,1),ylim=(0,1.03),xlabel='False positive rate',ylabel='True positive rate',title='Cough ROC — fresh 42-file test inference')
ax.legend(loc='lower right');ax.grid(alpha=.2)
fig.text(.06,.06,'Supplementary task only • fixed saved model • no threshold tuning on test\nNot a comparison of the snore models.',fontsize=12,color='#444444')
finish(fig,'05-cough-reevaluation-roc')

(SLIDES/'README.md').write_text('''# Phase 3 slide assets

Generated 14 Nov 2026 with `docs/prepare_phase3_evidence.py`. PNG files are high-resolution; SVG files are vector.

- 01: deployed web snore classifier confusion matrix (saved result).
- 02: both snore confusion matrices side by side (saved results).
- 03: snore model comparison table; CSV is also supplied.
- 04–05: supplementary cough task, freshly reevaluated using its saved 42-file test list and threshold.

Snore results are NOT freshly reevaluated. Both report 149 test clips, but the missing original split manifest prevents verification of exact shared test identities. Do not present these as Phase 2 → Phase 3 improvement.
Cough is a different task/dataset and must not be ranked against snore classifiers. The cough rerun confirms the saved paths and currently available audio, but original audio hashes were not saved.
Rows of all confusion matrices = actual labels; columns = predictions. Class 0 is non-snore/other; class 1 is snore/cough.
No snore ROC curve is generated: original per-example scores are unavailable.
Full fresh cough evidence, predictions, split manifest, hashes and data audit: `results/phase3-evidence/`.
''',encoding='utf-8')
print(json.dumps(new,indent=2));print('Charts:',SLIDES)
