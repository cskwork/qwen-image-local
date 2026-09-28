"""Local Qwen-Image-2.1 runner. Python 3.11+; Windows NVIDIA runtime."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

SKILL = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name('assets.json')
VISION_MANIFEST = Path(__file__).with_name('vision.json')
VISION_NAME = 'models/mmproj-Qwen3VL-8B-Instruct-F16.gguf'
MODEL_NAMES = (
    'models/qwen-image-2.1-Q4_K_M.gguf',
    'models/Qwen3-VL-8B-Instruct-UD-Q4_K_XL.gguf',
    'models/vae/qwen_image_2.1_vae_bf16.safetensors',
)


def model_root(explicit=None):
    value = explicit or os.environ.get('QWEN_IMAGE_LOCAL_ROOT')
    local = SKILL / 'local.json'
    if not value and local.exists():
        value = json.loads(local.read_text(encoding='utf-8-sig')).get('root')
    return Path(value or Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'qwen-image-local').expanduser().resolve()


def check_files(root, verify=False):
    from download import sha256
    assets = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for relative in ('runtime/sd-cli.exe', 'runtime/ggml-cuda.dll', 'runtime/cudart64_12.dll', *MODEL_NAMES):
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f'Missing file: {path}. Check --root or run install.')
    for asset in assets:
        if asset['path'] in MODEL_NAMES:
            path = root / asset['path']
            if path.stat().st_size != asset['size']:
                raise RuntimeError(f'Model size mismatch: {path}')
            if verify and sha256(path) != asset['sha256']:
                raise RuntimeError(f'Model checksum mismatch: {path}')


def doctor(root, verify=False):
    if sys.platform != 'win32':
        raise RuntimeError('This package supports Windows x64 with NVIDIA CUDA only.')
    check_files(root, verify)
    result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                            capture_output=True, text=True, check=True)
    print(f'Root: {root}\nGPU: {result.stdout.strip()}\nModel files ready.', flush=True)


def dimensions(value):
    number = int(value)
    if number < 256 or number > 2048 or number % 32:
        raise argparse.ArgumentTypeError('Dimensions must be multiples of 32 from 256 to 2048.')
    return number


def command(root, args, output):
    result = [str(root / 'runtime/sd-cli.exe'), '--diffusion-model', str(root / MODEL_NAMES[0]),
            '--llm', str(root / MODEL_NAMES[1]), '--vae', str(root / MODEL_NAMES[2]),
            '-p', args.prompt, '-W', str(args.width), '-H', str(args.height),
            '--steps', str(args.steps), '--cfg-scale', '6.0', '--sampling-method', 'euler',
            '--offload-to-cpu', '--fa', '--vae-tiling', '--max-vram', str(args.max_vram),
            '-s', str(args.seed), '-o', str(output)]
    if getattr(args, 'reference', None):
        result += ['--llm_vision', str(root / VISION_NAME), '-r', str(args.reference)]
    return result


def reference_ready(root):
    asset = json.loads(VISION_MANIFEST.read_text(encoding='utf-8'))[0]
    path = root / VISION_NAME
    return path.is_file() and path.stat().st_size == asset['size']


def verify_png(path, width, height):
    with path.open('rb') as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
        raise RuntimeError(f'Output is not a PNG: {path}')
    if struct.unpack('>II', header[16:24]) != (width, height):
        raise RuntimeError(f'Output dimensions differ from requested dimensions: {path}')


def generate(root, args):
    from generation_lock import generation_lock
    with generation_lock(root):
        return _generate(root, args)


def _generate(root, args):
    if not args.prompt.strip():
        raise ValueError('Prompt must not be empty.')
    if not 1 <= args.steps <= 100 or not 1 <= args.max_vram <= 128:
        raise ValueError('Steps must be 1–100 and max-vram must be 1–128 GiB.')
    output = Path(args.output).expanduser().resolve()
    if output.suffix.lower() != '.png':
        raise ValueError('Output must have a .png extension.')
    log = Path(str(output) + '.log')
    meta = Path(str(output) + '.json')
    for path in (output, log, meta):
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite: {path}')
    doctor(root)
    reference = getattr(args, 'reference', None)
    if reference:
        if not reference_ready(root):
            raise RuntimeError('Reference support is missing. Run install-reference first.')
        if not Path(reference).is_file():
            raise FileNotFoundError(f'Reference image not found: {reference}')
    output.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    with log.open('x', encoding='utf-8') as stream:
        process = subprocess.Popen(command(root, args, output), stdout=stream, stderr=subprocess.STDOUT)
        print(f'Generating locally. Log: {log}', flush=True)
        try:
            code = process.wait()
        except KeyboardInterrupt:
            process.terminate()
            process.wait()
            raise
    if code:
        raise RuntimeError(f'Generation exited {code}. Inspect {log}')
    if not output.is_file():
        raise RuntimeError(f'Runtime exited successfully but did not save {output}. Inspect {log}')
    verify_png(output, args.width, args.height)
    elapsed = round(time.perf_counter() - start, 2)
    metadata = dict(model='Qwen-Image-2.1 Q4_K_M', text_encoder='Qwen3-VL-8B-Instruct UD-Q4_K_XL',
                    runtime='stable-diffusion.cpp 3f8527a CUDA12', prompt=args.prompt,
                    width=args.width, height=args.height, steps=args.steps, seed=args.seed,
                    cfg_scale=6.0, elapsed_seconds=elapsed, vae_tiling=True)
    if reference:
        metadata['reference_file'] = Path(reference).name
    with meta.open('x', encoding='utf-8') as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
    print(f'Saved: {output}\nElapsed: {elapsed} seconds', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', help='Model/runtime installation directory')
    sub = parser.add_subparsers(dest='action', required=True)
    check = sub.add_parser('doctor', help='Check local files and NVIDIA GPU')
    check.add_argument('--verify', action='store_true', help='Also verify model SHA-256 hashes')
    sub.add_parser('install', help='Download and verify pinned model/runtime files')
    sub.add_parser('install-reference', help='Download the optional 1.16GB vision component')
    web = sub.add_parser('serve', help='Open the local prompt-and-image web app')
    web.add_argument('--port', type=int, default=8766)
    web.add_argument('--open', action='store_true', dest='open_browser')
    web.add_argument('--output-dir', type=Path, help='Image directory (default: ROOT/outputs/web)')
    gen = sub.add_parser('generate', help='Generate one image without network access')
    gen.add_argument('--prompt', required=True)
    gen.add_argument('--output', required=True)
    gen.add_argument('--width', type=dimensions, default=832)
    gen.add_argument('--height', type=dimensions, default=1216)
    gen.add_argument('--steps', type=int, default=20)
    gen.add_argument('--seed', type=int, default=42)
    gen.add_argument('--max-vram', type=float, default=6.5, help='GPU memory budget in GiB')
    gen.add_argument('--reference', type=Path, help='Reference PNG or JPEG (requires install-reference)')
    args = parser.parse_args()
    root = model_root(args.root)
    if args.action == 'doctor':
        doctor(root, args.verify)
    elif args.action in ('install', 'install-reference'):
        if sys.platform != 'win32':
            raise RuntimeError('Installer supports Windows x64 only.')
        if not shutil.which('curl.exe'):
            raise RuntimeError('curl.exe was not found on PATH.')
        from download import install
        manifest = VISION_MANIFEST if args.action == 'install-reference' else MANIFEST
        install(root, json.loads(manifest.read_text(encoding='utf-8')))
        doctor(root, verify=True)
    elif args.action == 'serve':
        from web_server import serve
        serve(root, args.port, args.open_browser, args.output_dir)
    else:
        generate(root, args)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
