"""Verify v3 web actually applies the local model, matching Python on public demo."""
from pathlib import Path
import argparse,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/snore-v3';OUT.mkdir(exist_ok=True,parents=True)
parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:18077');args=parser.parse_args()
reference=json.loads((OUT/'demo-candidate.json').read_text());checks=[]
def check(name,value):
 checks.append(dict(case=name,passed=bool(value)));print(name,bool(value),flush=True);assert value,name
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True);page=browser.new_page(viewport=dict(width=1440,height=1000));page.set_default_timeout(120000)
 errors=[];posts=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:posts.append(r.url) if r.method=='POST' else None)
 page.goto(args.url,wait_until='networkidle')
 check('test build clearly labeled',page.locator('.experiment-banner').is_visible())
 check('idle page does not show false recording banner',page.locator('.record-banner').count()==0)
 page.locator('#audio-file').set_input_files(str(ROOT/'deployments/snoresens-vercel/dist/samples/demo-45s.wav'))
 page.wait_for_function("location.hash.startsWith('#report/')");page.locator('.analysis-method').wait_for()
 check('report identifies experimental v3','รุ่นทดลอง 3' in page.locator('.analysis-method').inner_text())
 with page.expect_download() as captured:page.locator('[data-action="export-json"]').click()
 path=OUT/'web-v3-analysis.json';captured.value.save_as(path);result=json.loads(path.read_text())
 check('real 2250 cell inference',len(result['timeline'])==2250 and result['summary']['model_version']=='experimental-snore-v3-local-verifier')
 check('labels match Python',[r['prediction'] for r in result['timeline']]==[r['prediction'] for r in reference['timeline']])
 check('event boundaries match Python',result['snore_events']==reference['snore_events'])
 check('local verifier scores match Python',max(abs(a['v3_local_probability']-b['v3_local_probability']) for a,b in zip(result['timeline'],reference['timeline']) if a['v3_local_probability'] is not None)<.0001)
 check('v3 never adds a v2 negative cell',all(r['prediction']!='snore' or r['v2_prediction']=='snore' for r in result['timeline']))
 check('latest breathing checklist retained',page.locator('[data-action="open-checklist"]').count()==1)
 page.reload(wait_until='networkidle');page.locator('.analysis-method').wait_for();check('v3 persists after reload','รุ่นทดลอง 3' in page.locator('.analysis-method').inner_text())
 page.set_viewport_size(dict(width=390,height=844));check('mobile no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.screenshot(path=str(OUT/'v3-preview-mobile.png'),full_page=True)
 check('no JS errors',not errors);check('no audio POSTs',not posts);browser.close()
(OUT/'web-preview-checks.json').write_text(json.dumps(dict(url=args.url,checks=checks,errors=errors,audio_posts=posts),ensure_ascii=False,indent=2))
