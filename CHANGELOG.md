# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

## [1.1.0] - 2026-10-05

### Added

- `figma-comment-fix-loop/scripts/fetch_comments.py`: reads the open comments through the REST API with the token from the environment, sends it only to api.figma.com and never prints it. The skill calls it instead of an inline `curl`.
- `.codexignore`, and the square icon in the Codex and Cursor listings.
- Manifests for more agents, all at 1.1.0 with one shared description: a root `plugin.json` (Agent Plugins 1.0.0), `.codex-plugin/plugin.json` for Codex, `.cursor-plugin/plugin.json` for Cursor, `gemini-extension.json` for Gemini CLI and `skills.sh.json` for the skills.sh page groupings. The Codex, Copilot CLI and Gemini CLI installs were run from a local copy; Cursor was not tested.
- `docs/gotchas.md` ("Why does my agent...?"): every gotcha indexed by the symptom a designer sees, plus an index by literal error message. It links to the notes and never restates a fix.
- `docs/landscape.md`: a dated map of the Figma MCP servers, skill sets and catalogs, and how these skills compose with Figma's own.
- `docs/works-with.md`: which Figma connection each skill needs and how far each pair has been tested, with the blind demo on the official Figma MCP server (10 of 10 planted defects found).
- A `compatibility` field in every `SKILL.md`, stating only real requirements.
- Security text inside the skills: a Trust boundary section in `figma-canon`, an Untrusted input rule in `figma-orient` and `figma-comment-fix-loop`, and a "What it can change on your machine" section that opens `figma-bridge-doctor`.
- `figma-orient` accepts the official Figma MCP server as a read path, with a call budget.
- `figma-bridge-doctor` references `layer1-recovery.md`, `plugin-version-drift.md` and `rival-write-audit.md`, moved word for word out of its `SKILL.md`.
- `scripts/check_api.py` and `scripts/api-allowlist.txt`: every Plugin API name in the skills is checked against `@figma/plugin-typings` 1.140.0 (pinned, sha512 verified), including members that exist only in FigJam, Slides or Buzz.
- `scripts/count_claims.py`: every skill, gotcha and check count in the docs is recounted from the files.
- `scripts/build_dist.py`: reproducible release zips (one per skill, a plugin bundle and `SHA256SUMS`) read from a git commit. `scripts/release_notes.py`: a release fails unless the tag matches every version field and this file has the section.
- CI: the Plugin API check, the claim counts, the Agent Skills reference validator, the Claude Code plugin validator, a link check (lychee), a secret scan of the full history (gitleaks) and actionlint. New workflows: `drift.yml` (weekly check against the newest typings and link rot, opens an issue), `release.yml` (build twice, compare bytes, attach a build provenance attestation) and `scorecard.yml` (OpenSSF Scorecard).
- `AGENTS.md`, the contributor guide for AI agents, with `CLAUDE.md` pointing to it. `PRIVACY.md` (no telemetry, nothing collected). `CITATION.cff`.
- Issue forms for a rule that stopped being true and for a bug in a script, hook or installer. Discussion forms for show and tell and for gotchas, for when Discussions is turned on. A private security report link in the issue chooser.
- `llms.txt`: the version, three agent rules (the annotations property, `get_design_context` can leave annotations out, the `use_figma` retry flag) and a section on how the rules are checked.
- Tests that fail when a shipped GIF or MP4 carries text metadata: a GIF comment, plain text or XMP block, or an MP4 tag other than the encoder (location, author, device).
- Assets: a before and after image and a GIF from the blind demo, a vertical video for social posts, a social preview card and a square icon (`assets/icon.png`). The banner shows the skill and gotcha counts.

### Changed

- README rewritten: quick start on the first screen, the blind test before and after, a section per agent, how the repository is verified and how far it has been tested. The Portuguese prompt moved to `docs/README.pt-BR.md`, which mirrors the English README.
- Claude Code manifests: `$schema`, `displayName`, `documentationUrl`, `supportUrl` and `privacyPolicyUrl`; the marketplace entry gains a category (`design`) and tags; keywords updated; the description now says "after every write". The marketplace and plugin names are unchanged, so `figma-maxxing@figma-maxxing-skills` still installs.
- Cross-skill references are relative links (`../figma-canon/references/...`), so they resolve inside the plugin layout.
- Script commands in `figma-bridge-doctor` and `figma-preflight` use `${CLAUDE_SKILL_DIR}/scripts/...`.
- The `mcp-direct` daemon starts only after the user says yes, and only the user installs the bridge watchdog.
- `figma-comment-fix-loop` shows the comments it will act on and waits for a yes before any write.
- `SECURITY.md`: a private advisory link, response times, supported versions and a section on the `mcp-direct` daemon. `CONTRIBUTING.md`: where to post what, the API check, the changelog rule and contributing with an agent.
- Dependabot runs weekly and also updates the CI Python dependencies, which are pinned by sha256. Every GitHub Action is pinned to a commit SHA.
- `.gitattributes` counts Markdown in the language bar.
- The diagram of how the skills fit together names both write tools, `use_figma` and `figma_execute`.
- `figma-canon/references/security-canon.md` cites Figma's MCP server FAQ for the seat rules: a Full seat writes outside drafts, and a Dev seat only inside its own drafts.

### Fixed

- Annotations: `plugin-api-data.md` taught `node.getAnnotations()` and `figma.setAnnotations()`, which do not exist. It now uses the `node.annotations` property and `figma.annotations`, checked against `@figma/plugin-typings` 1.140.0.
- `use_figma` is no longer described as always atomic: on an error, obey `safeToRetryWithoutCanvasRead` and read the canvas before retrying when it is `false`.
- `figma-slop-check` detector 8 also reads `detachedInfo` on FRAME nodes. Figma turns a detached instance into a FRAME, so the rule that read only INSTANCE nodes could not see one. The blind demo found the gap; the new rule has not run since.
- `draw-overlay.js` (`figma-click-flow`) no longer depends on `figma.loadAllPagesAsync()`, which Figma lists as not implemented in `use_figma`, and checks that `reactions` and `absoluteBoundingBox` exist before reading them.

### Security

- `daemon.mjs` reads `npm_config_cache` from the environment before it runs `npm`.
- Every CI job has a read-only token, except the release job (contents, id-token, attestations), the drift job (issues) and the Scorecard job (security-events, id-token).

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
- `figma-bridge-doctor` asks before any step that quits Figma Desktop, and its reset script never quits Figma unless `FIGMA_FULL_RESET=1` is set. Without asking, it kills only orphan servers.
- The advisory file lock uses an OS file lock, so a crashed session never leaves the lock directory blocked.

[1.0.0]: https://github.com/thiagoxikota/figma-maxxing/releases/tag/v1.0.0
