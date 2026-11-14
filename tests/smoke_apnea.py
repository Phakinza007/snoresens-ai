"""Exercise data preparation and training with generated audio only, in a temp folder."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np
import soundfile as sf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from apnea_research import ResearchModel


def write_csv(path, rows):
    with path.open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    with tempfile.TemporaryDirectory(prefix='sanor-apnea-synthetic-') as folder:
        root=Path(folder);recordings=[];events=[];coverage=[]
        rng=np.random.default_rng(42)
        for split in ('train','validation','test'):
            for person in (1,2):
                identity=f'synthetic-{split}-{person}';rate=8000;t=np.arange(30*rate)/rate
                # Deliberately artificial classes; these are NOT apnea simulations or clinical data.
                audio=np.concatenate((rng.normal(0,0.08,len(t)),0.1*np.sin(2*np.pi*(200+person*40)*t)+rng.normal(0,0.003,len(t))))
                sf.write(root/f'{identity}.wav',audio,rate,subtype='PCM_16')
                recordings.append(dict(recording_id=identity,audio_path=f'{identity}.wav',person_id=identity,
                    night_id=identity+'-night',split=split,reference='PSG',alignment_verified='true'))
                events.append(dict(recording_id=identity,start_seconds=35,end_seconds=50,event_type='obstructive_apnea'))
                coverage.append(dict(recording_id=identity,start_seconds=0,end_seconds=60))
        write_csv(root/'recordings.csv',recordings);write_csv(root/'events.csv',events);write_csv(root/'scored_sleep.csv',coverage)
        prepared=subprocess.run([sys.executable,str(ROOT/'prepare_apnea.py'),str(root/'recordings.csv'),str(root/'events.csv'),
                                 str(root/'scored_sleep.csv'),'--out',str(root/'clinical-format-fixture.csv')],capture_output=True,text=True,check=True)
        with (root/'clinical-format-fixture.csv').open() as file: rows=list(csv.DictReader(file))
        assert len(rows)==12
        for row in rows:row['reference']='SYNTHETIC'
        write_csv(root/'synthetic.csv',rows)
        trained=subprocess.run([sys.executable,str(ROOT/'train_apnea.py'),str(root/'synthetic.csv'),'--out',str(root/'model'),
                                '--synthetic-test-data'],capture_output=True,text=True,check=True)
        report=json.loads(trained.stdout);assert report['validation_status']=='synthetic_only'
        try:ResearchModel(root/'model')
        except ValueError:pass
        else:raise AssertionError('Synthetic artifact accepted for user audio')
        research=ResearchModel(root/'model',allow_synthetic=True).analyze(root/recordings[0]['audio_path'])
        assert len(research['windows'])==2 and research['risk_percent'] is None
        assert all(window['status']=='scored' for window in research['windows'])
        print('PASS: 12 generated windows -> preparation -> training -> numeric artifact -> inference; synthetic artifact rejected for user audio.')


if __name__=='__main__':main()
