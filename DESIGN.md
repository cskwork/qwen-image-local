---
name: Qwen Image Local
description: A clear, evidence-led Korean landing page for local image generation on Windows NVIDIA PCs.
colors:
  primary: "#ff785b"
  neutral-bg: "#18212b"
  neutral-surface: "#f3f5f7"
  neutral-text: "#f3f5f7"
  neutral-ink: "#18212b"
  neutral-muted: "#b8c3ce"
  neutral-muted-on-light: "#52606e"
  border: "#46515c"
typography:
  display:
    fontFamily: "Manrope, Noto Sans KR, sans-serif"
    fontSize: "clamp(52px, 6vw, 84px)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.04em"
  heading:
    fontFamily: "Manrope, Noto Sans KR, sans-serif"
    fontSize: "clamp(30px, 3.4vw, 44px)"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "-0.035em"
  body:
    fontFamily: "Manrope, Noto Sans KR, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.75
  code:
    fontFamily: "Consolas, Courier New, monospace"
    fontSize: "13px"
    lineHeight: 1.8
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-ink}"
    height: "54px"
    padding: "14px 22px"
  button-secondary:
    backgroundColor: "{colors.neutral-bg}"
    textColor: "{colors.neutral-text}"
    height: "54px"
    padding: "14px 22px"
  command-panel:
    backgroundColor: "{colors.neutral-bg}"
    textColor: "{colors.neutral-text}"
---

## Overview

**Creative North Star: Local generation, shown plainly.** The page pairs a restrained dark canvas with a bright real output, then gives visitors the installation steps and measured run details. Korean carries the explanation; English remains for product names and commands.

**The Evidence First Rule.** Keep the generated portrait prominent and connect it to the concrete hardware, settings, and timing shown farther down the page.

## Colors

Use the dark ink canvas for the hero, tested results, and footer. The pale surface marks the setup and closing sections. Coral identifies the main action and focus state; muted text supports secondary details while preserving contrast against each surface.

## Typography

Use Manrope with Noto Sans KR fallbacks for interface and Korean copy. Keep display headings large and tightly tracked, body copy open, and technical commands in the compact monospace stack. Preserve comfortable line height for Korean text.

## Layout

At wide widths, constrain content to a centered 1200px maximum and pair hero copy with the portrait. The setup section uses a narrower explanatory column beside the command panel. Below 700px, stack these regions, keep 20px side gutters, and reduce section spacing. Measurement rows become a compact label/value layout.

**The Narrow Screen Rule.** Let long commands scroll horizontally inside their own panel; keep the surrounding page within the viewport.

## Elevation & Depth

The page is flat: separate sections with dark and pale surfaces, and use thin rules for grouping. Do not add card shadows or floating layers.

## Shapes

Use square corners for buttons and command surfaces. Thin dividers define groups; avoid decorative rounding.

## Components

Primary actions use a coral fill and dark text. Secondary actions use a dark fill and pale text. Keep controls at least 48px high where practical, show a clear coral keyboard focus outline, and underline text links on hover. The command panel pairs a dark terminal surface with a separate toolbar and visible horizontal scrolling when needed.

## Do's and Don'ts

- Keep the real generated portrait and its run context visible as evidence.
- Keep setup instructions and measured claims concrete and easy to scan.
- Keep the dark and pale section contrast and the single coral action accent.
- Don't imply cloud generation, image editing, or guaranteed performance.
- Don't commit to rounded cards, shadows, or extra accent colors that are absent from the page.
