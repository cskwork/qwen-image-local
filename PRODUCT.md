# Product

<!-- impeccable:product-schema 1 -->

## Platform
web, plus a Windows command-line skill

## Stack
Static HTML/CSS/JavaScript on GitHub Pages, Python 3.11+ standard-library helpers. An optional loopback-only Python server runs the local studio. No remote service or database is required.

## Users and purpose
People using an AI coding agent on a Windows NVIDIA PC who want to generate images locally with Qwen-Image-2.1. The owner requested a reusable skill, public GitHub repository, and public landing page after a successful local generation.

## Capabilities and constraints
Text-to-image only. Q4_K_M image model, UD-Q4_K_XL text encoder, model-specific BF16 VAE, pinned stable-diffusion.cpp Windows CUDA12 runtime. Downloads are explicit and checksummed; generation is local. Existing models can be reused through a configurable root. No model weights are committed or relicensed. No cloud generation fallback. Local studio: prompt and settings on the left, image and download on the right; one active job, explicit failures, same-origin requests. Current job survives page refresh, while saved images survive server restarts.

## Evidence
The original portrait was generated on RTX 4060 8GB, Windows, at 832×1216, 20 Euler steps, CFG 6, seed 42. Total invocation time was 134.2 seconds. This is one measured run, not a performance guarantee. No completed BF16 comparison exists. Source PNG contains its generation parameters. A second run through the packaged skill must succeed before publishing.

## Assumptions
Korean landing copy with English technical names; international users can read the English README. The site introduces installation and shows the actual output. It does not run generation in a browser.
