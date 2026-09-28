# Changelog

## 0.1.0 — 2026-09-28

First versioned minor release.

- Local browser studio with prompts and settings on the left and generated images on the right.
- Previous/Next navigation, thumbnail history, and reuse of an earlier prompt and settings. Latest 100 saved studio versions survive restarts.
- Optional PNG/JPEG reference attachments and selected-version references, using a separately downloaded 1.16GB vision component.
- Windows launcher, configurable local model root, checksummed model installation, and local-only generation.
- Cross-process model lock to prevent multiple windows from using the same model concurrently.

Text-only GPU generation was previously verified. Automated tests cover request validation, persistence, references and locking. Completed reference-guided GPU generation and visual quality remain pending user testing; reference conditioning is experimental.
