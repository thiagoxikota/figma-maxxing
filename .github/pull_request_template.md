## What changes

<!-- One or two sentences. -->

## Kind of change

- [ ] New gotcha
- [ ] Correction of a rule that stopped being true
- [ ] New or sharper check in a skill
- [ ] Script, hook, installer or tests
- [ ] Docs only

## Where this came from

<!-- For a new gotcha or rule: the symptom you saw, the cause if known, the fix you ran, and the month.
     For a correction: the version or date where you saw the new behavior. -->

## Checklist

- [ ] No client, product or people names, no file keys, no node ids from real files, no tokens, no absolute paths from my machine
- [ ] `python3 -m unittest discover -s tests` passes
- [ ] `python3 scripts/check_api.py` passes (needed when a skill mentions a Plugin API name)
- [ ] `python3 scripts/count_claims.py --check` passes (a new gotcha changes the count in both READMEs and the banner, or say the maintainer should update it)
- [ ] A line under `## [Unreleased]` in `CHANGELOG.md` if a user could notice the change
- [ ] `README.md` and `docs/README.pt-BR.md` changed together, if either changed
- [ ] English, no em dash, no emoji, straight quotes, no unmeasured claims

## If an agent drafted this

<!-- Which agent, and which person ran the fix behind any new gotcha. See AGENTS.md. Delete this section otherwise. -->
