"""Exercise the real web UI, WAV inference, playback and downloaded exports.

Run from project root: .venv/bin/python docs/check_phase3_browser.py
Uses an isolated headless Chrome profile and a temporary local HTTP server.
"""
import csv
import io
import json
from pathlib import Path
import sys
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from web_server import ThreadingHTTPServer,Handler
from playwright.sync_api import sync_playwright

OUT=ROOT/'results/phase3-evidence/browser'
OUT.mkdir(parents=True,exist_ok=True)
checks=[]
errors=[]
def check(name,condition,details=''):
    checks.append(dict(case=name,status='PASS' if condition else 'FAIL',details=details))
    print(checks[-1]['status'],name,flush=True)
    assert condition,f'{name}: {details}'

class ObservedHandler(Handler):
    """Record real API output for export comparison; preserve HTTP behavior."""
    def send_json(self,status,value):
        if self.path=='/api/analyze' and status==200:
            self.server.observed_analysis=value
        super().send_json(status,value)

server=ThreadingHTTPServer(('127.0.0.1',0),ObservedHandler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
        page=context.new_page();page.set_default_timeout(30000)
        # Spectrogram JSON exceeds Chrome's default inspector response cache.
        cdp=context.new_cdp_session(page)
        cdp.send('Network.enable',{'maxTotalBufferSize':100*1024*1024,'maxResourceBufferSize':20*1024*1024})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base+'/lab',wait_until='networkidle')
        check('initial empty state',page.locator('#results').is_hidden())
        check('untrained research model is disabled',page.locator('#apnea-enabled').is_disabled())
        page.screenshot(path=str(OUT/'01-empty-desktop.png'))
        demo=ROOT/'results/phase3-readiness/demo/demo-candidate-45s.wav'
        with page.expect_response(lambda r:r.url.endswith('/api/analyze') and r.request.method=='POST',timeout=600000) as captured:
            page.locator('#files').set_input_files(str(demo))
        response=captured.value
        # Observe the real server result, avoiding Chrome inspector body eviction.
        page.wait_for_function("document.querySelectorAll('#rows tr').length===1")
        api=server.observed_analysis
        (OUT/'uploaded-demo-api.json').write_text(json.dumps(api,ensure_ascii=False,indent=2))
        page.wait_for_function("document.querySelectorAll('#rows tr').length===1")
        check('real WAV upload and result rendering',response.status==200 and page.locator('#results').is_visible(),str(api['summary']))
        check('timeline duration',api['summary']['recording_seconds']==45 and len(api['timeline'])==45)
        check('analysis success message','วิเคราะห์' in page.locator('#status').inner_text() and not page.locator('#status').evaluate("e=>e.classList.contains('error')"))
        player=page.locator('#detail audio')
        page.wait_for_function("document.querySelector('#detail audio').readyState>=1")
        check('audio metadata loaded',abs(player.evaluate('e=>e.duration')-45)<.01)
        slider=page.locator('#detail input[type=range]')
        slider.fill('12.5')
        page.wait_for_function("Math.abs(document.querySelector('#detail audio').currentTime-12.5)<0.2")
        check('timeline slider seeks audio',abs(player.evaluate('e=>e.currentTime')-12.5)<.2)
        filter_select=page.locator('#detail select').last
        filter_select.select_option('snore')
        event_buttons=page.locator('.event-list').last.locator('.event-button')
        check('snore event filter',event_buttons.count()==len(api['snore_events']))
        event_buttons.first.click()
        page.wait_for_timeout(100)
        check('event button seeks audio',abs(player.evaluate('e=>e.currentTime')-api['snore_events'][0]['start_seconds'])<.2)
        player.evaluate('e=>e.play()')
        page.wait_for_timeout(350)
        check('audio playback advances',not player.evaluate('e=>e.paused') and player.evaluate('e=>e.currentTime')>api['snore_events'][0]['start_seconds'])
        player.evaluate('e=>e.pause()')
        filter_select.select_option('')
        page.get_by_text('ดู Spectrogram, Pitch และจังหวะเสียง',exact=True).click()
        check('expanded spectral charts',page.locator('.frequency-details canvas').count()>=1)
        page.locator('#detail').screenshot(path=str(OUT/'02-demo-result-desktop.png'))

        def download(locator):
            with page.expect_download() as captured:
                locator.click()
            dl=captured.value
            path=OUT/dl.suggested_filename;dl.save_as(path)
            return path
        individual_path=download(page.get_by_role('button',name='ดาวน์โหลดผล JSON',exact=True))
        individual=json.loads(individual_path.read_text())
        check('individual JSON preserves analysis',individual['summary']==api['summary'] and individual['timeline']==api['timeline'])
        check('JSON excludes browser-only URLs and IDs','sourceUrl' not in individual and 'id' not in individual and 'audio_scores' in individual)
        timeline_path=download(page.get_by_role('button',name='ดาวน์โหลด timeline CSV',exact=True))
        timeline=list(csv.DictReader(io.StringIO(timeline_path.read_text(encoding='utf-8-sig'))))
        check('timeline CSV content and ordering',len(timeline)==45 and all(float(row['start_seconds'])==original['start_seconds'] and row['prediction']==original['prediction'] and abs(float(row['snore_probability'])-original['snore_probability'])<1e-8 for row,original in zip(timeline,api['timeline'])))
        check('timeline CSV preserves unavailable loudness',timeline[0]['rms_dbfs']=='',str(timeline[0]))
        page.get_by_text('ดูผลอัตราหายใจราย 30 วินาทีและเหตุผลที่ไม่มีค่า',exact=True).click()
        breath_path=download(page.get_by_role('button',name='ดาวน์โหลดอัตราหายใจ CSV',exact=True))
        breath=list(csv.DictReader(io.StringIO(breath_path.read_text(encoding='utf-8-sig'))))
        windows=api['breathing_rate']['windows']
        check('breathing CSV preserves statuses',len(breath)==len(windows) and all(r['status']==w['status'] for r,w in zip(breath,windows)))
        silence=ROOT/'results/phase3-readiness/demo/digital-silence-6s.wav'
        with page.expect_response(lambda r:r.url.endswith('/api/analyze') and r.request.method=='POST',timeout=600000):
            page.locator('#files').set_input_files(str(silence))
        page.wait_for_function("document.querySelectorAll('#rows tr').length===2")
        check('multiple recordings comparison',page.locator('#rows tr').count()==2)
        options=page.locator('#baseline option').evaluate_all('nodes=>nodes.map(n=>({value:n.value,text:n.textContent}))')
        ref=next(o['value'] for o in options if demo.name in o['text'])
        page.locator('#baseline').select_option(ref)
        check('baseline reference selection',page.locator('#baseline').input_value()==ref)
        all_path=download(page.locator('#export-json'))
        all_results=json.loads(all_path.read_text())
        check('all-results JSON matches both uploads',len(all_results)==2 and all_results[0]['summary']==api['summary'] and all_results[1]['summary']['detected_snore_seconds']==0)
        csv_path=download(page.locator('#export-comparison'))
        comparison=list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8-sig'))))
        check('comparison CSV values',len(comparison)==2 and float(comparison[0]['recording_seconds'])==45 and float(comparison[0]['snore_percent_of_recording'])==api['summary']['snore_percent_of_recording'] and float(comparison[1]['snore_percent_of_recording'])==0)
        for row,item in zip(comparison,all_results):
            expected=item['audio_scores']['combined']['score']
            check('comparison combined score '+row['file'],row['combined_snore_score']=='' if expected is None else abs(float(row['combined_snore_score'])-expected)<.00001)
        # Exercise the UI error state using a fake WAV payload, without replacing any API.
        page.locator('#files').set_input_files({'name':'invalid.wav','mimeType':'audio/wav','buffer':b'not a WAV'})
        page.wait_for_function("document.querySelector('#status').classList.contains('error')")
        check('invalid WAV shows error and retains results',page.locator('#rows tr').count()==2 and 'WAV' in page.locator('#status').inner_text())
        page.locator('#files').set_input_files({'name':'wrong.mp3','mimeType':'audio/mpeg','buffer':b'not audio'})
        page.wait_for_function("document.querySelector('#status').textContent.includes('ต้องเป็น WAV')")
        check('unsupported extension is skipped',page.locator('#rows tr').count()==2)
        page.set_viewport_size({'width':390,'height':844})
        page.locator('#results').scroll_into_view_if_needed()
        page.screenshot(path=str(OUT/'03-results-mobile.png'))
        widths=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth})')
        check('mobile page has no document overflow',widths['document']<=widths['viewport'],str(widths))
        page.get_by_role('button',name='ลบผลนี้',exact=True).click()
        check('remove one result',page.locator('#rows tr').count()==1)
        page.get_by_role('button',name='ลบผลนี้',exact=True).click()
        check('remove all returns empty state',page.locator('#results').is_hidden())
        check('no uncaught JavaScript errors',len(errors)==0,str(errors))
        browser.close()
finally:
    server.shutdown();server.server_close();thread.join()
    (OUT/'checks.json').write_text(json.dumps(dict(date='2026-11-14',checks=checks,page_errors=errors,scope='Headless Chrome, real local API and downloaded files; no physical microphone or human listening verification'),ensure_ascii=False,indent=2))
    print(json.dumps(checks,ensure_ascii=False,indent=2))
