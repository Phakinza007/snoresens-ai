"""Train a fresh head with participant-disjoint breathing negatives.

Preserves original models. Threshold selection uses validation only, never test.
"""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report,confusion_matrix
from train import collect_data,split_indices,extract_mobile_scores
from train_cough import collect,split_people,loudest_window
from predict import load_wave,interpreter

OUT=ROOT/'experiments/snore-v2';OUT.mkdir(parents=True,exist_ok=True)
tf.keras.utils.set_random_seed(42)
dataset=Path.home()/'.cache/kagglehub/datasets/tareqkhanemu/snoring/versions/1'
if not dataset.is_dir():
    raise SystemExit('Download tareqkhanemu/snoring dataset version 1 with KaggleHub before running this training script.')
clips,labels,names,duplicates=collect_data(dataset)
k_splits=split_indices(labels)
paths,cy,people=collect(ROOT/'data/coswara/Extracted_data',ROOT/'data/coswara/annotations')
c_splits=split_people(cy,people)
features=[];ys=[];domains=[];splits=[];manifest=[]
cache=OUT/'features.npz'
for split,ids in zip(['train','validation','test'],k_splits):
    for i in ids:manifest.append(dict(source='kaggle_snoring_v1',file=names[i],label=int(labels[i]),split=split,audio_sha256=hashlib.sha256(clips[i].tobytes()).hexdigest(),person_id=None));ys.append(int(labels[i]));domains.append('kaggle');splits.append(split)
ordered_clips=[clips[i] for ids in k_splits for i in ids]
for split,ids in zip(['train','validation','test'],c_splits):
    for i in ids:
        if not paths[i].name.startswith('breathing-'):continue
        a=loudest_window(load_wave(paths[i]));ordered_clips.append(a)
        manifest.append(dict(source='coswara_breathing',file=str(paths[i].relative_to(ROOT)),label=0,split=split,audio_sha256=hashlib.sha256(a.tobytes()).hexdigest(),person_id=str(people[i])));ys.append(0);domains.append('breathing');splits.append(split)
(OUT/'split-manifest.json').write_text(json.dumps(manifest,indent=2))
for a,b in [('train','validation'),('train','test'),('validation','test')]:
    assert not {x['audio_sha256'] for x in manifest if x['split']==a}&{x['audio_sha256'] for x in manifest if x['split']==b}
    assert not {x['person_id'] for x in manifest if x['split']==a and x['person_id']}&{x['person_id'] for x in manifest if x['split']==b and x['person_id']}
fingerprint=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
if cache.exists() and (OUT/'feature-fingerprint.txt').read_text()==fingerprint:features=np.load(cache)['features']
else:
    features=extract_mobile_scores(ROOT/'artifacts/yamnet_base.tflite',np.stack(ordered_clips));np.savez_compressed(cache,features=features);(OUT/'feature-fingerprint.txt').write_text(fingerprint)
y=np.array(ys);domains=np.array(domains);splits=np.array(splits);train=np.flatnonzero(splits=='train');val=np.flatnonzero(splits=='validation');test=np.flatnonzero(splits=='test')
weights=np.where(domains[train]=='breathing',10.0,1.0)
model=tf.keras.Sequential([tf.keras.layers.Input((521,)),tf.keras.layers.Dense(64,activation='relu'),tf.keras.layers.Dropout(.2),tf.keras.layers.Dense(1,activation='sigmoid')])
model.compile(optimizer=tf.keras.optimizers.Adam(.001),loss='binary_crossentropy')
model.fit(features[train],y[train],sample_weight=weights,validation_data=(features[val],y[val],np.where(domains[val]=='breathing',10.0,1.0)),epochs=60,batch_size=32,callbacks=[tf.keras.callbacks.EarlyStopping(monitor='val_loss',patience=8,restore_best_weights=True)],verbose=2)
vp=model(features[val],training=False).numpy().ravel()
def score_threshold(threshold):
    pred=vp>=threshold;recall=float(np.mean(pred[y[val]==1]));breathing_spec=float(np.mean(~pred[domains[val]=='breathing']));other_spec=float(np.mean(~pred[(domains[val]=='kaggle')&(y[val]==0)]))
    return (min(recall,breathing_spec),(recall+breathing_spec+other_spec)/3,-abs(threshold-.5))
threshold=float(max(np.arange(.10,.951,.01),key=score_threshold))
testp=model(features[test],training=False).numpy().ravel();pred=testp>=threshold
old,oi,oo=interpreter(ROOT/'artifacts/snore_score_head.tflite',[1,521],[1,1]);oldp=[]
for f in features[test]:old.set_tensor(oi,f.reshape(1,521));old.invoke();oldp.append(float(old.get_tensor(oo)[0,0]))
oldp=np.array(oldp)
metrics=dict(version='snore-v2-breathing-negatives',threshold=threshold,threshold_policy='Validation-only max-min of snore recall and breathing specificity; tie-break mean domain recall then proximity to 0.5',seed=42,kaggle_dataset_version=1,exact_kaggle_duplicates_removed=duplicates,features='521 YAMNet class scores',window_samples=15600,training_policy='Fresh Dense head; no warm start from original head; breathing sample weights 10, others 1; early stopping weighted validation loss',manifest_sha256=fingerprint,
 limitations='Prompted breathing clips, not bedside recordings. Kaggle person IDs unavailable. Old head original split identity is unknown, so old Kaggle results below are diagnostic, not an unbiased before-after benchmark.',splits={s:{d:int(np.sum((splits==s)&(domains==d))) for d in ['kaggle','breathing']} for s in ['train','validation','test']})
for name,p,cut in [('v1',oldp,.63),('v2',testp,threshold)]:
    reports={}
    for d in ['all','kaggle','breathing']:
        mask=np.ones(len(test),dtype=bool) if d=='all' else domains[test]==d
        reports[d]={'confusion_matrix':confusion_matrix(y[test][mask],p[mask]>=cut,labels=[0,1]).tolist(),'report':classification_report(y[test][mask],p[mask]>=cut,labels=[0,1],output_dict=True,zero_division=0)}
    metrics[name]=reports
model.save(OUT/'snore_score_head.keras')
(OUT/'snore_score_head.tflite').write_bytes(tf.lite.TFLiteConverter.from_keras_model(model).convert())
w=model.get_weights();(OUT/'browser-head.json').write_text(json.dumps(dict(kernel=w[0].flatten().tolist(),bias=w[1].tolist(),output_kernel=w[2].flatten().tolist(),output_bias=float(w[3][0])),separators=(',',':')))
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2));(OUT/'test-predictions.json').write_text(json.dumps([dict(**manifest[i],v1_probability=float(a),v2_probability=float(b)) for i,a,b in zip(test,oldp,testp)],indent=2))
print(json.dumps(metrics,indent=2),flush=True)
