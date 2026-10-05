# Contributing

Most rules here came from something that broke in a real file. New ones follow that bar.

## Where to post what

- **A question** about a skill or your setup: [open an issue](https://github.com/thiagoxikota/figma-maxxing/issues/new/choose). If a step assumes a path or a tool you do not have, use the setup form.
- **Your file before and after** a run: a blank issue with the screenshots. Misses are as welcome as wins.
- **Something surprised you and you have no fix yet**: a blank issue with the symptom. Once someone has a fix that ran, it becomes a New gotcha.
- **A gotcha with a fix you ran**: the New gotcha issue form, or a pull request.
- **A rule that stopped being true**: the correction issue form, with the version or month where you saw the new behavior.
- **A bug in a script, the hook or the installer**: the bug issue form.
- **An idea** for a skill or a check: a blank issue.
- **A security problem**: report it privately, as described in [SECURITY.md](SECURITY.md).

## What is welcome

- **A new gotcha.** A Figma Plugin API behavior that surprised you, with the symptom, the cause and the fix. Add it to `skills/figma-canon/references/plugin-api-anomalies.md` (Plugin API, with a line in the index at the top) or `field-notes.md` (bridge, MCP server, several agents on one file), and list it in `docs/gotchas.md`.
- **A correction.** Figma changes. If a rule here stopped being true, open an issue or a pull request with the version or date where you saw the new behavior.
- **A sharper check.** A gate step that would have caught a defect that reached a developer or a stakeholder.

## The bar for a gotcha

1. You hit it yourself. No rules copied from documentation, a forum or a model's guess.
2. It has a symptom someone can recognize ("the section renders black"), a cause (or "not established") and a fix that you ran.
3. It carries a month ("Field note, 2026-10.") so readers can judge how fresh it is.
4. A detector snippet when one exists. A rule an agent can check beats a rule an agent has to remember.

The entry shape, with a real example, is in [AGENTS.md](AGENTS.md#the-gotcha-bar).

## Never include

- Client, employer, product or people names. Write "a client project".
- Figma file keys, file URLs or node ids from real files. Use `<fileKey>` and `123:456`.
- Tokens, cookies or absolute paths from your machine.
- Screenshots of work you do not own.

## Style

- English, plain and direct. Skills are operating instructions for an agent, not articles.
- No em dash, no emoji, straight quotes.
- No unmeasured claims ("faster", "first", "best"). A number comes from a script or a real run.
- Keep `SKILL.md` under 500 lines. Long detail goes in `references/`.
- A skill's `name` in the frontmatter matches its folder.
- A change to `README.md` goes into `docs/README.pt-BR.md` too.

## Before you open a pull request

```bash
python3 -m pip install pyyaml
python3 -m unittest discover -s tests -v
python3 scripts/check_api.py
python3 scripts/count_claims.py --check
```

The tests check frontmatter, links between skills and references, the lock, the hook, the installer and the style rules above. `check_api.py` checks every Plugin API name a skill mentions against the pinned `@figma/plugin-typings`, so an invented method or a typo fails before it reaches anyone's file. It downloads the typings from registry.npmjs.org once; `--typings-dir` works offline. `count_claims.py --check` recounts every skill, gotcha and check number the docs cite. A new gotcha changes the count in both READMEs and in the banner: update the lines it names and re-render the banner from `assets/banner.html`, or leave that to the maintainer and say so in the pull request.

If a user could notice your change, add a line under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md). The version rule is in [AGENTS.md](AGENTS.md#version-and-changelog).

## Using an AI agent to contribute

Welcome. Point it at [AGENTS.md](AGENTS.md) first (Claude Code reads it through `.claude/CLAUDE.md`). Say in the pull request that an agent drafted it, and which person ran the fix behind any new gotcha. A pull request with a gotcha nobody hit, or a check result nobody ran, will be closed.

By contributing you agree that your contribution is licensed under the [MIT license](LICENSE) and that you follow the [code of conduct](CODE_OF_CONDUCT.md).
