"""Exercise checklist UI with synthetic answers in an isolated browser profile."""
from pathlib import Path
import argparse,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--url',default='https://snoresens-ai-int182.vercel.app');args=parser.parse_args()
OUT=ROOT/'results/segmentation-debug';OUT.mkdir(parents=True,exist_ok=True)
analysis=json.loads((OUT/'demo-micro20-python.json').read_text())
checks=[];errors=[];posts=[]
def check(name,value):
    checks.append(dict(case=name,passed=bool(value)));print(name,bool(value),flush=True);assert value,name
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport=dict(width=1440,height=1000),device_scale_factor=1,reduced_motion='reduce');page.set_default_timeout(120000)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda req:posts.append(req.url) if req.method=='POST' else None)
    page.goto(args.url,wait_until='networkidle')
    page.evaluate('''async analysis=>{const {saveRecord}=await import('/app-assets/store.mjs');await saveRecord({id:'checklist-qa',name:'synthetic-qa-demo.wav',createdAt:'2026-11-14T10:00:00Z',source:'upload',sessionId:'qa-session',isSample:false,analysis,audio:await(await fetch('/samples/demo-45s.wav')).blob()});}''',analysis)
    page.goto(args.url+'/#report/checklist-qa');page.reload(wait_until='networkidle')
    check('report keeps 20 ms analysis', '0.02' in page.locator('.analysis-method').inner_text())
    page.locator('[data-action="open-checklist"]').click();page.locator('#checklist-form').wait_for()
    check('all five breathing questions render',page.locator('fieldset.check-q').count()==5)
    page.locator('#checklist-form button[type="submit"]').click()
    check('incomplete form cannot save',page.locator('#checklist-form').count()==1 and page.locator('input:invalid').count()>0)
    for field in page.locator('fieldset.check-q').all():
        option=field.locator('input[value="no"]');(option if option.count() else field.locator('input[value="none"]')).check()
    page.locator('input[name="dry_mouth"][value="yes"]').check()
    page.locator('#checklist-form button[type="submit"]').click();page.wait_for_url('**/#report/checklist-qa')
    check('completed checklist returns to report','ผลเช็กลิสต์ตอนเช้า' in page.locator('.check-card').inner_text())
    with page.expect_download() as captured:page.locator('[data-action="export-json"]').click()
    path=OUT/'checklist-qa-export.json';captured.value.save_as(path);export=json.loads(path.read_text())
    check('JSON includes saved answers and computed checklist',export['morning_checklist']['answers']['dry_mouth']=='yes' and export['checklist_result']['symptoms']==['dry_mouth'] and export['checklist_result']['snoring'])
    page.reload(wait_until='networkidle');page.locator('.check-card').wait_for()
    check('checklist survives reload','แนะนำปรึกษาแพทย์' in page.locator('.check-card').inner_text())
    page.locator('[data-action="open-checklist"]').click();page.locator('input[name="witnessed"][value="yes"]').check()
    page.locator('#checklist-form button[type="submit"]').click();page.wait_for_url('**/#report/checklist-qa')
    check('warning response updates displayed result',page.locator('.check-card h2').inner_text()=='ควรพบแพทย์')
    page.locator('[data-action="reanalyze"]').click();page.wait_for_function("location.hash.startsWith('#report/')&&!location.hash.endsWith('checklist-qa')")
    check('checklist survives real 20 ms reanalysis',page.locator('.check-card h2').inner_text()=='ควรพบแพทย์' and '0.02' in page.locator('.analysis-method').inner_text())
    page.set_viewport_size(dict(width=390,height=844));page.locator('.check-card').scroll_into_view_if_needed()
    check('mobile report does not overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    page.screenshot(path=str(OUT/'risk-checklist-mobile.png'),full_page=True)
    page.goto(args.url+'/#history');page.locator('.trend-day').first.wait_for()
    check('history groups reanalysis into the same night',page.locator('.trend-day').count()==1)
    check('no JavaScript errors',not errors);check('no audio or health POSTs',not posts)
    browser.close()
(OUT/'risk-checklist-browser-checks.json').write_text(json.dumps(dict(url=args.url,synthetic_data=True,checks=checks,errors=errors,posts=posts),ensure_ascii=False,indent=2))
