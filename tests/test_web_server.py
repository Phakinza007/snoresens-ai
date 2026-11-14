import io
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
from web_server import Handler, analyze_bytes


class WebServerTests(unittest.TestCase):
    def request(self, path, body, headers=None):
        handler = Handler.__new__(Handler)
        handler.path = path
        handler.headers = {'Content-Length':str(len(body)), **(headers or {})}
        handler.rfile = io.BytesIO(body)
        responses = []
        handler.send_json = lambda status, data: responses.append((status, data))
        handler.send_error = lambda status: responses.append((status, {}))
        handler.do_POST()
        return responses[0]

    def test_analysis_route_typed_result(self):
        fixture = json.loads(Path('tests/fixtures/sample-analysis.json').read_text())
        with patch('web_server.analyze_bytes', return_value=fixture) as analyze:
            status, data = self.request('/api/analyze', b'audio', {'X-Quiet-Threshold-Dbfs':'-50'})
        self.assertEqual(status, 200)
        self.assertIsInstance(data['timeline'][0]['start_seconds'], float)
        analyze.assert_called_once_with(b'audio', -50, 10)

    def test_invalid_headers_empty_body_and_bad_session(self):
        self.assertEqual(self.request('/api/analyze', b'x', {'X-Min-Quiet-Gap-Seconds':'wrong'})[0], 400)
        self.assertEqual(self.request('/api/analyze', b'')[0], 413)
        self.assertEqual(self.request('/api/session-summary', b'{}')[0], 400)
        self.assertEqual(self.request('/api/session-summary', b'[{"oops":1}]')[0], 400)

    def test_apnea_research_requires_explicit_header(self):
        with patch('web_server.analyze_bytes', return_value={'apnea_research':{'enabled':True}}) as analyze:
            status,data=self.request('/api/analyze',b'audio',{'X-Apnea-Research':'true'})
        self.assertEqual(status,200)
        analyze.assert_called_once_with(b'audio',-45,10,enable_apnea=True)
        self.assertTrue(data['apnea_research']['enabled'])
        self.assertEqual(self.request('/api/analyze',b'audio',{'X-Apnea-Research':'yes'})[0],400)

    def test_apnea_status_without_trained_model(self):
        handler=Handler.__new__(Handler);handler.path='/api/apnea-status'
        responses=[];handler.send_json=lambda status,data:responses.append((status,data))
        with tempfile.TemporaryDirectory() as folder, patch('web_server.ROOT',Path(folder)):
            handler.do_GET()
        self.assertEqual(responses[0][0],200)
        self.assertEqual(responses[0][1]['status'],'not_trained')
        self.assertIsNone(responses[0][1]['risk_percent'])

    def test_wav_signature_validation(self):
        with self.assertRaises(ValueError): analyze_bytes(b'not a WAV')


if __name__ == '__main__': unittest.main()
