"""Run local HTTP/inference checks and prepare a clearly attributed demo candidate.

Run from the project root: .venv/bin/python docs/check_phase3_readiness.py
Does not retrain models, open a browser, or change application behavior.
"""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web_server import Handler, ThreadingHTTPServer

OUT = ROOT / 'results/phase3-readiness'
OUT.mkdir(parents=True, exist_ok=True)
demo_dir = OUT / 'demo'
demo_dir.mkdir(exist_ok=True)
audio, sr = sf.read(ROOT / 'test_snore_16k.wav', dtype='float32')
assert sr == 16000 and audio.ndim == 1
silence = np.zeros(5 * sr, dtype=np.float32)
demo = np.concatenate([silence, audio[:15*sr], silence, audio[23*sr:38*sr], silence])
sf.write(demo_dir / 'demo-candidate-45s.wav', demo, sr, subtype='PCM_16')
sf.write(demo_dir / 'digital-silence-6s.wav', np.zeros(6*sr), sr, subtype='PCM_16')
rng = np.random.default_rng(182)
sf.write(demo_dir / 'synthetic-noise-6s.wav', rng.normal(0, .025, 6*sr), sr, subtype='PCM_16')
(demo_dir / 'README.md').write_text('''# Demo candidate — requires listening review

45-second edited demonstration, not a natural continuous sleep recording or accuracy dataset.
Source: test_snore_16k.wav, derived from Tongue base snoring by Langenbergstefan.
Source URL: https://commons.wikimedia.org/wiki/File:Tongue_base_snoring.ogg
License: CC BY-SA 3.0, https://creativecommons.org/licenses/by-sa/3.0/
Changes: conversion to mono 16 kHz WAV (existing source), two crops, inserted digital silence.
This derived demo is distributed under CC BY-SA 3.0.

| Demo time (s) | Content |
|---|---|
| 0–5 | Inserted digital silence |
| 5–20 | Source 0–15 seconds; listen and annotate before assigning labels |
| 20–25 | Inserted digital silence |
| 25–40 | Source 23–38 seconds; listen and annotate before assigning labels |
| 40–45 | Inserted digital silence |

digital-silence-6s.wav and synthetic-noise-6s.wav are generated engineering controls.
Synthetic noise is seeded Gaussian noise, not traffic or bedroom noise.
Model predictions are not ground-truth labels. No human snore timestamps are supplied yet.
''', encoding='utf-8')

rows = []
server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f'http://127.0.0.1:{server.server_port}'

def request(path, data=None, headers=None):
    start = time.perf_counter()
    try:
        with urlopen(Request(base + path, data=data, headers=headers or {}), timeout=600) as response:
            return response.status, response.read(), time.perf_counter()-start
    except HTTPError as error:
        return error.code, error.read(), time.perf_counter()-start

def record(name, passed, actual, seconds):
    rows.append(dict(case=name, status='PASS' if passed else 'FAIL', actual=actual, seconds=round(seconds, 3)))

try:
    for path in ['/', '/app.js', '/measurements.js', '/audio-charts.js', '/style.css']:
        code, body, seconds = request(path)
        record('GET '+path, code == 200 and len(body)>0, f'HTTP {code}, {len(body)} bytes', seconds)
    for name, file, expected_duration in [
        ('existing-sample', ROOT/'test_snore_16k.wav', len(audio)/sr),
        ('demo-candidate', demo_dir/'demo-candidate-45s.wav', 45),
        ('digital-silence', demo_dir/'digital-silence-6s.wav', 6),
        ('synthetic-noise', demo_dir/'synthetic-noise-6s.wav', 6),
    ]:
        code, body, seconds = request('/api/analyze', file.read_bytes(), {'Content-Type':'audio/wav'})
        result = json.loads(body)
        (OUT/f'{name}-analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        summary = result.get('summary', {})
        measured = summary.get('recording_seconds', -1)
        passed = code == 200 and abs(measured-expected_duration)<.001 and bool(result.get('timeline'))
        if name == 'digital-silence':
            passed = passed and summary.get('detected_snore_seconds') == 0
        actual = f'HTTP {code}; duration={measured}; detected_snore_seconds={summary.get("detected_snore_seconds")}; events={summary.get("snore_event_count")}'
        record(name, passed, actual, seconds)
    for name, data, headers, expected in [
        ('invalid-format', b'not a WAV', {}, 400),
        ('empty-upload', b'', {}, 413),
        ('invalid-settings', b'not a WAV', {'X-Min-Quiet-Gap-Seconds':'wrong'}, 400),
    ]:
        code, body, seconds = request('/api/analyze', data, headers)
        record(name, code == expected, f'HTTP {code}: {body.decode()[:200]}', seconds)
    code, body, seconds = request('/api/apnea-status')
    result = json.loads(body)
    record('research-model-status', code == 200 and result.get('status') == 'not_trained', json.dumps(result,ensure_ascii=False), seconds)
finally:
    server.shutdown()
    server.server_close()
    thread.join()

with (OUT/'http-checks.csv').open('w') as f:
    writer=csv.DictWriter(f, fieldnames=['case','status','actual','seconds'])
    writer.writeheader()
    writer.writerows(rows)

models=[]
for label, filename, report_key, matrix_key in [
    ('Snore embedding classifier','metrics.json','report','confusion_matrix'),
    ('Snore score classifier — web inference','mobile_metrics.json','report','confusion_matrix'),
    ('Cough classifier — separate task','cough_metrics.json','test_report','test_confusion_matrix'),
]:
    path=ROOT/'artifacts'/filename
    data=json.loads(path.read_text())
    models.append(dict(model=label, accuracy=data[report_key]['accuracy'], test=data['test'],
                       threshold=data['threshold'], matrix=data[matrix_key], evidence=str(path.relative_to(ROOT)),
                       sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(OUT/'saved-model-metrics.json').write_text(json.dumps(models,indent=2), encoding='utf-8')
node_log=Path('/tmp/sanor-phase3-node-tests.log')
if node_log.exists(): shutil.copy2(node_log,OUT/'node-tests.log')
(OUT/'http-checks.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
for row in rows: print(row['status'], row['case'], row['actual'])
print(f'HTTP checks: {sum(r["status"] == "PASS" for r in rows)}/{len(rows)}')
if any(r['status']=='FAIL' for r in rows): raise SystemExit(1)
