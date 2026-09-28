# Setup and recovery

This package targets Windows x64 with an NVIDIA GPU and Python 3.11 or newer. Use a current NVIDIA driver compatible with CUDA 12. The measured machine had an RTX 4060 8GB and 32GB system RAM. Other configurations have not been benchmarked.

## Existing installation

Pass `--root` before the command, set `QWEN_IMAGE_LOCAL_ROOT`, or create `local.json` in the skill directory:

```json
{"root": "C:\\models\\qwen-image-local"}
```

The root needs `runtime/sd-cli.exe` and the three model paths named by `scripts/assets.json`. `doctor --verify` checks the model hashes. Keep local configuration out of Git.

## Fresh installation

After the user authorizes downloading the models and runtime, run:

```powershell
python scripts/qwen_local.py install
python scripts/qwen_local.py doctor --verify
```

Or supply `--root 'D:\models\qwen-image-local'` before `install`. Allow about 16GB free disk space for a fresh installation. Downloads use pinned revisions, bounded retries, resumable ranges, and SHA-256 verification. A mismatched existing file causes an explicit failure; it is never silently replaced. Retry interrupted downloads with the same command. A concurrent installation is refused. If a killed process leaves `.install.lock`, verify that its recorded PID is no longer running before manually removing that lock.

`install` reads only the bundled asset manifest. It does not run downloaded scripts; it extracts verified Windows executable/DLL archives. Model licenses are separate from this package's code license. See the upstream repositories linked in the root README before using or redistributing their weights.

## Optional reference support

After authorization to add reference conditioning, run `python scripts/qwen_local.py install-reference` with the same root. This downloads and verifies the pinned 1.16GB `mmproj-Qwen3VL-8B-Instruct-F16.gguf` vision component. It is separate from the base installation. Refresh the studio to enable attachments. One PNG/JPEG (8MB maximum, 4096 pixels per side) can be attached per web request; selected history images can also be references. CLI uses `generate --reference PATH --prompt TEXT --output NEW.png`.

The reference path is experimental in v0.1.0; unit tests and attachment handling are verified, but completed GPU reference output still needs user acceptance testing. Do not promise identity preservation or speed based on the text-only benchmark.

## Failure handling

- Missing root/files: check the configured root before downloading duplicates.
- Download failure: rerun the install command. If a final checksum fails, keep the diagnostics and repair the affected partial download only with the user's authorization.
- CUDA unavailable: confirm `nvidia-smi` works and the CUDA12 runtime DLLs are beside `sd-cli.exe`. Do not silently fall back to CPU or a hosted API.
- Memory pressure: close other GPU workloads or lower resolution. VAE tiling is already enabled. A different GPU may need `--max-vram` adjusted.
- Nonzero exit or missing/invalid image: report the failure and show the `.log` path. The helper preserves diagnostic output and fails closed.

When installing the skill into an agent's skill directory, copy this entire `qwen-image-local` folder. Existing skill directories should be reviewed before replacement. A new chat may be needed for discovery.
