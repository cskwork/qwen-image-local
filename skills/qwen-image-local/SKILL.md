---
name: qwen-image-local
description: Generate images locally with Qwen-Image-2.1 on Windows NVIDIA PCs. Use when the user requests local Qwen image generation, this installed 4-bit model, or setup of this local workflow.
---

# Qwen Image Local

Use the bundled Python helper for local text-to-image generation. It runs the Q4_K_M image model and UD-Q4_K_XL text encoder through stable-diffusion.cpp. Python 3.11+, Windows x64, NVIDIA CUDA, and curl are required. RTX 4060 8GB has been tested; other devices need verification.

## Generate

Resolve `scripts/qwen_local.py` relative to this skill, then run:

```powershell
python scripts/qwen_local.py doctor
python scripts/qwen_local.py generate --prompt 'Describe the requested image' --output 'C:\absolute\path\image.png'
```

Use an existing working Python 3.11+ interpreter. A model root comes from `--root`, `QWEN_IMAGE_LOCAL_ROOT`, or this skill's ignored `local.json`, in that order; otherwise the helper uses `%LOCALAPPDATA%\qwen-image-local`. Run `python scripts/qwen_local.py --root 'C:\models\qwen-local' doctor` to use another installation. Read [setup](references/setup.md) only if installation is missing or needs repair.

Translate the user's image intent into a clear prompt while preserving subject, style, and constraints. For an underspecified ordinary image, choose reasonable details and proceed. Use the existing model; downloading or changing a model is a separate installation action. Keep the user's requested local execution: report a local failure rather than silently switching to a hosted image tool.

Defaults are 832×1216, 20 steps, CFG 6, seed 42, 6.5 GiB VRAM budget, and tiled VAE decoding. Use `--width` and `--height` in multiples of 32, `--steps`, and `--seed` when requested. Keep output paths unique; existing images and sidecars are protected against overwriting.

For a reference-guided request, inspect the supplied image, ensure the optional vision component is installed (see setup), and pass `--reference 'absolute/path.png'` along with the user's instructions. Do not describe plain prompt regeneration as image editing. Reference-conditioned GPU output is experimental in v0.1.0 and needs actual output verification before claiming success or subject preservation.

## Local web studio

When the user wants a prompt-entry page with the output beside it, run `python scripts/qwen_local.py serve --open` with the same root configuration. It serves the bundled `web/` assets at `http://127.0.0.1:8766/`. Keep the server process alive for the user; use `--port` after `serve` when the default port is occupied. Outputs default to the model root's `outputs/web`. Verify readiness and, when testing generation, submit through the page and wait until the actual image is visible. The web UI runs one job at a time, requires local models, and does not download models automatically. See [setup](references/setup.md) for first-time installation.

The studio provides Previous/Next history, prompt/settings reuse, PNG/JPEG attachments, and selected-version references. The latest 100 saved versions survive restarts. Prior images and uploads remain on disk. Generation uses an OS lock per model root, including across studio windows and CLI processes.

## Completion

Stay with the process until it exits. A launch or a progress percentage is not completion. Require exit code 0 and the helper's saved-image confirmation. Open the PNG using the available image viewer, check it against the request, then display it with an absolute path. Report the measured elapsed time from its JSON sidecar when useful. Keep failures explicit and preserve logs; do not claim a performance improvement from unmatched settings.

Normal generation uses local files and no image API or network request. Initial installation downloads roughly 11 GB and needs additional space for extraction and temporary files. Never remove the user's original models as part of installation or generation.
