"""Local-only web interface for the existing WAV inference pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import webbrowser
import traceback
import os
import mimetypes
from urllib.parse import unquote, urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from compare import session_summary
from apnea_research import model_status

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
APP = WEB / "snoresens"
MAX_BYTES = 200 * 1024 * 1024


def analyze_bytes(raw: bytes, quiet_threshold: float = -45.0, min_gap: float = 10.0, enable_apnea: bool = False) -> dict:
    if raw[:4] not in (b"RIFF", b"RF64") or raw[8:12] != b"WAVE":
        raise ValueError("รองรับไฟล์ WAV เท่านั้น")
    with tempfile.TemporaryDirectory(prefix="sanor-") as temp_dir:
        wav = Path(temp_dir) / "input.wav"
        wav.write_bytes(raw)
        result = subprocess.run(
            [sys.executable, str(ROOT / "predict.py"), str(wav), "--include-timeline", "--include-spectrogram",
             "--quiet-threshold-dbfs", str(quiet_threshold), "--min-quiet-gap-seconds", str(min_gap)] + (['--apnea-research'] if enable_apnea else []),
            capture_output=True, text=True, timeout=600, check=False,
        )
        if result.returncode:
            raise ValueError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else result.stdout.strip())
        output = json.loads(result.stdout)
        for key in ("file", "timeline_csv", "cough_review_csv"):
            output.pop(key, None)
        return output


class Handler(BaseHTTPRequestHandler):
    def send_data(self, status: int, body: bytes, content_type: str, download_name: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, value: dict) -> None:
        self.send_data(status, json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in ('/', '/app', '/app/'):
            self.send_data(200, (APP / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            return
        if path.startswith('/app-assets/'):
            asset = (APP / unquote(path[len('/app-assets/'):])).resolve()
            if not asset.is_relative_to(APP.resolve()) or not asset.is_file():
                self.send_error(404)
                return
            content_type = 'text/javascript' if asset.suffix == '.mjs' else (mimetypes.guess_type(str(asset))[0] or 'application/octet-stream')
            self.send_data(200, asset.read_bytes(), content_type)
            return
        if path in ('/lab', '/lab/'):
            self.send_data(200, (WEB / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            return
        if self.path == '/samples/test_snore_16k.wav':
            sample = ROOT / 'test_snore_16k.wav'
            if not sample.is_file():
                self.send_error(404)
                return
            self.send_data(200, sample.read_bytes(), 'audio/wav', 'test_snore_16k.wav')
            return
        if self.path == '/api/apnea-status':
            self.send_json(200, model_status(ROOT / 'artifacts' / 'apnea'))
            return
        files = {"/": "index.html", "/app.js": "app.js", "/measurements.js": "measurements.js", "/audio-charts.js": "audio-charts.js", "/style.css": "style.css"}
        name = files.get(self.path)
        if not name:
            self.send_error(404)
            return
        content_type = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[Path(name).suffix]
        self.send_data(200, (WEB / name).read_bytes(), content_type + "; charset=utf-8")

    def do_POST(self) -> None:
        if self.path not in ("/api/analyze", "/api/session-summary"):
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_BYTES:
                self.send_json(413, {"error": "เลือกไฟล์ WAV ที่มีขนาดไม่เกิน 200 MB"})
                return
            if self.path == '/api/session-summary':
                parts = json.loads(self.rfile.read(size))
                if not isinstance(parts, list):
                    raise ValueError('Expected a list of recording parts')
                self.send_json(200, session_summary(parts))
                return
            enabled = self.headers.get('X-Apnea-Research', 'false')
            if enabled not in ('true', 'false'):
                raise ValueError('X-Apnea-Research must be true or false')
            options = {'enable_apnea': True} if enabled == 'true' else {}
            self.send_json(200, analyze_bytes(self.rfile.read(size),
                float(self.headers.get('X-Quiet-Threshold-Dbfs', '-45')),
                float(self.headers.get('X-Min-Quiet-Gap-Seconds', '10')), **options))
        except (ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
            self.send_json(400, {"error": f"วิเคราะห์ไฟล์ไม่ได้: {error}"})


if __name__ == "__main__":
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
        url = "http://127.0.0.1:8765"
        print(f"Sanor web: {url}", flush=True)
        if os.environ.get("SANOR_NO_BROWSER") != "1":
            webbrowser.open(url)
        server.serve_forever()
    except Exception:
        log = ROOT / "results" / "web_server_error.log"
        log.parent.mkdir(exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        print(f"รายละเอียดข้อผิดพลาด: {log}", file=sys.stderr)
        raise
