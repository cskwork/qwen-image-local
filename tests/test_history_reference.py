import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/qwen-image-local/scripts'
sys.path.insert(0, str(SCRIPTS))
import qwen_local
import web_server
from generation_lock import generation_lock


class HistoryReferenceTests(unittest.TestCase):
    def app(self, root):
        with patch.object(qwen_local, 'doctor'):
            return web_server.Application(root, root / 'images')

    def test_history_survives_restart_without_rewriting_images(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'images'
            output.mkdir()
            key = 'a' * 32
            image = output / (key + '.png')
            image.write_bytes(b'preserve-me')
            metadata = dict(prompt='original prompt',width=832,height=1216,steps=20,seed=42,elapsed_seconds=2)
            Path(str(image) + '.json').write_text(json.dumps(metadata))
            app = self.app(root)
            self.assertEqual(len(app.history), 1)
            self.assertEqual(app.history[0]['prompt'], 'original prompt')
            self.assertEqual(app.job['state'], 'done')
            self.assertEqual(image.read_bytes(), b'preserve-me')

    def test_corrupt_history_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'images'
            output.mkdir()
            path = output / ('b'*32 + '.png.json')
            path.write_text('broken')
            app = self.app(root)
            self.assertEqual(app.history_warnings, 1)
            self.assertEqual(path.read_text(), 'broken')

    def test_reference_validation_and_local_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(qwen_local, 'reference_ready', return_value=True):
            root = Path(folder)
            app = self.app(root)
            data = b'\x89PNG\r\n\x1a\n' + struct.pack('>I',13) + b'IHDR' + struct.pack('>II',64,64)
            result = app.attach(data)
            self.assertEqual(app.resolve_reference(result['id']).read_bytes(), data)
            reloaded = self.app(root)
            self.assertEqual(reloaded.resolve_reference(result['id']).read_bytes(), data)
            with self.assertRaises(ValueError):
                app.attach(b'not an image')
            oversized = data[:16] + struct.pack('>II',5000,64)
            with self.assertRaises(ValueError):
                app.attach(oversized)
            with self.assertRaises(ValueError):
                app.resolve_reference('upload-' + 'f'*32)

    def test_reference_requires_vision_model(self):
        with tempfile.TemporaryDirectory() as folder:
            app = self.app(Path(folder))
            with self.assertRaisesRegex(RuntimeError, 'not installed'):
                app.attach(b'anything')

    def test_selected_history_image_can_be_reference(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(qwen_local, 'reference_ready', return_value=True):
            root = Path(folder)
            app = self.app(root)
            path = root / 'saved.png'
            path.write_bytes(b'local')
            app.images['a'*32] = path
            self.assertEqual(app.resolve_reference('image-'+'a'*32), path)

    def test_reference_is_passed_to_actual_runtime(self):
        args = argparse.Namespace(prompt='Change background',width=512,height=512,steps=10,max_vram=6.5,seed=42,reference=Path('reference.png'))
        command = qwen_local.command(Path('root'),args,Path('out.png'))
        self.assertEqual(command[command.index('-r')+1], 'reference.png')
        self.assertEqual(command[command.index('--llm_vision')+1], str(Path('root')/qwen_local.VISION_NAME))

    def test_model_lock_excludes_another_process_and_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script = 'import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); from generation_lock import generation_lock\ntry:\n with generation_lock(Path(sys.argv[2])): sys.exit(2)\nexcept BlockingIOError: sys.exit(0)'
            with generation_lock(root):
                result = subprocess.run([sys.executable,'-c',script,str(SCRIPTS),str(root)],timeout=10)
                self.assertEqual(result.returncode,0)
            with generation_lock(root):
                pass


if __name__ == '__main__':
    unittest.main()
