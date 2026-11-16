"""Browser checks use synthetic annotations in an isolated profile, not human labels."""
from pathlib import Path
import json,csv
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'experiments/snore-v3'
checks=[]
def check(name,value):
 checks.append(dict(case=name,passed=bool(value)));assert value,name
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 page=browser.new_page(viewport=dict(width=390,height=844));errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:18763',wait_until='networkidle');page.locator('#cases option').first.wait_for(state='attached')
 check('review cases load',page.locator('#cases option').count()>10)
 page.wait_for_function("document.querySelector('audio').readyState>=1")
 check('audio can load',page.locator('audio').evaluate('(a)=>a.duration>0'))
 page.locator('#complete').click();check('cannot mark incomplete coverage as complete',not page.locator('#complete').is_checked())
 page.locator('#add').click();check('label must be explicitly selected',page.locator('#intervals li').count()==0 and bool(page.locator('#error').inner_text()))
 page.locator('#label').select_option('other');page.locator('#add').click();check('interval saved',page.locator('#intervals li').count()==1)
 page.locator('#add').click();check('overlap rejected',page.locator('#intervals li').count()==1 and bool(page.locator('#error').inner_text()))
 page.locator('#complete').check();page.reload(wait_until='networkidle');check('annotation persists',page.locator('#complete').is_checked() and page.locator('#intervals li').count()==1)
 page.locator('#reviewer').fill('AUTOMATED-QA-NOT-HUMAN')
 with page.expect_download() as capture:page.locator('#export').click()
 target=OUT/'AUTOMATED-QA-NOT-HUMAN.csv';capture.value.save_as(target)
 rows=list(csv.DictReader(target.open(encoding='utf-8-sig')));case=json.loads((ROOT/'data/snore-v3-review/cases.json').read_text())[0]
 check('CSV uses original source timestamps',len(rows)==1 and abs(float(rows[0]['start_seconds'])-case['source_start'])<.001)
 check('CSV identifies reviewer and completion',rows[0]['reviewer']=='AUTOMATED-QA-NOT-HUMAN' and rows[0]['complete']=='true')
 check('mobile has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 check('no JavaScript errors',not errors);browser.close()
(OUT/'review-browser-checks.json').write_text(json.dumps(dict(synthetic_checks=True,checks=checks),indent=2));print(len(checks),'browser checks passed')
