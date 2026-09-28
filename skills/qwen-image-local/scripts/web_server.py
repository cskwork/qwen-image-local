"""Loopback-only web interface around the existing generation helper."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import struct
import threading
import time
from urllib.parse import urlsplit
import uuid
import webbrowser

import qwen_local

WEB = Path(__file__).resolve().parents[1] / 'web'
SIZES = {(512, 512), (768, 768), (832, 1216), (1216, 832)}
IDENTIFIER = re.compile(r'^[a-f0-9]{32}$')
MAX_UPLOAD = 8 * 1024 * 1024


def image_format(data):
    if len(data) >= 24 and data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR':
        width, height = struct.unpack('>II', data[16:24])
        extension = '.png'
    elif data[:3] == b'\xff\xd8\xff':
        offset, width, height = 2, 0, 0
        while offset + 4 <= len(data):
            if data[offset] != 255:
                break
            marker = data[offset + 1]
            if marker == 255:
                offset += 1
                continue
            if marker in (0xDA, 0xD9):
                break
            length = int.from_bytes(data[offset + 2:offset + 4], 'big')
            if length < 2 or offset + 2 + length > len(data):
                break
            if marker in (0xC0, 0xC1, 0xC2) and length >= 8:
                height, width = struct.unpack('>HH', data[offset + 5:offset + 9])
                break
            offset += 2 + length
        extension = '.jpg'
    else:
        raise ValueError('Attach a PNG or JPEG image.')
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise ValueError('Reference dimensions must be between 1 and 4096 pixels per side.')
    return extension


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    prompt = data.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
        raise ValueError('Enter a prompt between 1 and 4000 characters.')
    values = {key: data.get(key, default) for key, default in
              [('width', 832), ('height', 1216), ('steps', 20), ('seed', 42)]}
    if any(type(value) is not int for value in values.values()):
        raise ValueError('Size, steps and seed must be integers.')
    if (values['width'], values['height']) not in SIZES:
        raise ValueError('Choose a supported image size.')
    if not 10 <= values['steps'] <= 40 or not -1 <= values['seed'] <= 2147483647:
        raise ValueError('Steps must be 10–40; seed must be -1–2147483647.')
    reference_id = data.get('reference_id')
    if reference_id is not None and (not isinstance(reference_id, str)
            or not re.fullmatch(r'(upload|image)-[a-f0-9]{32}', reference_id)):
        raise ValueError('Invalid reference image identifier.')
    return dict(prompt=prompt.strip(), reference_id=reference_id, **values)


class Application:
    def __init__(self, root, output):
        self.root, self.output = root, output.resolve()
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.job = None
        self.images = {}
        self.history = []
        self.history_warnings = 0
        self.references = {}
        self.load_history()
        try:
            qwen_local.doctor(root)
            self.problem = None
        except (OSError, ValueError, RuntimeError, qwen_local.subprocess.SubprocessError) as error:
            self.problem = str(error)

    def load_history(self):
        for metadata in sorted(self.output.glob('*.png.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:100]:
            key = metadata.name.removesuffix('.png.json')
            image = self.output / (key + '.png')
            if not IDENTIFIER.fullmatch(key):
                continue
            try:
                if metadata.stat().st_size > 32000 or not image.is_file() or not image.resolve().is_relative_to(self.output):
                    raise ValueError('Invalid history entry')
                saved = json.loads(metadata.read_text(encoding='utf-8-sig'))
                settings = validate(saved)
                entry = dict(id=key, image=f'/images/{key}.png', **settings,
                             elapsed_seconds=saved['elapsed_seconds'])
                self.images[key] = image
                self.history.append(entry)
            except (OSError, ValueError, KeyError, TypeError):
                self.history_warnings += 1
        if self.history:
            self.job = dict(self.history[0], state='done')
        for path in (self.output / 'references').glob('*'):
            if IDENTIFIER.fullmatch(path.stem) and path.suffix in ('.png', '.jpg') and path.resolve().is_relative_to(self.output):
                self.references['upload-' + path.stem] = path

    def resolve_reference(self, reference_id):
        if not reference_id:
            return None
        if not qwen_local.reference_ready(self.root):
            raise RuntimeError('Reference support is not installed. Run install-reference, then refresh.')
        if reference_id.startswith('image-'):
            path = self.images.get(reference_id.removeprefix('image-'))
        else:
            path = self.references.get(reference_id)
        if not path or not path.is_file():
            raise ValueError('Reference image not found. Attach it again or choose an available history image.')
        return path

    def attach(self, data):
        if not qwen_local.reference_ready(self.root):
            raise RuntimeError('Reference support is not installed. Run install-reference first.')
        extension = image_format(data)
        key = 'upload-' + uuid.uuid4().hex
        path = self.output / 'references' / (key.removeprefix('upload-') + extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        with self.lock:
            self.references[key] = path
        return dict(id=key, image=f'/references/{key}')

    def status(self):
        with self.lock:
            job = dict(self.job) if self.job else None
        if job and job['state'] == 'running':
            job['elapsed_seconds'] = round(time.monotonic() - job['started'], 1)
        if job:
            job.pop('started', None)
        return dict(ready=self.problem is None, problem=self.problem, token=self.token,
                    model='Qwen-Image-2.1 Q4', root=str(self.root), job=job,
                    reference_ready=qwen_local.reference_ready(self.root))

    def start(self, data):
        settings = validate(data)
        with self.lock:
            if self.problem:
                raise RuntimeError(self.problem)
            if self.job and self.job['state'] == 'running':
                raise BlockingIOError('An image is already generating. Wait for it to finish.')
            reference = self.resolve_reference(settings['reference_id'])
            key = uuid.uuid4().hex
            self.job = dict(id=key, state='running', started=time.monotonic(), **settings)
        threading.Thread(target=self.run, args=(key, settings, reference), daemon=False).start()
        return key

    def run(self, key, settings, reference=None):
        output = self.output / (key + '.png')
        try:
            args = argparse.Namespace(**settings, output=str(output), max_vram=6.5, reference=reference)
            qwen_local.generate(self.root, args)
            metadata = json.loads(Path(str(output) + '.json').read_text(encoding='utf-8'))
            metadata['reference_id'] = settings.get('reference_id')
            pending = Path(str(output) + '.json.tmp')
            pending.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
            pending.replace(Path(str(output) + '.json'))
            with self.lock:
                self.images[key] = output
                self.job.update(state='done', image=f'/images/{key}.png',
                                elapsed_seconds=metadata['elapsed_seconds'])
                self.history.insert(0, dict(id=key, image=f'/images/{key}.png', **settings,
                                            elapsed_seconds=metadata['elapsed_seconds']))
                self.history = self.history[:100]
        except Exception as error:
            with self.lock:
                self.job.update(state='error', error=str(error))


def make_server(app, port):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, payload, content_type='application/json; charset=utf-8'):
            body = json.dumps(payload, ensure_ascii=False).encode() if isinstance(payload, dict) else payload
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, dict(error='Open the 127.0.0.1 address printed by the launcher.'))
            path = urlsplit(self.path).path
            if path == '/api/status':
                return self.reply(200, app.status())
            if path == '/api/history':
                with app.lock:
                    history = list(app.history)
                return self.reply(200, dict(images=history, warnings=app.history_warnings))
            files = {'/': ('index.html', 'text/html; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if path in files:
                name, mime = files[path]
                return self.reply(200, (WEB / name).read_bytes(), mime)
            if path.startswith('/images/') and path.endswith('.png'):
                key = path.removeprefix('/images/').removesuffix('.png')
                with app.lock:
                    image = app.images.get(key)
                if image and image.is_file():
                    return self.reply(200, image.read_bytes(), 'image/png')
            if path.startswith('/references/'):
                with app.lock:
                    reference = app.references.get(path.removeprefix('/references/'))
                if reference and reference.is_file():
                    return self.reply(200, reference.read_bytes(), 'image/png' if reference.suffix == '.png' else 'image/jpeg')
            return self.reply(404, dict(error='Not found.'))

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if (not self.valid_host() or self.headers.get('Origin') != origin
                    or not secrets.compare_digest(self.headers.get('X-Qwen-Token', ''), app.token)):
                return self.reply(403, dict(error='Request rejected. Refresh the local page and try again.'))
            path = urlsplit(self.path).path
            if path not in ('/api/generate', '/api/reference'):
                return self.reply(404, dict(error='Not found.'))
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if path == '/api/reference':
                    if not 0 < length <= MAX_UPLOAD:
                        raise ValueError('Reference image must be at most 8MB.')
                    if self.headers.get('Content-Type') != 'application/octet-stream':
                        raise ValueError('Send image bytes as application/octet-stream.')
                    return self.reply(201, app.attach(self.rfile.read(length)))
                if not 0 < length <= 20000:
                    raise ValueError('Request must be at most 20KB.')
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('Use JSON request content.')
                data = json.loads(self.rfile.read(length))
                key = app.start(data)
                self.reply(202, dict(id=key))
            except BlockingIOError as error:
                self.reply(409, dict(error=str(error)))
            except (ValueError, UnicodeError) as error:
                self.reply(400, dict(error=str(error)))
            except (RuntimeError, OSError) as error:
                self.reply(503, dict(error=str(error)))

        def log_message(self, *_args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def serve(root, port=8766, open_browser=False, output=None):
    if not 0 <= port <= 65535:
        raise ValueError('Port must be between 0 and 65535.')
    app = Application(root, output or root / 'outputs/web')
    server = make_server(app, port)
    address = f'http://127.0.0.1:{server.server_port}/'
    print(f'Local studio: {address}\nImages: {app.output}\nKeep this process running. Ctrl+C stops the server.', flush=True)
    if open_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Stopping server. Any active generation will finish before exit.', flush=True)
    finally:
        server.server_close()
