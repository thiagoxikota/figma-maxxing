# Works with

Which Figma connection each skill needs, and how far each combination has been tested. Status as of 2026-10-05, read from each skill's `SKILL.md`: its `compatibility` field and the server paths its body describes.

## The three setups

- **figma-console bridge.** [figma-console-mcp](https://github.com/southleft/figma-console-mcp) by Southleft (MIT) runs on your machine and reaches Figma Desktop through its Desktop Bridge plugin. Writes go through `figma_execute`. The skills were written and used on this path; the README records v1.40.8 as the last version checked.
- **Official Figma MCP server.** Figma's remote server, signed in with OAuth. Writes go through `use_figma`, which also runs Plugin API JavaScript; `figma-preflight` and `figma-click-flow` name a Full seat for writes there. Figma documents that runtime in its own figma-use skill in [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide), and use of the server falls under the [Figma Developer Terms](https://www.figma.com/legal/developer-terms/).
- **No server.** No MCP connection to Figma at all. The skills are plain Markdown, so a person or a chat AI can still read the rules and the checklists. [`llms.txt`](../llms.txt) is the digest written for that case.

## What the status words mean

- **Tested:** the author ran this skill on this setup in his own production work (Claude Code on macOS). The public edition is a rewrite of that private set and has not yet been run end to end on a second machine.
- **Untested:** the skill's `SKILL.md` describes a path for this setup, and nobody has validated it for this repository yet.
- **Not applicable:** the skill needs something this setup does not provide.
- **Demo run:** the skill ran once on a demo file built for a blind test, and not every step ran as written. The audit agent logged 19 skill steps that it adapted, skipped or did not need on that server, and the fix agent adapted 3 of the 8 preflight checks; they are listed below. 1.1.0 changed detector 8 of `figma-slop-check` after the run, and the new rule has not run since. See [Blind demo on the official Figma MCP](#blind-demo-on-the-official-figma-mcp).

## The matrix

| Skill | figma-console bridge | Official Figma MCP (`use_figma`) | No server |
|---|---|---|---|
| [`figma-canon`](../skills/figma-canon/SKILL.md) | Tested | Untested | Untested (reading only) |
| [`figma-preflight`](../skills/figma-preflight/SKILL.md) | Tested | Demo run | Not applicable |
| [`figma-orient`](../skills/figma-orient/SKILL.md) | Tested | Untested | Not applicable |
| [`figma-slop-check`](../skills/figma-slop-check/SKILL.md) | Tested | Demo run | Untested (manual checklist) |
| [`figma-handoff-gate`](../skills/figma-handoff-gate/SKILL.md) | Tested | Demo run | Untested (manual checklist) |
| [`figma-comment-fix-loop`](../skills/figma-comment-fix-loop/SKILL.md) | Tested | Untested | Not applicable |
| [`figma-click-flow`](../skills/figma-click-flow/SKILL.md) | Tested | Untested | Not applicable |
| [`figma-bridge-doctor`](../skills/figma-bridge-doctor/SKILL.md) | Tested (macOS) | Not applicable | Not applicable |

## Skill by skill

**`figma-canon`**
- Bridge: the references were written from work through `figma_execute`.
- Official server: the core write rules apply to `use_figma` as well, and some notes are about that server only (for example `figma.notify` and `setPluginData` are not supported there). Many field notes describe the bridge, so read each note's server before applying it.
- No server: knowledge only, with no scripts and no network, so it reads as a reference.

**`figma-preflight`**
- Bridge: path A of Check 0, proven by `figma_get_status`.
- Official server: path B of Check 0, proven by `whoami` plus `get_metadata` on the target. The skill marks path B as not validated by this repository and asks for small writes and a read-back of every change. It ran once, in the [blind demo](#blind-demo-on-the-official-figma-mcp).
- No server: Check 0 blocks every write when no MCP call confirms the connection, so there is nothing to gate. The file lock (`figma_lock.py`) is plain Python and works on either path.

**`figma-orient`**
- Bridge: the primary read path.
- Official server: a valid read path for small reads through `get_metadata`. Its budget depends on the plan: on a Starter plan one field case got about one call before the cap (see [the field note](../skills/figma-canon/references/field-notes.md#the-official-figma-mcp-server-has-a-hard-tool-call-cap-on-a-starter-plan)).
- No server: it needs a read path to map the file.

**`figma-slop-check`**
- Bridge: the checks are written for `figma_execute`, `figma_get_variables` and `figma_capture_screenshot`.
- Official server: `use_figma` also runs Plugin API JavaScript, and the skill states it was not validated there. It ran once, in the [blind demo](#blind-demo-on-the-official-figma-mcp).
- No server: the two lenses and the catalog can be applied by hand in Figma; that use has not been tested.

**`figma-handoff-gate`**
- Bridge: the detector snippets are written for `figma_execute`.
- Official server: same situation as `figma-slop-check`: Plugin API JavaScript, not validated there, and run once in the [blind demo](#blind-demo-on-the-official-figma-mcp).
- No server: the 17 checks can be walked by hand; that use has not been tested.

**`figma-comment-fix-loop`**
- Bridge: the path the loop was built on.
- Official server: fixes go through `use_figma` on path B of `figma-preflight`, and its screenshot tool replaces `figma_capture_screenshot`. Not validated by this repository.
- No server: reading the comments needs only a Figma personal access token and the REST API, but fixing them needs a write path. The canvas capture steps are macOS only on any setup.

**`figma-click-flow`**
- Bridge: the overlay recipe in `references/draw-overlay.js` runs through `figma_execute`.
- Official server: the same recipe is written to run in `use_figma`, with a guard for `figma.loadAllPagesAsync`, which Figma lists as not implemented there. Not validated by this repository.
- No server: it draws on the canvas.

**`figma-bridge-doctor`**
- Bridge: it repairs the figma-console connection. Its scripts are macOS only; on another OS they print a manual checklist and exit.
- Official server: that server does not go through the bridge, so there is nothing for this skill to repair.

## Other parts of the repository

- **The optional hook** (`hooks/figma-canon-precheck.py`) reads a script before it runs. The example in the README wires it to figma-console's `figma_execute` tools only. Its unit tests run in CI; it has not been tried as a hook on `use_figma`.
- **The file lock** (`skills/figma-preflight/scripts/figma_lock.py`) is standard-library Python that never talks to Figma. Its unit tests run in CI on Ubuntu and macOS.
- **The installer** (`install.py`) copies skill folders and does not depend on any server.

## Blind demo on the official Figma MCP

Run on 2026-10-05 by agents in Claude Code, connected to Figma's official server through a claude.ai Figma connector with a Full seat. Every Figma call went through that server (`whoami`, `get_metadata`, `get_variable_defs`, `search_design_system`, `use_figma`, `get_screenshot`). Figma Desktop stayed closed: no bridge, no REST, no figma-console. The file was a demo file made for this test, not client work. The README shows the [before and after](../README.md#before-and-after).

1. **Build (4 Figma MCP calls).** One agent drew a "Team members" list screen with 10 planted defects and wrote an answer key: a raw hex title, a hand-drawn icon next to library icons, a detached row, a gap and a radius off the scale, a clipped label, hype copy with emoji, default layer names, an add action with no remove, and missing list states.
2. **Blind audit (12 Figma MCP calls).** A second agent, who never saw the key, ran `figma-slop-check` and `figma-handoff-gate`. Its prompt named the skills and also told it which properties to inspect: bound variables, instances versus frames, spacing, radius, names and text bounds. Those cover 6 of the 10 planted defects. Slop check: FAIL, 16 findings (4 critical, 6 high, 4 medium, 2 low), rubric 0/10 from four auto-fails. Handoff gate: FAIL, 11 issues (9 blockers, 2 warnings). One call failed: an extra `devStatus` read the skills do not ask for, which the server answers as not supported.
3. **Judge.** A third agent scored the 27-item punch list against the key: 10 of 10 planted defects found, 0 partial, 0 missed. 13 items map to a planted defect. The other 14 were checked one by one against the key, the screenshots and pixel samples: 6 were already listed in the key as known gaps, and 8 were new, including a 4.32:1 text contrast failure the key missed. They describe 13 distinct problems, because both checks flagged the same rename. None of the 14 contradicted the evidence. The judge made no Figma call, so 2 of them (no annotation column, no prototype starting point) could not be checked against the file itself.
4. **Fix (13 Figma MCP calls).** A fourth agent ran `figma-preflight` on path B of Check 0 (`whoami` plus `get_metadata`). Preflight passed all 8 checks, three of them adapted to the tools this server has. It ran once, before the first of 4 writes, and the locked-ancestor post-write check was not run as a separate step. The agent then built a fixed copy of the screen next to the original, plus 5 state frames (loading, empty, remove swipe, remove confirm, removed), and read back every property it changed. It fixed 12 of the 16 slop findings. Two were partial (text inside the main components stayed unstyled, and the error, edge and permission states were not built). One lost to the task's required frame name, and one was not applied, because renaming the shared main component would also rename layers in the original. The original frame read back unchanged.
5. **Second audit (13 Figma MCP calls).** The same two gates on the fixed screen. Slop check: FAIL, 6 findings (1 critical: no focus state on Button or ListItem; 2 medium; 3 low). Of the 6 slop findings, 2 were left from the first list (unstyled text inside the main components, the root frame name), 2 were already on the screen but the first audit did not report them (no focus state, list rows named after their component), and 2 came from the fix itself (an icon stroke scaled to 1.67 by `rescale`, and a label shortened to "Pending"). Handoff gate: FAIL, 13 issues (8 blockers, 5 warnings), up from 11, mostly destinations and states the fix pass did not draw, plus the old frame still sitting on the delivered page.

**What did not run as written on the official server** (the audit agent's log has 20 entries: 19 skill steps and 1 extra read of its own, grouped here):

- No selection tool and no `figma_search_components`, `figma_get_design_system_summary` or `figma_get_component_details`. The agents listed the local components with read-only `use_figma` scans instead. `search_design_system` returned only published community libraries, not the components in this file.
- `get_screenshot` never renders above the node's own size, so the 2x proof of small elements (handoff check 17a) and the 0.4 overview could not come from it. The first audit used `node.screenshot()` at scale 3 to 6 inside a read-only `use_figma` call. The second audit stayed at 1x and reported that as a warning.
- `use_figma` has no timeout parameter, and its 20 KB output cap cut one full-screen read of 79 nodes. The agent fetched the missing tail in the next call.
- No bridge status (`figma_get_status`), so `figma-bridge-doctor` and path A of preflight Check 0 did not apply.
- `figma-orient` did not run. The agents did an equivalent read-only inventory (pages, components, variables, styles) and saved no map.
- The optional precheck hook targets `figma_execute`, so it did not run. The fix agent checked its scripts by hand for the patterns the hook blocks.
- The files the skills save in a project folder (run JSON, exception ledger) were not written, because the demo file has no project folder.

**What the run found in the skills themselves:** the detached-copy rule of `figma-slop-check` (detector 8 then, the `detached` check since 1.2.0) caught the detached row through its name match. Its second rule, `isDetachedFromComponent` on INSTANCE nodes, cannot fire on a detached copy, because Figma turns a detached instance into a FRAME. The auditor read `detachedInfo` on the frame instead. The check now reads it too; that rule was added after the run and has not run since.

**What it does not show:** the agent that planted the defects had read these skills, so the defects match what the checks cover. One screen, one demo file, one run. A hit rate on files nobody prepared is not measured.

## Report a result

Ran a skill on a setup marked Untested? [Open an issue](https://github.com/thiagoxikota/figma-maxxing/issues/new/choose) with the setup (server, plan and seat, agent, operating system), the skill and what happened. A clean run moves a cell from Untested to Tested; a failure becomes a gotcha.
