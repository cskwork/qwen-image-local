import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/qwen-image-local/scripts'))
import web_server


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        with patch.object(web_server.qwen_local, 'doctor'):
            self.app = web_server.Application(Path(self.temp.name), Path(self.temp.name) / 'images')
        self.server = web_server.make_server(self.app, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, method, path, payload=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        body = json.dumps(payload) if payload is not None else None
        request_headers = {'Content-Type':'application/json','Origin':self.origin,'X-Qwen-Token':self.app.token}
        request_headers.update(headers or {})
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_page_and_ready_status(self):
        self.assertIn(b'What will you create?', self.request('GET', '/')[1])
        status = json.loads(self.request('GET', '/api/status')[1])
        self.assertTrue(status['ready'])
        self.assertIsNone(status['job'])

    def test_reject_cross_origin_and_missing_token(self):
        for headers in [{'Origin':'https://example.com'}, {'X-Qwen-Token':''}, {'Host':'evil.example'}]:
            self.assertEqual(self.request('POST','/api/generate',{'prompt':'hello'},headers)[0],403)

    def test_file_paths_not_exposed(self):
        self.assertEqual(self.request('GET','/../scripts/assets.json')[0],404)
        self.assertEqual(self.request('GET','/images/../../secret.png')[0],404)

    def test_bad_request_is_explicit(self):
        for payload in [[], {'prompt':' '}, {'prompt':'hi','width':True}, {'prompt':'hi','steps':100}]:
            self.assertEqual(self.request('POST','/api/generate',payload)[0],400)

    def test_missing_model_is_503(self):
        self.app.problem = 'Missing model'
        self.assertEqual(self.request('POST','/api/generate',{'prompt':'hello'})[0],503)

    def test_busy_request_does_not_launch_another_job(self):
        self.app.job = dict(state='running', id='existing', started=0)
        self.assertEqual(self.request('POST','/api/generate',{'prompt':'hello'})[0],409)
        self.assertEqual(self.app.job['id'],'existing')

    def test_worker_success_serves_image_and_failure_stays_failure(self):
        settings = web_server.validate({'prompt':'hello'})
        self.app.job = dict(state='running', id='test', started=0)
        def fake_generate(root, args):
            path = Path(args.output)
            path.parent.mkdir(parents=True)
            path.write_bytes(b'fake-image-for-route-test')
            Path(str(path)+'.json').write_text('{"elapsed_seconds":1.5}')
        with patch.object(web_server.qwen_local,'generate',side_effect=fake_generate):
            self.app.run('test', settings)
        self.assertEqual(self.app.status()['job']['state'],'done')
        self.assertEqual(self.request('GET','/images/test.png'),(200,b'fake-image-for-route-test'))
        self.app.job = dict(state='running', id='failure', started=0)
        with patch.object(web_server.qwen_local,'generate',side_effect=RuntimeError('GPU failure')):
            self.app.run('failure', settings)
        self.assertEqual(self.app.status()['job']['state'],'error')
        self.assertEqual(self.request('GET','/images/failure.png')[0],404)


if __name__ == '__main__':
    unittest.main()
