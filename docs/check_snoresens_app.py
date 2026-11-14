"""Real browser checks for the Figma-derived app; local temporary server only."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import threading
from urllib.request import urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from web_server import ThreadingHTTPServer,Handler
from playwright.sync_api import sync_playwright

OUT=ROOT/'results/snoresens-web-checks';OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]
def check(name,condition,detail=''):
    checks.append(dict(case=name,status='PASS' if condition else 'FAIL',detail=detail))
    print(checks[-1]['status'],name,flush=True)
    assert condition,f'{name}: {detail}'
class Observed(Handler):
    def send_json(self,status,value):
        if self.path=='/api/analyze' and status==200:
            self.server.last_analysis=value
            (OUT/'last-api-summary.json').write_text(json.dumps(value.get('summary',{}),indent=2))
        super().send_json(status,value)
server=ThreadingHTTPServer(('127.0.0.1',0),Observed)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True,args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
        context=browser.new_context(viewport={'width':390,'height':844},accept_downloads=True,permissions=['microphone'])
        page=context.new_page();page.set_default_timeout(30000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        def action(name):return page.locator(f'[data-action="{name}"]').filter(visible=True)
        def nav(name):
            page.locator('#bottom-nav').get_by_role('link',name=name,exact=True).click()
            page.wait_for_function("name=>document.querySelector('#bottom-nav [aria-current=page]')?.textContent.includes(name)",arg=name)
        def shot(name):page.screenshot(path=str(OUT/name),full_page=True)
        def overflow():return page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        def dl(action_name):
            with page.expect_download() as captured:action(action_name).click()
            d=captured.value;path=OUT/d.suggested_filename;d.save_as(path);return path
        page.goto(base,wait_until='networkidle')
        page.get_by_role('heading',name='คืนนี้ ฟังการนอนของคุณ').wait_for()
        check('mobile home loads with four navigation links',page.locator('#bottom-nav a').count()==4)
        check('empty state contains no invented history',page.locator('.empty-card').count()==1)
        check('mobile home has no page overflow',overflow())
        shot('01-home-mobile.png')
        page.goto(base+'/#record',wait_until='networkidle');action('begin-record').click()
        page.locator('#record-consent').wait_for()
        check('direct recording route cannot bypass consent',page.locator('[data-action="begin-record"]').is_disabled())
        page.goto(base,wait_until='networkidle');page.get_by_role('heading',name='คืนนี้ ฟังการนอนของคุณ').wait_for()
        nav('โปรไฟล์');shot('02-profile-mobile.png')
        action('privacy').click();check('privacy dialog is accessible',page.get_by_role('dialog').is_visible())
        page.keyboard.press('Escape');check('Escape closes dialog',not page.get_by_role('dialog').is_visible())
        action('edit-name').click();page.locator('#display-name').fill('ผู้ทดสอบ Snoresens')
        page.get_by_role('button',name='บันทึกชื่อ',exact=True).click()
        page.reload(wait_until='networkidle')
        page.get_by_role('heading',name='ผู้ทดสอบ Snoresens').wait_for()
        check('profile name survives reload',page.get_by_role('heading',name='ผู้ทดสอบ Snoresens').is_visible())
        nav('หน้าหลัก')
        demo=ROOT/'results/phase3-readiness/demo/demo-candidate-45s.wav'
        with page.expect_response(lambda r:r.url.endswith('/api/analyze') and r.request.method=='POST',timeout=120000) as captured:
            page.locator('#audio-file').set_input_files(str(demo))
        page.wait_for_url('**/#report/*',timeout=120000)
        page.locator('.assessment').wait_for()
        api=server.last_analysis
        check('real WAV analysis renders report',captured.value.status==200 and api['summary']['recording_seconds']==45)
        check('report uses actual snore duration',api['summary']['detected_snore_seconds']==28 and 'พบกรน 62.2%' in page.locator('.assessment').inner_text())
        check('mobile report has no overflow',overflow())
        shot('03-report-mobile.png')
        page.set_viewport_size({'width':1440,'height':1000})
        check('desktop report has no overflow',overflow());shot('09-report-desktop.png')
        page.set_viewport_size({'width':390,'height':844})
        audio=page.locator('#report-audio');page.wait_for_function("document.querySelector('#report-audio').readyState>=1")
        page.locator('#seek').fill('12.5')
        check('report slider seeks audio',abs(audio.evaluate('e=>e.currentTime')-12.5)<.2)
        action('seek').first.click();page.wait_for_timeout(100)
        check('event selection seeks to detected start',abs(audio.evaluate('e=>e.currentTime')-api['snore_events'][0]['start_seconds'])<.2)
        audio.evaluate('e=>e.play()')
        page.wait_for_function("start=>{const a=document.querySelector('#report-audio');return !a.paused&&a.currentTime>start+.05}",arg=api['snore_events'][0]['start_seconds'],timeout=5000)
        check('real audio playback advances',not audio.evaluate('e=>e.paused') and audio.evaluate('e=>e.currentTime')>api['snore_events'][0]['start_seconds'])
        audio.evaluate('e=>e.pause()')
        exported=json.loads(dl('export-json').read_text())
        check('report JSON preserves API summary and timeline',exported['summary']==api['summary'] and exported['timeline']==api['timeline'])
        check('report JSON contains score definitions','audio_scores' in exported and 'combined' in exported['audio_scores'])
        rows=list(csv.DictReader(io.StringIO(dl('export-timeline').read_text(encoding='utf-8-sig'))))
        check('timeline CSV has correct rows and predictions',len(rows)==45 and all(row['prediction']==original['prediction'] and float(row['start_seconds'])==original['start_seconds'] for row,original in zip(rows,api['timeline'])))
        saved_audio=dl('export-audio')
        check('downloaded WAV is unchanged',hashlib.sha256(saved_audio.read_bytes()).digest()==hashlib.sha256(demo.read_bytes()).digest())
        page.reload(wait_until='networkidle');page.locator('.assessment').wait_for()
        check('analysis and audio persist across reload',page.locator('.assessment').is_visible())
        page.wait_for_function("document.querySelector('#report-audio').readyState>=1")
        check('stored audio duration preserved',abs(page.locator('#report-audio').evaluate('e=>e.duration')-45)<.01)
        silence=ROOT/'results/phase3-readiness/demo/digital-silence-6s.wav'
        old_hash=page.url
        page.locator('#audio-file').set_input_files(str(silence))
        page.wait_for_function("location.href!=="+json.dumps(old_hash),timeout=120000)
        page.get_by_role('heading',name='ไม่พบเสียงกรนในไฟล์นี้').wait_for()
        check('silence shows no detection rather than invented risk','ไม่พบเสียงกรน' in page.locator('.assessment').inner_text())
        nav('ประวัติ');page.locator('.history-card').first.wait_for()
        check('history contains both real recordings',page.locator('.history-card').count()==2)
        shot('04-history-mobile.png')
        history=json.loads(dl('export-history').read_text())
        check('history JSON contains both analyses',len(history)==2 and sorted(r['summary']['recording_seconds'] for r in history)==[6,45])
        comparison=list(csv.DictReader(io.StringIO(dl('export-comparison').read_text(encoding='utf-8-sig'))))
        check('history CSV matches results',len(comparison)==2 and sorted(float(r['detected_snore_seconds']) for r in comparison)==[0,28])
        page.locator('.history-card').last.click();page.locator('.assessment').wait_for()
        action('delete-record').click();page.keyboard.press('Escape')
        check('cancel deletion preserves report',page.locator('.assessment').is_visible())
        action('delete-record').click();action('confirm-delete').click()
        page.wait_for_url('**/#history');page.wait_for_function("document.querySelectorAll('.history-card').length===1")
        check('confirmed deletion removes a single record',page.locator('.history-card').count()==1)
        nav('หน้าหลัก')
        page.locator('#audio-file').set_input_files({'name':'invalid.wav','mimeType':'audio/wav','buffer':b'not WAV'})
        page.locator('#toast.error').wait_for();check('invalid upload shows recoverable error',page.locator('#toast').is_visible())
        nav('ประวัติ');check('failed upload does not create history',page.locator('.history-card').count()==1)
        nav('หน้าหลัก');action('start-guide').click()
        page.get_by_role('heading',name='เตรียมก่อนบันทึก').wait_for();shot('07-prepare-mobile.png')
        action('show-consent').click();page.locator('#record-consent').wait_for()
        check('recording requires explicit consent',page.locator('[data-action="begin-record"]').is_disabled())
        shot('08-consent-mobile.png');page.locator('#record-consent').check();action('begin-record').click()
        page.locator('[data-action="stop-record"]').wait_for(timeout=30000)
        check('simulated microphone starts recording',page.locator('[data-action="stop-record"]').is_visible())
        page.wait_for_timeout(2300);shot('05-recording-mobile.png')
        check('recording timer advances',page.locator('#record-time').inner_text()!='00:00:00')
        action('pause-record').click();page.wait_for_timeout(300)
        paused_time=page.locator('#record-time').inner_text();page.wait_for_timeout(1100)
        check('pause stops the captured-audio timer',page.locator('#record-time').inner_text()==paused_time)
        action('resume-record').click();page.wait_for_timeout(1300)
        check('resume continues captured audio',page.locator('#record-time').inner_text()!=paused_time)
        action('stop-record').click();page.wait_for_url('**/#report/*',timeout=120000);page.locator('.assessment').wait_for()
        check('stop converts audio and analyzes real WAV',server.last_analysis['summary']['recording_seconds']>1 and server.last_analysis['summary']['recording_seconds']<30,str(server.last_analysis['summary']))
        nav('โปรไฟล์');action('clear-data').click();action('confirm-clear').click()
        page.get_by_text('0 รายการในเบราว์เซอร์นี้',exact=False).wait_for()
        nav('ประวัติ');check('clear data leaves empty history',page.locator('.empty-card').count()==1)
        page.reload(wait_until='networkidle');page.locator('.empty-card').wait_for()
        check('cleared history remains empty after reload',page.locator('.history-card').count()==0)
        nav('หน้าหลัก');action('sample').click()
        page.wait_for_url('**/#report/*',timeout=120000);page.locator('.assessment').wait_for()
        check('built-in sample uses actual audio inference',server.last_analysis['summary']['recording_seconds']==150.435 and server.last_analysis['summary']['detected_snore_seconds']==131)
        check('sample report is labeled as sample',page.locator('.report-meta .pill').inner_text()=='เสียงตัวอย่าง')
        page.set_viewport_size({'width':1440,'height':1000})
        page.goto(base,wait_until='networkidle');page.get_by_role('heading',name='คืนนี้ ฟังการนอนของคุณ').wait_for()
        check('desktop uses visible sidebar navigation',page.locator('.sidebar').is_visible() and not page.locator('#bottom-nav').is_visible())
        check('desktop has no overflow',overflow());shot('06-home-desktop.png')
        capture=page.evaluate('''async()=>{
          const {startRecording}=await import('/app-assets/audio.mjs');
          let finish,ticks=0;const parts=[],errors=[],done=new Promise(resolve=>finish=resolve);
          const session=await startRecording({partMillis:500,onTick:s=>ticks=s,onDone:finish,onError:e=>errors.push(e.message),onChunk:async(blob,part)=>{
            const view=new DataView(await blob.arrayBuffer());
            parts.push({part,rate:view.getUint32(24,true),seconds:view.getUint32(40,true)/32000});
          }});
          await new Promise(resolve=>setTimeout(resolve,1350));session.stop();await done;
          return {parts,errors,ticks};
        }''')
        (OUT/'pcm-capture-check.json').write_text(json.dumps(capture,indent=2))
        check('PCM recorder splits and flushes independent WAV parts',len(capture['parts'])>=2 and [r['part'] for r in capture['parts']]==list(range(1,len(capture['parts'])+1)) and all(r['rate']==16000 for r in capture['parts']) and not capture['errors'],str(capture))
        check('PCM timer matches saved audio sample duration',abs(sum(r['seconds'] for r in capture['parts'])-capture['ticks'])<.001,str(capture))
        with urlopen(base+'/lab') as response:check('original lab remains accessible',response.status==200 and 'id="files"' in response.read().decode())
        with urlopen(base+'/app-assets/audio.mjs') as response:check('ES modules served as JavaScript',response.headers.get_content_type()=='text/javascript')
        try:
            urlopen(base+'/app-assets/%2e%2e/%2e%2e/README.md');check('asset traversal blocked',False)
        except HTTPError as error:check('asset traversal blocked',error.code==404)
        check('no uncaught browser JavaScript errors',len(errors)==0,str(errors))
        browser.close()
except Exception:
    if 'page' in locals():
        try:page.screenshot(path=str(OUT/'failure.png'),full_page=True)
        except Exception:pass
    raise
finally:
    server.shutdown();server.server_close();thread.join()
    (OUT/'checks.json').write_text(json.dumps({'date':'2026-11-14','checks':checks,'javascript_errors':errors,'recording_scope':'Simulated Chrome microphone, not a physical phone/bedroom test'},ensure_ascii=False,indent=2))
