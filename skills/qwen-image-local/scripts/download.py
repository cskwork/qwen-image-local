"""Pinned, checksummed downloads with resumable ranges and bounded retries."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import zipfile

CHUNK = 32 * 1024 * 1024


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download(root, asset):
    target = root / asset['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    size, digest = asset['size'], asset['sha256']
    if target.exists():
        if target.stat().st_size == size and sha256(target) == digest:
            print(f'Verified existing: {target.name}', flush=True)
            return target
        raise RuntimeError(f'Existing file differs; refusing to overwrite: {target}')
    partial = Path(str(target) + '.download')
    state = Path(str(target) + '.ranges.json')
    done = set(json.loads(state.read_text()) if state.exists() else [])
    count = (size + CHUNK - 1) // CHUNK
    if any(not isinstance(i, int) or i < 0 or i >= count for i in done):
        raise RuntimeError(f'Invalid resume state: {state}')
    if not partial.exists():
        done.clear()
        with partial.open('xb') as stream:
            stream.truncate(size)
    elif partial.stat().st_size != size:
        raise RuntimeError(f'Partial file size differs: {partial}')
    lock = threading.Lock()
    print(f'Downloading {target.name} ({size / 1e9:.2f} GB)', flush=True)

    def part(index):
        if index in done:
            return
        start, end = index * CHUNK, min(size, (index + 1) * CHUNK) - 1
        chunk = Path(str(target) + f'.chunk-{index}')
        result = subprocess.run([
            'curl.exe', '--fail', '--location', '--silent', '--show-error',
            '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '15',
            '--max-time', '90', '--speed-time', '20', '--speed-limit', '1024',
            '--retry', '3', '--retry-all-errors', '--range', f'{start}-{end}',
            '--output', str(chunk), asset['url']], capture_output=True, timeout=420)
        if result.returncode or not chunk.exists() or chunk.stat().st_size != end - start + 1:
            raise RuntimeError(f'Download failed: {target.name}, range {index}, exit {result.returncode}')
        data = chunk.read_bytes()
        with lock:
            with partial.open('r+b') as stream:
                stream.seek(start)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            done.add(index)
            pending = Path(str(state) + '.tmp')
            pending.write_text(json.dumps(sorted(done)))
            pending.replace(state)
            if len(done) % max(1, count // 10) == 0 or len(done) == count:
                print(f'{target.name}: {len(done)}/{count}', flush=True)
        chunk.unlink()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(part, range(count)))
    if sha256(partial) != digest:
        raise RuntimeError(f'Checksum mismatch: {partial}. No model was installed.')
    partial.rename(target)
    state.unlink(missing_ok=True)
    print(f'SHA-256 verified: {target.name}', flush=True)
    return target


def extract(archive, destination):
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            path = (destination / member.filename).resolve()
            if not path.is_relative_to(destination):
                raise RuntimeError('Archive contains a path outside the runtime directory.')
            if ((member.external_attr >> 16) & 0o170000) == 0o120000:
                raise RuntimeError('Archive contains a symbolic link.')
        package.extractall(destination)


def install(root, assets):
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.install.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError(f'Installation lock exists: {lock}. Check for an active installer.') from error
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(str(os.getpid()))
        needed = sum(a['size'] for a in assets if not (root / a['path']).exists())
        if needed and shutil.disk_usage(root).free < needed + 4 * 1024**3:
            raise RuntimeError('Not enough disk space: allow download size plus 4 GiB for extraction.')
        for asset in assets:
            downloaded = download(root, asset)
            if downloaded.suffix == '.zip':
                extract(downloaded, root / 'runtime')
        (root / 'skill-install-manifest.json').write_text(json.dumps(assets, indent=2))
        print('Installation complete.', flush=True)
    finally:
        lock.unlink()
