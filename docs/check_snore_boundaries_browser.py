"""Check deployed 20 ms boundaries, including reanalysis of a real stored v1 fixture.

Uses an isolated browser profile. No personal browser data is read or changed.
"""
from pathlib import Path
import argparse,json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--url',default='https://snoresens-ai-int182.vercel.app');args=parser.parse_args()
OUT=ROOT/'results/segmentation-debug';OUT.mkdir(parents=True,exist_ok=True)
fixture=json.loads((ROOT/'tests/fixtures/demo-v1-analysis.json').read_text())
reference=json.loads((OUT/'demo-micro20-python.json').read_text())
checks=[];errors=[];posts=[]
def check(name,result):
    checks.append(dict(case=name,passed=bool(result)));print(name,bool(result),flush=True);assert result,name
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=2,reduced_motion='reduce');page.set_default_timeout(120000)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda request:posts.append(request.url) if request.method=='POST' else None)
    page.goto(args.url,wait_until='networkidle');page.get_by_role('heading',name='คืนนี้ ฟังการนอนของคุณ').wait_for()
    info=page.evaluate("async()=>await(await fetch('/models/model-info.json')).json()")
    check('published model is v2 with 20 ms boundary cells',info['version']=='snore-v2-breathing-negatives' and info['decision_hop_seconds']==.02)
    page.evaluate('''async analysis=>{
      const {saveRecord}=await import('/app-assets/store.mjs');
      await saveRecord({id:'legacy-v1',name:'demo-candidate-45s.wav',createdAt:'2026-11-14T05:00:00Z',isSample:true,analysis,audio:await(await fetch('/samples/demo-45s.wav')).blob()});
    }''',fixture)
    page.goto(args.url+'/#report/legacy-v1');page.reload(wait_until='networkidle');page.locator('.assessment').wait_for()
    check('old result retains 1 second version label','รุ่นเดิม' in page.locator('.analysis-method').inner_text() and '1 วินาที' in page.locator('.analysis-method').inner_text())
    page.locator('[data-action="reanalyze"]').click()
    page.wait_for_function("location.hash.startsWith('#report/')&&!location.hash.endsWith('legacy-v1')")
    page.wait_for_function("document.querySelector('.analysis-method')?.textContent.includes('รุ่น 2')")
    with page.expect_download() as captured:page.locator('[data-action="export-json"]').click()
    result_path=OUT/'production-micro20-analysis.json';captured.value.save_as(result_path);result=json.loads(result_path.read_text())
    check('old audio was really reanalyzed into 2250 cells',len(result['timeline'])==2250 and result['summary']['analysis_hop_seconds']==.02)
    check('browser and Python decisions agree',[x['prediction'] for x in result['timeline']]==[x['prediction'] for x in reference['timeline']])
    check('browser and Python boundaries agree',result['snore_events']==reference['snore_events'])
    old=json.loads((OUT/'demo-v2-python.json').read_text())
    check('refinement never expands a previously negative 100 ms cell',all(row['prediction']!='snore' or old['timeline'][round(row['start_seconds']*50)//5]['prediction']=='snore' for row in result['timeline']))
    check('subsecond labels are visible' ,'.' in page.locator('.event-row').first.inner_text() and len(page.locator('.event-row').first.inner_text().split('–')[0].split('.')[-1])==2)
    page.wait_for_function("document.querySelector('#report-audio').readyState>=1")
    page.locator('#seek').fill('12.4');page.locator('#detail-timeline').focus();page.keyboard.press('ArrowRight')
    check('zoom allows 0.02 second seeking',abs(float(page.locator('#seek').input_value())-12.42)<.002)
    pixels=page.evaluate("""()=>{const c=document.querySelector('#detail-timeline'),ctx=c.getContext('2d'),start=Number(c.dataset.start),span=Number(c.dataset.span);return [9.02,9.2].map(t=>Array.from(ctx.getImageData(Math.floor((t-start)/span*c.width),30,1,1).data).slice(0,3));}""")
    check('canvas leaves trimmed gap gray and snore blue',pixels==[[231,237,248],[49,87,245]])
    page.screenshot(path=str(OUT/'micro20-report-desktop.png'),full_page=True)
    page.reload(wait_until='networkidle');page.locator('#detail-timeline').wait_for()
    check('v2 result persists','รุ่น 2' in page.locator('.analysis-method').inner_text())
    stored=page.evaluate("async()=>{const {listRecords}=await import('/app-assets/store.mjs');return (await listRecords()).map(r=>({id:r.id,seconds:r.analysis.summary.detected_snore_seconds,rows:r.analysis.timeline.length}));}")
    check('old result remains intact beside the new result',len(stored)==2 and next(r for r in stored if r['id']=='legacy-v1')['rows']==45)
    page.set_viewport_size({'width':390,'height':844});page.locator('.zoom-panel').evaluate('(node)=>window.scrollTo(0,scrollY+node.getBoundingClientRect().top-230)')
    page.screenshot(path=str(OUT/'micro20-zoom-mobile.png'))
    check('mobile has no page overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
    check('no audio uploads',not posts);check('no JavaScript errors',not errors)
    browser.close()
(OUT/'production-micro20-checks.json').write_text(json.dumps(dict(url=args.url,checks=checks,errors=errors,audio_posts=posts),ensure_ascii=False,indent=2))
