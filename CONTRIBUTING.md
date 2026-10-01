# Contributing

Most rules here came from something that broke in a real file. New ones follow that bar.

## What is welcome

- **A new gotcha.** A Figma Plugin API behavior that surprised you, with the symptom, the cause and the fix. Add it to `skills/figma-canon/references/plugin-api-anomalies.md` or `field-notes.md`.
- **A correction.** Figma changes. If a rule here stopped being true, open an issue or a pull request with the version or date where you saw the new behavior.
- **A sharper check.** A gate step that would have caught a defect that reached a developer or a stakeholder.

## The bar for a gotcha

1. You hit it yourself. No rules copied from documentation, a forum or a model's guess.
2. It has a symptom someone can recognize ("the section renders black"), a cause and a fix that you ran.
3. It carries a month ("field note, 2026-10") so readers can judge how fresh it is.
4. A detector snippet when one exists. A rule an agent can check beats a rule an agent has to remember.

## Never include

- Client, employer, product or people names. Write "a client project".
- Figma file keys, file URLs or node ids from real files. Use `<fileKey>` and `123:456`.
- Tokens, cookies or absolute paths from your machine.
- Screenshots of work you do not own.

## Style

- English, plain and direct. Skills are operating instructions for an agent, not articles.
- No em dash, no emoji, straight quotes.
- Keep `SKILL.md` under 500 lines. Long detail goes in `references/`.
- A skill's `name` in the frontmatter matches its folder.

## Before you open a pull request

```bash
python3 -m pip install pyyaml
python3 -m unittest discover -s tests -v
```

The tests check frontmatter, links between skills and references, the lock, the hook, the installer and the style rules above.
