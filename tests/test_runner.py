import argparse
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/qwen-image-local/scripts'
sys.path.insert(0, str(SCRIPTS))
import qwen_local as runner
import download


class RunnerTests(unittest.TestCase):
    def args(self, output):
        return argparse.Namespace(prompt='A portrait; $(no-shell) "quoted"', output=str(output),
                                  width=832, height=1216, steps=20, max_vram=6.5, seed=42)

    def test_dimensions_reject_invalid_values(self):
        for value in ('255', '833', '4096'):
            with self.assertRaises(argparse.ArgumentTypeError):
                runner.dimensions(value)
        self.assertEqual(runner.dimensions('832'), 832)

    def test_prompt_is_one_literal_argument_and_tiling_enabled(self):
        args = self.args('image.png')
        command = runner.command(Path('models'), args, Path('image.png'))
        self.assertEqual(command[command.index('-p') + 1], args.prompt)
        self.assertIn('--vae-tiling', command)

    def test_output_and_sidecars_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'image.png'
            for suffix in ('', '.log', '.json'):
                path = Path(str(output) + suffix)
                path.write_text('keep')
                with self.assertRaises(FileExistsError):
                    runner.generate(Path(folder), self.args(output))
                self.assertEqual(path.read_text(), 'keep')
                path.unlink()

    def test_success_without_image_is_failure(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(runner, 'doctor'), patch.object(runner.subprocess, 'Popen') as process:
            process.return_value.wait.return_value = 0
            output = Path(folder) / 'image.png'
            with self.assertRaisesRegex(RuntimeError, 'did not save'):
                runner.generate(Path(folder), self.args(output))
            self.assertFalse(Path(str(output) + '.json').exists())

    def test_nonzero_exit_is_failure(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(runner, 'doctor'), patch.object(runner.subprocess, 'Popen') as process:
            process.return_value.wait.return_value = 7
            with self.assertRaisesRegex(RuntimeError, 'exited 7'):
                runner.generate(Path(folder), self.args(Path(folder) / 'image.png'))

    def test_png_dimensions_are_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'image.png'
            output.write_bytes(b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 832, 1216))
            runner.verify_png(output, 832, 1216)
            with self.assertRaises(RuntimeError):
                runner.verify_png(output, 512, 512)

    def test_download_reuses_verified_file_and_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'model').write_bytes(b'good')
            asset = dict(path='model', size=4, sha256=hashlib.sha256(b'good').hexdigest())
            self.assertEqual(download.download(root, asset), root / 'model')
            (root / 'model').write_bytes(b'evil')
            with self.assertRaisesRegex(RuntimeError, 'refusing to overwrite'):
                download.download(root, asset)
            self.assertEqual((root / 'model').read_bytes(), b'evil')

    def test_archive_cannot_escape_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / 'runtime.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('../escape.txt', 'bad')
            with self.assertRaisesRegex(RuntimeError, 'outside'):
                download.extract(archive, Path(folder) / 'runtime')
            self.assertFalse((Path(folder) / 'escape.txt').exists())


if __name__ == '__main__':
    unittest.main()
