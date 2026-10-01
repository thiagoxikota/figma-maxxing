# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [semantic versioning](https://semver.org/).

## [1.0.0] - 2026-10-01

First public release.

### Added

- Eight skills: `figma-canon`, `figma-preflight`, `figma-orient`, `figma-slop-check`, `figma-handoff-gate`, `figma-comment-fix-loop`, `figma-click-flow`, `figma-bridge-doctor`.
- `figma-canon` references: Plugin API core and data rules, write atomicity, auto layout, naming, state coverage, handoff format, quality rubric, AI slop signatures, inspection protocol, security, rate limits, Code Connect setup, Plugin API anomalies and field notes.
- Advisory file lock for agent sessions that share a Figma file (`skills/figma-preflight/scripts/figma_lock.py`).
- Optional precheck hook for `figma_execute` (`hooks/figma-canon-precheck.py`), warn mode by default.
- Installer that copies skills and never overwrites (`install.py`).
- Claude Code plugin and marketplace manifests.
- `llms.txt` index for AI readers, README in English and Portuguese.
- Tests and CI on macOS and Ubuntu.
- `llms.txt`: a self-contained digest for chat AIs, with the rules any designer can use without installing anything.
- Diagram of how the skills fit together, in light and dark versions.
- Code of conduct, issue forms, pull request template, Dependabot for GitHub Actions.

### Security

- The `mcp-direct` fallback daemon accepts only local requests that carry its bearer token and a JSON content type, and refuses any request with an `Origin` header.
- `figma-bridge-doctor` asks before any step that quits Figma Desktop and kills only orphan servers without asking.
- The advisory file lock uses an OS file lock, so a crashed session never leaves the lock directory blocked.

[1.0.0]: https://github.com/thiagoxikota/figma-maxxing/releases/tag/v1.0.0
