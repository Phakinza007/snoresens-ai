"""Capture presentation screenshots from the deployed Site.

Receives Site URL and a short-lived owner QA header over hidden stdin only.
Never saves or prints the credential. Browser storage is isolated from the user.
"""
import json
from pathlib import Path
import sys
import termios
import zipfile
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/demo-presentation'
(OUT/'desktop').mkdir(parents=True,exist_ok=True)
(OUT/'mobile').mkdir(exist_ok=True)
if sys.stdin.isatty():
    settings=termios.tcgetattr(sys.stdin);hidden=settings.copy();hidden[3]&=~termios.ECHO
    termios.tcsetattr(sys.stdin,termios.TCSANOW,hidden)
print('Ready for deployment capture JSON on stdin (input is hidden).',flush=True)
config=json.loads(sys.stdin.readline())
if sys.stdin.isatty():termios.tcsetattr(sys.stdin,termios.TCSANOW,settings)
url=config['url'].rstrip('/');token=config.pop('token',None)
origin=f'{urlsplit(url).scheme}://{urlsplit(url).netloc}'
images=[];errors=[];posts=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
    context=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=2,permissions=['microphone'],reduced_motion='reduce')
    if token:
        context.route(origin+'/**',lambda route:route.continue_(headers={**route.request.headers,'OAI-Sites-Authorization':'Bearer '+token}))
    page=context.new_page();page.set_default_timeout(120000)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda request:posts.append(request.url) if request.method=='POST' else None)
    response=page.goto(url,wait_until='networkidle')
    page.get_by_role('heading',name='คืนนี้ ฟังการนอนของคุณ').wait_for()
    if response.status!=200:raise RuntimeError('Published app did not load successfully')
    def nav(name):
        selector='#side-nav' if page.viewport_size['width']>=800 else '#bottom-nav'
        page.locator(selector).get_by_role('link',name=name,exact=True).click()
        page.wait_for_function("name=>document.querySelector('#side-nav [aria-current=page]')?.textContent.includes(name)",arg=name)
    def action(name):return page.locator(f'[data-action="{name}"]').filter(visible=True)
    def shot(path,title,full=False):
        page.evaluate('document.activeElement?.blur()');page.screenshot(path=str(OUT/path),full_page=full,animations='disabled')
        images.append({'file':path,'title':title});print('Captured:',path,flush=True)
    action('sample').click();page.wait_for_url('**/#report/*');page.locator('.assessment').wait_for()
    # Add the exact 45-second edited demo through the real file picker flow.
    old_url=page.url
    page.locator('#audio-file').set_input_files(str(ROOT/'results/phase3-readiness/demo/demo-candidate-45s.wav'))
    page.wait_for_function('url=>location.href!==url',arg=old_url)
    page.wait_for_function("document.querySelector('.assessment')?.textContent.includes('62.2%')")
    demo_hash=urlsplit(page.url).fragment
    shot('desktop/02-report.png','รายงานผลเสียงเดโม 45 วินาที')
    nav('หน้าหลัก');shot('desktop/01-home.png','หน้าหลักเว็บและผลล่าสุด')
    nav('ประวัติ');shot('desktop/03-history.png','ประวัติจากเสียงตัวอย่างสองไฟล์')
    page.set_viewport_size({'width':390,'height':844})
    nav('หน้าหลัก');shot('mobile/01-home.png','หน้าหลักบนมือถือ')
    page.goto(url+'/#'+demo_hash,wait_until='networkidle');page.locator('.assessment').wait_for();page.evaluate('scrollTo(0,0)')
    shot('mobile/02-report-summary.png','สรุปผลการวิเคราะห์')
    page.locator('.player-panel').scroll_into_view_if_needed();shot('mobile/03-report-playback.png','Timeline และการย้อนฟัง')
    nav('ประวัติ');shot('mobile/04-history.png','ประวัติบนมือถือ')
    nav('โปรไฟล์');shot('mobile/05-profile.png','โปรไฟล์และข้อมูลส่วนตัว')
    nav('หน้าหลัก');action('start-guide').click();page.get_by_role('heading',name='เตรียมก่อนบันทึก').wait_for();shot('mobile/06-prepare.png','คำแนะนำก่อนบันทึก')
    action('show-consent').click();page.locator('#record-consent').wait_for();shot('mobile/07-consent.png','ยินยอมก่อนใช้ไมโครโฟน')
    page.locator('#record-consent').check();action('begin-record').click();action('stop-record').wait_for();page.wait_for_timeout(2100)
    shot('mobile/08-recording.png','หน้าบันทึกจากไมโครโฟนจำลอง')
    action('stop-record').click();page.wait_for_url('**/#report/*');page.locator('.assessment').wait_for()
    if errors:raise RuntimeError('Uncaught browser errors during capture')
    if posts:raise RuntimeError('Unexpected audio POST during browser-only capture')
    browser.close()

(OUT/'README.md').write_text('''# ภาพสำหรับ Demo Presentation — Snoresens AI

แคปจากเว็บที่ deploy แล้ววันที่ 14 พฤศจิกายน 2026:
https://snoresens-ai-int182.wrybarge4.chatgpt.site

- desktop/: PNG 3840 × 2160 (16:9) เหมาะวางเต็มสไลด์
- mobile/: PNG 780 × 1688 เหมาะวางเป็นภาพแอป 2–3 ภาพต่อสไลด์
- ภาพเป็น screenshot จากเว็บจริง ไม่มีแถบเบราว์เซอร์หรือการเติมตัวเลขทับภาพ
- รายงาน 45 วินาทีได้กรน 28 วินาที / 62.2% / 3 ช่วง จากโมเดลจริง
- ประวัติเป็นเสียงตัวอย่าง 150.435 วินาทีและเดโม 45 วินาทีในวันเดียวกัน ไม่ใช่การเก็บเสียงหลายคืน
- demo 45 วินาทีตัดต่อจาก Tongue base snoring โดย Langenbergstefan (Wikimedia Commons, CC BY-SA 3.0) กับช่วงเงียบ: https://commons.wikimedia.org/wiki/File:Tongue_base_snoring.ogg
- ภาพหน้าบันทึกใช้ไมโครโฟนจำลองของ Chrome เพื่อแสดง UI ไม่ใช่หลักฐานการอัดข้ามคืนหรือเสียงผู้ป่วยจริง
- ไม่ได้ทดสอบหรืออ้างว่าเป็นคะแนนสุขภาพ/ความเสี่ยงโรค

ลำดับสไลด์แนะนำ: หน้าหลัก → เตรียม/ยินยอม → บันทึก → รายงาน/ย้อนฟัง → ประวัติ
'''.replace('https://snoresens-ai-int182.wrybarge4.chatgpt.site',url),encoding='utf-8')
(OUT/'manifest.json').write_text(json.dumps({'source_url':url,'date':'2026-11-14','images':images,'javascript_errors':errors,'audio_post_requests':posts},ensure_ascii=False,indent=2))
with zipfile.ZipFile(ROOT/'exports/SnoresensAI-Demo-Screenshots.zip','w',zipfile.ZIP_DEFLATED) as z:
    for file in OUT.rglob('*'):
        if file.is_file():z.write(file,'SnoresensAI-Demo-Screenshots/'+str(file.relative_to(OUT)))
print('Presentation screenshots and ZIP ready.',flush=True)
