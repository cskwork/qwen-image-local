# Qwen Image Local

Generate images on a Windows NVIDIA PC with **Qwen-Image-2.1 Q4**, directly from your coding agent or terminal. No hosted image API is used during generation.

[Landing page](https://cskwork.github.io/qwen-image-local/) · [Agent skill](skills/qwen-image-local/SKILL.md)

Current release: **v0.1.0** · [Download and release notes](https://github.com/cskwork/qwen-image-local/releases/latest)

![Actual locally generated portrait](docs/assets/portrait.png)

## What is tested

Windows, RTX 4060 **8GB**, 32GB RAM. The shown 832×1216 portrait took **134.2 seconds**, including runtime loading and saving, at 20 Euler steps, CFG 6, seed 42. One measured run is not a speed guarantee. The original BF16 run was interrupted, so no matched before/after benchmark is claimed. Other GPUs and operating systems are not validated.

## Install the skill

Requires Git and Python 3.11+. In PowerShell:

```powershell
git clone https://github.com/cskwork/qwen-image-local.git
cd qwen-image-local
$skillRoot = Join-Path $HOME '.codex\skills'
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
if (Test-Path (Join-Path $skillRoot 'qwen-image-local')) { throw 'Skill already exists; review it before replacing.' }
Copy-Item -Recurse skills\qwen-image-local $skillRoot
```

Start a new agent chat if needed, then ask:

> Use $qwen-image-local to create a studio portrait on my local PC.

> $qwen-image-local 로 내 PC에서 자연스러운 인물 사진을 만들어줘.

Other agents that support `SKILL.md` can use the same skill folder in their documented skill directory.

## Install the model once

Windows x64, NVIDIA CUDA-compatible driver, `curl.exe`, and around **16GB free disk space** are required. The measured system had 8GB VRAM and 32GB RAM. The installer downloads about 11GB from pinned upstream revisions and verifies SHA-256. Model weights are not included in this repository.

```powershell
python skills/qwen-image-local/scripts/qwen_local.py install
python skills/qwen-image-local/scripts/qwen_local.py doctor --verify
```

Default model storage: `%LOCALAPPDATA%\qwen-image-local`. For an existing installation, pass `--root` **before** the command:

```powershell
python skills/qwen-image-local/scripts/qwen_local.py --root 'D:\models\qwen-image-local' doctor
```

You can also set `QWEN_IMAGE_LOCAL_ROOT` or put `{"root":"D:\\models\\qwen-image-local"}` in the installed skill's `local.json`. Local configuration is ignored by Git. See [setup and recovery](skills/qwen-image-local/references/setup.md).

## Generate

### Local web studio

After installing Python and the models, double-click **`start-web.cmd`** in the repository. It starts a loopback-only server and opens the studio in your browser. Enter your prompt on the left; the generated image appears on the right with a Save PNG button. Keep the launcher running while generating.

Or run explicitly:

```powershell
python skills/qwen-image-local/scripts/qwen_local.py serve --open
```

For an existing model folder:

```powershell
python skills/qwen-image-local/scripts/qwen_local.py --root 'D:\models\qwen-image-local' serve --open
```

Default address: `http://127.0.0.1:8766/`. Use `serve --port 8770 --open` if that port is busy. Output images and their logs/settings are saved under the model root's `outputs/web`; use `--output-dir` after `serve` to change this. Each server handles one job at a time, and an OS lock also prevents concurrent generation across processes using the same model root.

Use **Previous / Next** or the thumbnails to browse versions. **Reuse prompt & settings** restores a selected version's controls for refinement; generating saves a new image without replacing the original. The latest 100 saved studio versions are loaded again after a server restart. Files beyond the displayed history are preserved. Corrupt history records are reported without deleting their files.

### Attach a reference image

Install the optional **1.16GB vision component** once:

```powershell
python skills/qwen-image-local/scripts/qwen_local.py install-reference
```

Use the same `--root` or local configuration as your main models. Refresh the studio, attach a PNG/JPEG, and describe what to keep or change. **Use image as reference** attaches a selected history version directly. Remove the reference to return to text-only generation. Uploads stay in the output folder's `references` subfolder; they are not sent to a hosted service. Limits: one reference per request, 8MB per image, and 4096 pixels per side.

CLI equivalent:

```powershell
python skills/qwen-image-local/scripts/qwen_local.py generate --reference reference.png --prompt 'Change the background to a garden, keeping the subject' --output outputs/with-reference.png
```

Reference conditioning is experimental in v0.1.0: the vision file and request path are implemented and verified by automated checks, but a completed reference-guided GPU generation has not yet been accepted. User testing is pending; results may not preserve every detail and can take longer than text-only generation.

Missing models are shown clearly in the page; install them with the existing `install` command, then restart the studio. No automatic model downloads occur from the web UI. The studio binds to 127.0.0.1, rejects cross-origin generation requests, and uses no external web resources. Do not expose it through a public tunnel or reverse proxy. This is a local single-user tool, not a hosted generation service. GitHub Pages remains the public introduction and cannot run your GPU.

### Command line

```powershell
python skills/qwen-image-local/scripts/qwen_local.py generate --prompt 'A natural studio portrait of an adult model in a cream linen shirt, gray background, soft light' --output outputs/portrait.png
```

Defaults: **832×1216**, **20 steps**, seed **42**. Options: `--width`, `--height`, `--steps`, `--seed`, `--max-vram`. Dimensions must be multiples of 32 from 256 to 2048; higher resolutions are not benchmarked. Outputs must be PNG. Existing images, logs, and metadata files are never overwritten. Tiled VAE decoding is enabled for the tested 8GB GPU.

The helper saves the PNG, a diagnostic `.png.log`, and generation settings/timing in `.png.json`. It checks the exit status, output existence, PNG header, and dimensions; the agent then visually inspects the image. Errors remain errors. There is no automatic model deletion or hosted fallback. CLI generation makes no network calls; the optional studio uses local loopback requests only.

Both text-only and reference-conditioned requests are exposed. The text-only workflow has completed GPU verification; reference-conditioned output quality still needs user testing.

## Models and licenses

| Component | Upstream | File size |
|---|---|---:|
| Image model, Q4_K_M | [Unsloth Qwen-Image-2.1-GGUF](https://huggingface.co/unsloth/Qwen-Image-2.1-GGUF) | 4.20GB |
| Text encoder, UD-Q4_K_XL | [Unsloth Qwen3-VL-8B-Instruct-GGUF](https://huggingface.co/unsloth/Qwen3-VL-8B-Instruct-GGUF) | 5.15GB |
| Model-specific BF16 VAE | [Unsloth Qwen-Image-2.1-FP8](https://huggingface.co/unsloth/Qwen-Image-2.1-FP8) | 0.68GB |
| Windows CUDA12 runtime | [stable-diffusion.cpp 3f8527a](https://github.com/leejet/stable-diffusion.cpp/releases/tag/master-929-3f8527a) | 0.90GB download |
| Optional reference vision encoder | [Qwen Qwen3-VL-8B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct-GGUF) | 1.16GB |

Sizes are download sizes, not total VRAM requirements. Upstream models and runtime retain their own licenses, including the Qwen Research license shown by the image-model publisher. Check those terms for your intended use; this repository does not relicense the weights. This is an independent integration, not an official Qwen or Unsloth product.

Repository code and documentation: [MIT](LICENSE). The sample is an AI-generated fictional adult portrait produced with the documented local model; it is not a real-person endorsement. Its PNG retains generation parameters.

## Development

```powershell
python -m unittest discover -s tests -v
python -m http.server 8765 --directory docs
```

Tests cover failure reporting, output preservation, literal prompt arguments, model verification, and archive path protection. CI does not download model weights or claim GPU inference coverage. Actual local inference is verified separately before publication.
