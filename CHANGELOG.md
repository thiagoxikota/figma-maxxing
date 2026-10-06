# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Changed

- Both READMEs: move installation navigation into the opening, qualify the audit instructions and keep the demo test limits beside each result. Remove requests for stars.
- Social preview: paper background, red accent and larger text, with an unmodified crop of the real demo screenshot and an embedded licensed font.

## [1.2.0] - 2026-10-05

### Changed

- `figma-slop-check`: the Rigor lens is rewritten as 11 rigor checks in 5 groups, ordered by what a node stores: bound or loose (`color`, `text-style`, `scale`), components intact (`detached`, `properties`), auto layout sized right (`sizing`, `collapse`, `fill-in-hug`), words (`wording`, `names`) and pixels (`screenshot`). Spacing, radius and icon size are one `scale` check. Findings are tagged by check name, not by number. `references/detectors.md` becomes `references/checks.md`.
- `figma-slop-check`: each finding is labeled swap, snap or ask (it was exact, approximation or new decision), with a signed distance on a snap. One `.figma-slop-check/decisions.json` replaces `exceptions.json` and `drift-accepted.json`: an `intentional` entry leaves the punch list, a `debt` entry comes back with its distance until it is fixed, and an applied snap is logged in the run file. An existing `exceptions.json` or `drift-accepted.json` is no longer read; move its entries by hand. `references/severity-and-exceptions.md` becomes `references/punch-list.md`.
- Both READMEs and `docs/works-with.md` say that the blind test ran with the earlier rigor lens.

### Removed

- `figma-slop-check`: the glass-over-content detector and the frame-name label clearance detector (an 80px floor between stacked frames). The slop lens keeps one line for each: no glass stacked on glass or with nothing behind it, and no frame-name label landing on the frame above.

## [1.1.1] - 2026-10-05

### Security

- `daemon.mjs`, the opt-in `mcp-direct` daemon of `figma-bridge-doctor`, asks npm for its cache through `execFileSync` with a fixed argument list and no shell, instead of `execSync` with a command string. Cisco skill scanner 2.0.14 (`--policy balanced`) reported that line as CRITICAL `COMMAND_INJECTION_JS_CHILD_PROCESS`; after the change it reports 0 critical and 0 high findings.
- `daemon.mjs` no longer sends error text to the HTTP client (CodeQL `js/stack-trace-exposure`). The client gets a fixed message per failure class, and the detail goes to the daemon's stderr. The `mcp-direct` README describes both changes.
- The local server recipes for loading images and saving exports (`plugin-api-data.md`, `plugin-api-anomalies.md`, `figma-comment-fix-loop`) bind `::1`, or `127.0.0.1` where `localhost` resolves only there, instead of `::`, which listens on every interface. The export server now comes as code in `plugin-api-data.md`: it keeps only the basename of `name`, accepts only `.png` names and PNG bytes, and writes into one folder. `Access-Control-Allow-Origin: *` stays, with its reason: Figma documents that plugin iframes have a `null` origin. `security-canon.md` gains a section on local servers the agent starts, and `PRIVACY.md` mentions the recipe.

### Fixed

- Two field notes contradicted `@figma/plugin-typings` 1.140.0. They are qualified, not removed: writes under a locked ancestor that did not take, and `setTimeout` that did not fire. Each now says it was seen through the figma-console bridge (`figma_execute`), quotes what the typings say, and gives the cause as not established. `figma-preflight`, `docs/gotchas.md`, `llms.txt` and both READMEs carry the same qualification. Both note headings, and so their anchors, changed.
- Both READMEs: the 14 unplanted items describe 13 distinct problems (both checks flagged the same rename); the test ran on a live Figma file built for the test; the M8ven entry is described as it is (claimed by the author, public grade C (Emerging), code sub-score 100 read on 2026-10-04 at commit 1dca321); each install route says where it ran from (GitHub main at 5afe295, the v1.1.0 release, GitHub, or a local copy).
- `docs/works-with.md`: "Demo run" no longer says "end to end". It counts what did not run as written (19 skill steps in the audit, 3 of the 8 preflight checks in the fix) and says detector 8 changed after the run. The READMEs and `llms.txt` say the same.
- The 1.1.0 entry below gives the limits of the 10 of 10 result in the same sentence.
- `fetch_comments.py` handles a read timeout and an answer that is not JSON, and prints the first 300 bytes of an HTTP error body, never the headers. Exit codes: 1 HTTP error, 2 usage or no token, 3 network error or timeout, 4 not JSON. Tests cover each branch without network.
- `security-canon.md`: `talktofigma` moves from BANNED/High, which cited no advisory, to UNVERIFIED (not evaluated here). The default deny still applies.

### Changed

- `figma-comment-fix-loop` lists the exit codes of `fetch_comments.py` and says to keep `comments-raw.json` out of git, because it holds commenter handles.
- Portuguese README: phrases that read as translations are rewritten ("Para começar", "O que dá errado, e qual skill pega", "Dá para usar na biblioteca do time", "um checklist", "reserva o arquivo com um lock"). The "Para começar" anchor changed.
- The README gotcha list starts with the gotchas that agree with Figma's docs and keeps one qualified field note.
- `scripts/release_notes.py` checks every JSON manifest with a version field and the version line of `llms.txt`, as its docstring says. `scripts/build_dist.py` says that six of the per-skill zips need `figma-canon` installed next to them.
- `AGENTS.md`: a "Cutting a release" section, ending with "never move a tag; ship the next patch".
- `.codexignore`: the first comment says scanners read it and Codex CLI 0.156.1 copies the whole repository regardless.
- Version 1.1.1 in every manifest, every `SKILL.md`, `CITATION.cff` and `llms.txt`.

## [1.1.0] - 2026-10-05

### Added

- `figma-comment-fix-loop/scripts/fetch_comments.py`: reads the open comments through the REST API with the token from the environment, sends it only to api.figma.com and never prints it. The skill calls it instead of an inline `curl`.
- `.codexignore`, and the square icon in the Codex and Cursor listings.
- Manifests for more agents, all at 1.1.0 with one shared description: a root `plugin.json` (Agent Plugins 1.0.0), `.codex-plugin/plugin.json` for Codex, `.cursor-plugin/plugin.json` for Cursor, `gemini-extension.json` for Gemini CLI and `skills.sh.json` for the skills.sh page groupings. The Codex, Copilot CLI and Gemini CLI installs were run from a local copy; Cursor was not tested.
- `docs/gotchas.md` ("Why does my agent...?"): every gotcha indexed by the symptom a designer sees, plus an index by literal error message. It links to the notes and never restates a fix.
- `docs/landscape.md`: a dated map of the Figma MCP servers, skill sets and catalogs, and how these skills compose with Figma's own.
- `docs/works-with.md`: which Figma connection each skill needs and how far each pair has been tested, with the blind demo on the official Figma MCP server (10 of 10 planted defects found, on one demo screen in one run; the agent that planted the defects had read the skills, and the auditor's prompt named the properties to inspect).
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

[1.2.0]: https://github.com/thiagoxikota/figma-maxxing/releases/tag/v1.2.0
[1.1.1]: https://github.com/thiagoxikota/figma-maxxing/releases/tag/v1.1.1
[1.1.0]: https://github.com/thiagoxikota/figma-maxxing/releases/tag/v1.1.0
[1.0.0]: https://github.com/thiagoxikota/figma-maxxing/releases/tag/v1.0.0
