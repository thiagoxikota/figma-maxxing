<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.png">
  <img alt="Figma Maxxing. Agent skills for real Figma files, by Thiago Xikota." src="assets/banner-light.png">
</picture>

# Figma Maxxing

**Agent skills for real Figma files: inspect before writing, prove what changed, catch handoff gaps.**

[![Tests](https://github.com/thiagoxikota/figma-maxxing/actions/workflows/test.yml/badge.svg)](https://github.com/thiagoxikota/figma-maxxing/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-black.svg)](LICENSE)

**[Leia em português](docs/README.pt-BR.md)** · [Install](#install) · [What you need](#what-you-need) · [The skills](#the-skills) · [Gotchas](#a-few-of-the-gotchas)

## Paste this into your AI

You do not need to install anything to get a checklist for your work. Copy one of the blocks below into the AI you use (Claude, ChatGPT, Gemini, Cursor) and fill in the brackets.

```text
Read https://raw.githubusercontent.com/thiagoxikota/figma-maxxing/main/llms.txt
If you cannot open it, tell me and do not guess.
I am a designer. [I do / do not] have an AI agent connected to Figma.
My context: [Figma plan, whether my files have a design system, solo or team].
Pick at most five rules for my work. For each one, give me one check I can do
in Figma today. Then tell me whether any skill is worth installing for me.
```

Em português:

```text
Leia https://raw.githubusercontent.com/thiagoxikota/figma-maxxing/main/llms.txt
Se não conseguir abrir, me avise e não invente.
Sou designer. [Tenho / Não tenho] um agente de IA conectado ao Figma.
Meu contexto: [plano do Figma, se meus arquivos têm design system, se trabalho
sozinho ou em time]. Escolha no máximo cinco regras para o meu trabalho. Para
cada uma, me dê uma checagem que eu consiga fazer no Figma hoje. Depois, diga se
alguma skill vale a pena instalar no meu caso.
```

If a rule saves you an afternoon and you have a GitHub account, a star helps other designers find this.

## Why this exists

I'm Thiago Xikota, an AI Product Designer. This is the set of skills I run when an agent edits my Figma files: files that already have a design system, comments from the team and a developer waiting for the handoff.

A screen can look right while the file is wrong. The fill is a raw hex next to a variable of the same color. The icon was drawn by hand because nobody searched the library. The handoff shows how to add something and never how to remove it. You find out when you click a layer, or when the developer asks.

These skills tell the agent to inspect the file before it writes and to read back what it changed before it says done. Most of the rules came from something that broke in a real file.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/flow-dark.png">
  <img alt="How the skills fit together: 01 map the file with figma-orient, 02 check before writing with figma-preflight, 03 write with figma_execute, 04 check after writing with figma-slop-check, 05 hand off with figma-handoff-gate. figma-canon holds the rules every step reads; figma-comment-fix-loop runs steps 02 to 04 once per comment." src="assets/flow-light.png">
</picture>

## Install

```bash
npx skills add thiagoxikota/figma-maxxing
```

That installs the skills for your agent (Claude Code, Codex, Cursor and others supported by the [skills CLI](https://skills.sh)). The CLI is a third-party tool that sends anonymous install counts; `DISABLE_TELEMETRY=1` turns that off. It does not connect your agent to Figma: that is [the next step](#what-you-need).

<details>
<summary>Other ways to install</summary>

**Claude Code plugin**

```text
/plugin marketplace add thiagoxikota/figma-maxxing
/plugin install figma-maxxing@figma-maxxing-skills
```

Skills are then available as `/figma-maxxing:figma-preflight` and so on. The plugin contains skills only. It installs no hooks and no MCP servers.

**Manual copy**

```bash
git clone https://github.com/thiagoxikota/figma-maxxing.git
cd figma-maxxing
python3 install.py --dry-run                      # see what would be copied
python3 install.py --scope user                   # Claude Code, all projects: ~/.claude/skills
python3 install.py --target agents --scope user   # Codex and others: ~/.agents/skills
```

The installer copies folders and nothing else. It refuses to overwrite a skill that already exists.

</details>

## Start with one job

Once the setup in [What you need](#what-you-need) is in place, say the job in your own words. Without that setup, use the text in [Paste this into your AI](#paste-this-into-your-ai).

| The job | Say something like | What runs |
|---|---|---|
| Apply the feedback people left in the file | "Fix what they commented on this page" | `figma-comment-fix-loop` reads the open comments, fixes each one on the frame where it was pinned and hands you the evidence |
| Check a screen before you call it done | "Is this frame ready?" | `figma-slop-check` looks for machine-made tells and precision defects, then `figma-handoff-gate` checks what a developer needs |
| Build or edit without breaking the file | "Add an empty state to this screen" | `figma-preflight` confirms the target, the tokens and the existing components before a single node is written |
| Understand a file you just opened | Paste the Figma URL | `figma-orient` maps pages, components and variables and saves the map for next time |

## What goes wrong, and what catches it

**1. It looks right until you click a layer.**
Left alone, an agent hardcodes values and draws from scratch what already exists in the library. Over a few sessions, one feature can pile up dozens of hand-drawn icons, each write innocent on its own. `figma-preflight` makes the agent look for the real component and the real icon before it writes anything.

**2. The agent said it worked. Nothing changed.**
A node under a locked parent refuses a write in silence. In one large batch of variable bindings, a handful never happened, and the check that compared colors still came back green, because nothing had changed at all. The rule that came out of it: after a write, read back the property you changed, never a proxy for it.

**3. The Plugin API does not behave the way you would guess.**
`figma-canon` carries the list of things that surprised me, each with the symptom, the cause and the fix. [A few of them](#a-few-of-the-gotchas) are below.

**4. You become the middleman between every comment and every fix.**
`figma-comment-fix-loop` pulls the open comments, works through each one on the frame where it was pinned and returns a list that pairs every comment with its change and a screenshot, or with the reason it was left open.

**5. The handoff draws "add" and forgets "remove".**
A developer builds what is drawn and guesses the rest. `figma-handoff-gate` lists every interactive element and asks where it leads. If one direction exists, the way back has to exist too.

**6. The bridge dropped again.**
`figma-bridge-doctor` handles the connection between your agent and Figma Desktop. It tries the smallest fix first and asks before it ever quits Figma.

## The skills

| Skill | When it runs | What it does |
|---|---|---|
| [`figma-canon`](skills/figma-canon/SKILL.md) | Any time Figma comes up | The knowledge base: Plugin API rules, gotchas, auto layout, naming, state coverage, handoff format. Loaded piece by piece, only what the task needs |
| [`figma-preflight`](skills/figma-preflight/SKILL.md) | Before every write | Read-only gate. Approves the write or returns a fix list. Also audits flows for orphan screens and buttons that lead nowhere |
| [`figma-orient`](skills/figma-orient/SKILL.md) | First contact with a file | Builds the map of the file and saves it in your project |
| [`figma-slop-check`](skills/figma-slop-check/SKILL.md) | After a write | Catches design that looks machine made and design that is imprecise |
| [`figma-handoff-gate`](skills/figma-handoff-gate/SKILL.md) | Before a handoff | Action completeness, annotation quality, proof at the right scale, no trace of the process |
| [`figma-comment-fix-loop`](skills/figma-comment-fix-loop/SKILL.md) | When feedback arrives | Comments to fixes to evidence |
| [`figma-click-flow`](skills/figma-click-flow/SKILL.md) | "Turn this into a flow" | Draws flow arrows from tappable elements to their destination screens |
| [`figma-bridge-doctor`](skills/figma-bridge-doctor/SKILL.md) | Connection problems | Diagnoses and repairs the Desktop Bridge connection (macOS) |

## A few of the gotchas

From [`plugin-api-anomalies.md`](skills/figma-canon/references/plugin-api-anomalies.md) and [`field-notes.md`](skills/figma-canon/references/field-notes.md):

- [A section bound to a color variable renders the color you passed, not the variable.](skills/figma-canon/references/field-notes.md#a-section-fill-bound-to-a-variable-renders-the-base-color-you-passed) Resolve the variable first, then bind.
- [Writes under a locked parent fail in silence.](skills/figma-canon/references/field-notes.md#writes-to-descendants-of-a-locked-node-fail-silently) The node says `locked: false`, the editor refuses anyway, and nothing throws.
- [`instance.resize()` leaves the icon at full size inside a small box.](skills/figma-canon/references/plugin-api-anomalies.md#instanceresize-does-not-scale-the-children-use-rescale) Use `rescale()`.
- [Replacing a node inside a main component wipes the override on every instance.](skills/figma-canon/references/plugin-api-anomalies.md#replacing-a-node-inside-a-master-wipes-the-override-on-every-instance) Capture the overrides before the swap and apply them back after.
- [`clone()` of a section child lands on the page, not in the section.](skills/figma-canon/references/plugin-api-anomalies.md#clone-of-a-section-child-lands-at-page-level-not-in-the-section) The screenshot looks right. The layer tree shows it on the page.
- [The REST export can lag minutes behind your plugin edits.](skills/figma-canon/references/plugin-api-anomalies.md#rest-v1images-renders-stale-cloud-state-after-plugin-edits) Check the exported PNG itself, not the canvas.
- [`setTimeout` never fires in the plugin sandbox.](skills/figma-canon/references/field-notes.md#settimeout-never-fires-in-the-plugin-sandbox) A timeout guard built on it guards nothing.
- [Changing `action` on a prototype reaction does nothing.](skills/figma-canon/references/field-notes.md#re-pointing-a-reaction-write-actions-not-action) Figma reads `actions`, and the call still returns success.
- [`getNodeByIdAsync` can hang instead of throwing](skills/figma-canon/references/plugin-api-anomalies.md#getnodebyidasync-hangs-does-not-throw-in-large-multi-page-files) in a large file with many pages.

The two files hold more than 80 notes like these, on the Plugin API, the bridge and running several agents on one file. Figma and other people keep lists of their own. These are the ones I learned in production, mostly through the figma-console bridge.

## What you need

- **Figma Desktop** for macOS or Windows. The browser version is not enough: the bridge is a development plugin, and Figma only imports those in the desktop app.
- **[figma-console-mcp](https://github.com/southleft/figma-console-mcp)** by Southleft (MIT). It runs on your machine and talks to Figma through its Desktop Bridge plugin. These skills are written for its `figma_execute` tool. Last checked against v1.40.8.
- **Node.js 18 or newer.**
- **An MCP client that loads Agent Skills.** I use Claude Code.
- **A Figma personal access token** for the comment workflow, with File content (read), File versions (read), Variables (read) and Comments (read and write). It is used for REST calls such as reading comments. Canvas work goes through the bridge.

For Claude Code, setup looks like this. For other clients, follow the [upstream guide](https://github.com/southleft/figma-console-mcp#readme).

```bash
claude mcp add figma-console -s user -e FIGMA_ACCESS_TOKEN=figd_YOUR_TOKEN_HERE -e ENABLE_MCP_APPS=true -- npx -y figma-console-mcp@latest
```

1. Restart Claude Code so it starts the server. The first start creates the plugin manifest.
2. In Figma Desktop, open a file and go to Plugins, Development, Import plugin from manifest. Pick `~/.figma-console-mcp/plugin/manifest.json` (`~` is your home folder).
3. Run the Figma Desktop Bridge plugin in the file you want to work on.
4. Ask your agent: "check the Figma connection". It should call `figma_get_status`.

That command writes the token in plain text to your agent's config, and it may stay in your shell history. Treat both as secrets and never commit the config. When figma-console-mcp updates, its release notes sometimes ask you to import the manifest again.

**Using only the official Figma MCP server?** I have not validated these skills there: I wrote and used them on the figma-console bridge. Its `use_figma` tool also runs Plugin API code, so `figma-canon`, `figma-slop-check` and `figma-handoff-gate` still work as rules and checklists, and `figma-preflight` accepts that server as a write path.

**What it costs.** This repository and figma-console-mcp are free and open source. Your agent and your Figma plan are not included.

## The optional hook

`hooks/figma-canon-precheck.py` reads the script your agent is about to run in Figma and warns about patterns that are known to fail, before the call reaches Figma. Nothing in this repository installs it. To turn it on in Claude Code, add this to your `settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__figma-console__figma_execute(_across_files)?",
        "hooks": [
          { "type": "command", "command": "python3 /path/to/figma-maxxing/hooks/figma-canon-precheck.py", "timeout": 10 }
        ]
      }
    ]
  }
}
```

By default it only adds warnings. Set `FIGMA_PRECHECK_MODE=block` to make it refuse the patterns it marks as `BLOCK` (they fail in a Design file).

## Good for, not for

| Good for | Not for |
|---|---|
| Files that already have components, variables and a team | Generating a full product from one sentence |
| Feedback rounds, cleanup, state coverage, handoff | Replacing the designer's judgment about what to build |
| Agents that write through the figma-console bridge | A setup with no desktop app (the bridge needs Figma Desktop) |
| macOS for the recovery scripts | Windows or Linux automation of the bridge (the skills themselves are plain Markdown) |

## How far this has been tested

I built these skills in Claude Code on macOS with figma-console-mcp, on my own work. This public edition is a rewrite of that set: translated to English, generalized, with every client name and identifying detail removed. The lock, the hook and the installer have unit tests that run on every push. The public edition has not yet been run end to end on a second machine. If something still depends on my setup, [open an issue](https://github.com/thiagoxikota/figma-maxxing/issues) with your environment and the exact error.

## Contributing

A gotcha you hit yourself, with symptom, cause and fix, is the best contribution. See [CONTRIBUTING.md](CONTRIBUTING.md), the [code of conduct](CODE_OF_CONDUCT.md) and the [changelog](CHANGELOG.md). Security notes are in [SECURITY.md](SECURITY.md).

## Credits

Built on [figma-console-mcp](https://github.com/southleft/figma-console-mcp) by Southleft. The skill format is the open [Agent Skills](https://agentskills.io) standard.

Not affiliated with Figma. Figma is a trademark of Figma, Inc.

## License

MIT. See [LICENSE](LICENSE).
