---
name: figma-bridge-doctor
description: >-
  Single owner of the connection between Figma Desktop and the figma-console MCP Desktop Bridge
  plugin, alias-agnostic, across every project. Use on any intent to open, activate, restart or
  check Figma or the bridge, and before any figma-console tool call. Trigger phrases: "open the
  Figma file", "is the bridge connected?", "restart the bridge",
  "abre o figma", "liga a bridge". Probes state, takes the minimum action, verifies with
  figma_get_status and escalates at most 4 times. Always Figma Desktop, never the browser.
  The automation is macOS only.
license: MIT
metadata:
  author: Thiago Xikota
  version: "1.0.0"
---

# figma-bridge-doctor

Domain owner for everything Figma Desktop + Bridge. When the user mentions opening a Figma file, activating the bridge, or any bridge issue, this skill picks the right action and verifies it worked.

Script paths below are relative to this skill's directory (the folder that holds this file). The scripts live in this skill's `scripts/` directory. Resolve the path before running, wherever the skill is installed.

Tool names are written as base names (`figma_get_status`). Your client may add a prefix: in Claude Code, with the server registered under the name `figma-console`, they appear as `mcp__figma-console__figma_get_status`. If you registered it under another name, use that name wherever this skill writes `figma-console`.

## Platform and permissions

- **The automation is macOS only.** The scripts use `open`, `osascript`, `launchctl`, `lsof`, `pgrep` and `ps`. On any other OS each macOS-only script prints a short manual checklist and exits 1: follow the "Manual checklist" section with the user instead.
- **Accessibility permission.** The plugin is launched by a menu click through System Events. The app that runs the script (Terminal, iTerm, the IDE or whatever hosts the agent) needs the Accessibility permission: System Settings > Privacy & Security > Accessibility. Without it the click fails and the script prints `osascript click failed`. Granting it is a user action.
- **English Figma UI.** The click targets the menu items by name: `Plugins` > `Development` > `Figma Desktop Bridge`. If Figma runs in another language the names do not match and the click fails. Ask the user to switch Figma to English or to run the plugin by hand.
- **Prerequisites.** Figma Desktop, the figma-console MCP server (`figma-console-mcp`, by Southleft) registered in the agent, and its Desktop Bridge plugin imported once from `~/.figma-console-mcp/plugin/manifest.json`.

## State and environment

State files live under the state dir, `${FIGMA_MAXXING_STATE_DIR:-$HOME/.config/figma-maxxing}`, written `<state-dir>` below. The scripts create it on first run.

| File | What it holds |
|---|---|
| `<state-dir>/figma-files.json` | Alias registry. Starts as an empty JSON object (`{}`); entries live under the `files` key. The user grows it, nothing ships in it. |
| `<state-dir>/figma-bridge-last-url` | One line: the last URL opened. Starts empty. |
| `<state-dir>/figma-reconnect-signal` | Exists only while a plugin trigger is pending for the optional watchdog. |
| `<state-dir>/mcp-direct-<HTTP_PORT>.token` | Exists only while the `scripts/mcp-direct/` daemon runs: its bearer token, mode 0600. |

| Variable | Used by | Effect |
|---|---|---|
| `FIGMA_MAXXING_STATE_DIR` | all scripts | Moves the state dir. |
| `FIGMA_ACCESS_TOKEN` | the MCP server | Figma personal access token for REST backed tools. The same variable figma-console-mcp reads. Never print it, never write it to a file. |
| `FIGMA_FULL_RESET=1` | `figma-bridge-reset.sh` | Quit and relaunch Figma. Without it the script never quits Figma. Set it only after the user said yes to a restart (Step 5). |
| `FIGMA_NO_PLUGIN=1` | `figma-open.sh`, `figma-bridge-reset.sh` | Skip the plugin trigger. |
| `FIGMA_KILL_OTHER_SESSIONS=1` | `figma-bridge-reset.sh` | Also kill the MCP servers of other sessions. Only when solo. |
| `FIGMA_AGENT_PROCESS` | `figma-status.sh`, `figma-bridge-reset.sh` | Process name of the agent that spawns the MCP servers (default `claude`, the Claude Code process). Used to tell this session's server from the others. |
| `FIGMA_BRIDGE_DEFAULT_URL` | `figma-bridge-reset.sh` | Target when no argument is given (wins over the cached URL). |
| `WS_PORT`, `HTTP_PORT`, `FIGMA_MCP_ENTRY` | `scripts/mcp-direct/` | Ports and server entry of the direct client (defaults 9231 and 8791). |

## The mental model (one paragraph)

The figma-console MCP server needs the Bridge plugin running inside Figma Desktop to do writes. Bridge = a WebSocket connection between a `figma-console-mcp` node process (port 9223-9232) and the in-Figma plugin. It breaks for predictable reasons: plugin not yet launched after Figma opens, stale MCP server on the wrong port, Figma in a 0-window state, Accessibility permission missing on the terminal. Recovery is a small set of mechanical steps; this skill executes them and verifies.

The field notes below disagree on how the plugin attaches when several servers are alive. Notes from 2026-05 and 2026-06 saw it serve ONE server at a time (first or lowest port, last trigger wins). Notes from 2026-08 and 2026-09 saw one WebSocket per live server in the range. The two were never reconciled, so never assume which session the plugin is serving: read `figma_get_status`.

## The smart dispatch (state-aware, minimal-action)

The user prompts in natural language. They do not type commands or remember flags. You figure out intent + current state + the minimum action that gets them what they need. Pick the CHEAPEST action that achieves the goal.

### Step 1: probe current state FIRST (always)

Before any action, snapshot state:

```bash
bash scripts/figma-status.sh   # local: my MCP port, other sessions, cached URL
```

Then call `figma_get_status` for the bridge view: is the WebSocket up, which file is paired, what port.

### Step 2: extract target file from user input

The user might give:
- **An alias** ("myapp", "ds", "ds-docs"): look it up in `<state-dir>/figma-files.json`.
- **A raw URL** (`https://www.figma.com/design/<fileKey>/...` or `/board/<fileKey>/`): extract the key, look it up in the registry by key.
- **A project name not in the registry** ("open the new-project file"): ask once for the URL.
- **No file mention** ("turn the bridge on", "is it connected?"): use the cached `<state-dir>/figma-bridge-last-url`, or surface "which file?" if the cache is empty.
- **The current paired file** (the user is asking about what is already loaded): use what `figma_get_status` returned.

### Step 3: URL paste auto-register (the project-agnostic part)

If the user pastes a `figma.com/(design|board|file)/<fileKey>` URL and the key is NOT in `<state-dir>/figma-files.json`:

1. Ask in one line: "What do you want to call this one? (for example: myapp, ds, new-app) Or press enter and I will derive it from the file name."
2. Call `bash scripts/figma-add.sh "<url>" [optional-alias] [optional-label]`. The script extracts the key, derives the alias from the URL filename if none is given, and sets validated=null. Idempotent.
3. Proceed with the open via `figma-open.sh <alias>`.

If the user gives the URL WITH a clear name, like "open this one from the Acme project: https://...", you can pass the alias as arg 2: `bash scripts/figma-add.sh "<url>" acme`. Do not ask the question if the project name is unambiguous in the message.

**Never hardcode a project alias in your dispatch logic.** The registry is a JSON file the user grows. Every project is equal. `<state-dir>/figma-files.json` is the source of truth at any moment: re-read it each turn.

### Step 4: pick the MINIMUM action

Based on state + target:

| State | Target file | Action |
|---|---|---|
| Bridge UP, paired with target | (same) | **No-op.** Report "PASS already on <file>, port <N>". Done. |
| Bridge UP, paired with a different file | switch to <X> | `figma_navigate` if Figma has a tab for <X>, else `figma-open.sh <X>` to open + navigate |
| Bridge DOWN, Figma running with a file open | <X> | osascript menu click (Step T below) if last-opened was <X>, else `figma-open.sh <X>` |
| Bridge DOWN, Figma running but no file | <X> | `figma-open.sh <X>` |
| Bridge DOWN, Figma not running | <X> | `figma-open.sh <X>` (it opens Figma + waits + clicks) |
| Bridge UP but acting flaky / stale data | <X> | `figma_reconnect`, then verify; if still bad, `bash scripts/figma-bridge-reset.sh <X>` (gentle by default) |

As of figma-console-mcp v1.40.8, `figma_reconnect` is informational: it does not repair a dead connection, and `figma_get_status` is the only proof of a live connection. The last row still calls it first; `figma_get_status` decides whether to move on to the reset.

### Step 5: verify + escalate (mandatory after any action except no-op)

```
sleep 3
figma_get_status probe:true

connected to target file -> DONE, report briefly: "bridge on <file>, port <N>, latency <ms>"
disconnected -> escalate:
  attempt 1: figma-bridge-reset.sh <alias> (gentle by default, Figma stays open)
  attempt 2: consent-gated full reset: ask first, then FIGMA_FULL_RESET=1
             figma-bridge-reset.sh <alias> (quit + relaunch); on no, go to attempt 3
  attempt 3: consent-gated tight-loop atomic re-attach (multi-session race fix, below)
  attempt 4: manual checklist to user, STOP
```

**Never quit Figma Desktop without asking.** The user may be working in it right now. `figma-bridge-reset.sh` never quits Figma unless `FIGMA_FULL_RESET=1` is set. Any step that quits Figma, today only the full reset of attempt 2, first asks one short question and waits for an explicit yes:

> "The bridge is still down. Can I quit and reopen Figma Desktop? Your open tabs come back after the relaunch."

Anything but an explicit yes counts as no: skip to attempt 3. Ask once per recovery, not before every retry.

If a reset prints `WARN: no MCP listener on 9223-9232 after 15s` and `Skipping click`, it stopped before the plugin click on purpose because no server was listening. Typically it just killed this session's server (the only one when you work solo), and that server only respawns on the next MCP call, which cannot happen while the script runs. Do what the script says: call `figma_get_status` once (that respawns the server), run Step T, then verify. This completes the same attempt; it is not a new one.

Cap at 4 escalations. Nothing enforces this for you: count the attempts and stop after the fourth. Do NOT loop further.

### Deep recovery (rare): references/deep-recovery.md

Tight-loop atomic re-attach (multi-session race), respawn-low (win the attach without killing other sessions) and orphan-MCP port exhaustion live in [references/deep-recovery.md](references/deep-recovery.md). Load it at escalation attempt 3 (attempt 1 failed and attempt 2 failed or was declined, with other Claude Code sessions alive), or when the ports are exhausted after a long session.

### Critical preconditions

- **Menu click only launches the plugin when a file is open in Figma.** Empty Figma + click = no-op. Always open first.
- **Multi-session safety**: `figma-bridge-reset.sh` defaults to killing ONLY this session's MCP server. Other Claude Code sessions on 9223-9232 are SKIPPED by a process-tree check: a server is this session's when its nearest ancestor named `claude` (or `$FIGMA_AGENT_PROCESS`) is the same process as the script's. Comparing whole ancestor chains is not enough, because every session started from the same terminal app shares the terminal's ancestors. If the script finds no such ancestor it kills nothing and says so. `figma-status.sh` uses the same check for `my_mcp_port`, and splits every other listener in two: `orphans=` (no live owner: the server and its own npx wrapper lead straight to launchd, so the session that started it is gone) and `other_sessions=` (anything else, such as another agent session). Set `FIGMA_KILL_OTHER_SESSIONS=1` to kill all of them (only when solo).
- **The full reset quits Figma.** It is a graceful quit that preserves the open tabs, then a relaunch. The script skips the quit by default and runs it only with `FIGMA_FULL_RESET=1`, which needs the user's yes first (Step 5). Never `killall Figma`: that leaves Figma in a 0-window state where no plugin can attach.
- **First sync each session**: when the user first mentions Figma in a session, run `figma-status.sh` + `figma_get_status` BEFORE asking them anything. Often you can answer "is it connected?" without any further input.

## Plugin version: THREE layers, and the banner does not say the direction

Field note, 2026-09. The plugin panel shows the status `Connected`, the line `Connected to N AI apps`, a Pause button, and sometimes a `Plugin update available` notice asking you to re-import through `Plugins > Development > Import from manifest`. Before obeying that notice, understand that there are THREE distinct versions, and they diverge on their own:

| Layer | Where it lives | How to read it |
|---|---|---|
| Package | `$(npm config get cache)/_npx/<hash>/node_modules/figma-console-mcp/package.json` | `plugin_pkg_newest` in `figma-status.sh` |
| Plugin bundle | `figma-desktop-bridge/code.js` INSIDE the package, and the copy in `~/.figma-console-mcp/plugin/` | `plugin_bundle_newest` and `plugin_disk_version` |
| Plugin RUNNING | process inside Figma, per open file | `figma_get_status` -> `connectedFiles[].pluginVersion` + `pluginUpdateAvailable` |

`N AI apps` counts **live servers in the 9223-9232 range**, not files: the plugin opens one WebSocket per server. 6 open Claude Code sessions = "6 AI apps". It is not a sign of a problem.

**The trap (paid for in 2026-09, a self-inflicted regression):** every server, on boot, rewrites `~/.figma-console-mcp/plugin/` with ITS OWN bundle. A server from an old npx cache **downgrades the plugin on disk**. It happened because an earlier version of the fallback's `daemon.mjs` resolved the cache with `ls -t` (newest mtime), and the cache with the newest mtime was **1.35.0**, not 1.40.0. The 1.35.0 server overwrote the disk, and the next plugin trigger loaded 1.35.0 inside Figma. The banner appeared saying only "update available", without saying that the correct move was BACKWARDS. Following the banner and re-importing would have installed the downgrade for good.

**Rules that stay:**

1. **Never re-import because of the banner without measuring first.** Run `figma-status.sh` and read `plugin_drift`. `true` = the disk is NOT the newest bundle; fix the DISK first.
2. **Updating the plugin is almost never "Import from manifest".** Figma reads `code.js` from disk on every Run. A correct disk + re-running the plugin (Step T) already solves it. Import from manifest only when `manifest.json` really changed (compare its md5 with the package's) or when the entry disappeared from the `Plugins > Development` menu.
3. **Fixing the disk** = copy `code.js`, `ui.html`, `manifest.json` from the package with the HIGHEST VERSION (not the one with the newest mtime) to `~/.figma-console-mcp/plugin/`, and write the package version into `.version`. Back up the dir first (`plugin.bak-<version>-<date>`).
4. **`pluginVersion` is per FILE.** After re-running, one file can be on 1.39.0 and another still on 1.35.0: each one only switches when the plugin runs in that file. Check the whole `connectedFiles[]`, not only the active one.
5. **An old npx cache is dangerous garbage**: move it to `<hash>.stale-<version>` as soon as you identify it. While it exists, any resolution by mtime can resurrect the downgrade.

Full fix recipe:

```bash
bash scripts/figma-status.sh | grep plugin_        # measure: drift? which version?
# if plugin_drift=true:
NPX="$(npm config get cache)/_npx"
PKG=$(for d in "$NPX"/*/node_modules/figma-console-mcp; do \
  [ -f "$d/package.json" ] && echo "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" "$d/package.json") $d"; \
done | sort -V | tail -1 | cut -d' ' -f2-)
cp -R ~/.figma-console-mcp/plugin ~/.figma-console-mcp/plugin.bak-$(date +%Y%m%d-%H%M%S)
cp "$PKG"/figma-desktop-bridge/{code.js,ui.html,manifest.json} ~/.figma-console-mcp/plugin/
python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'],end='')" "$PKG/package.json" > ~/.figma-console-mcp/plugin/.version
# then Step T (re-run the plugin) and check pluginVersion in figma_get_status
```

## Step T: TRIGGER-only (when Figma is already open)

```bash
osascript <<'OSA'
tell application "Figma" to activate
delay 0.5
tell application "System Events"
  tell process "Figma"
    set frontmost to true
    delay 0.5
    click menu item "Figma Desktop Bridge" of menu 1 of menu item "Development" of menu 1 of menu bar item "Plugins" of menu bar 1
  end tell
end tell
OSA
sleep 4
```

Idempotent. Validated 2026-05-23. macOS only, needs the Accessibility permission, assumes the English Figma UI.

## After reconnecting in a WRITE session: rival-write audit (mandatory)

Field note, 2026-06: during the disconnect window the plugin may have served ANOTHER Claude Code session (even one running the same prompt), which wrote into the file. After reconnecting in the middle of write work:

1. List `page.children` and compare with your inventory from before the drop.
2. Look for nodes with names from YOUR plan that you did not create (ids outside your sequence = rival write).
3. Move rival debris into a container named `_archive` (create it if the file has none) and prefix each moved node's name with `[parallel session]`. Never delete it.
4. Tell the user that another live Claude Code window exists and can steal the bridge again (field note, 2026-06: the plugin served one server at a time and whoever re-triggered last won; see "The mental model" for the later, conflicting notes).
5. Do not rely on the file lock (`figma_lock.py`, in the `figma-preflight` skill's `scripts/` directory) to detect this: two sessions that claim with the same agent name and the same task id are indistinguishable to the lock.

**Do not adopt a rival write into a deliverable, even if it turned out well** (validated 2026-06-15: a parallel session dropped a clean cutout image onto a slide; it was adopted because it fit the theme, against step 3). Default = archive + flag. If you adopt it anyway: (a) verify the node at FULL RES (crop + read the image, not a downscaled 0.8x preview screenshot), (b) confirm no more rival writes are coming in, (c) tell the user explicitly that the element came from another session. Silently adopting it into a deck that goes to a stakeholder is a provenance hole.

**If the rival write RE-INJECTS after you archive it, it is a live loop, not a one-shot** (validated 2026-06-15: one emblem was archived and the parallel session cloned another onto the same slide seconds later). You cannot win by cleaning node by node against a live writer. Do this: (1) clean ONCE (archive or remove the duplicate, the original already preserved), (2) confirm it is clean via `figma_execute` (children with no foreign node), (3) export IMMEDIATELY: `download_assets` (official Figma MCP server) renders the current state, and the **count of `rawImages` is a detector of a rival image node**: a slide with 1 legitimate image returns 1 rawImage; if a rival image node had entered, it would return 2. (4) escalate to the user to CLOSE the other Claude Code window: without that, the live Figma file keeps being polluted even with a clean export.

## The active file DRIFTS on its own in the middle of a write

Field note, 2026-08. With two files paired at the same time, the active target changes without you asking (the designer clicks another tab, another Claude Code session re-triggers the plugin). Symptoms, in the order they appear:

1. `figma_execute` dies with `in setCurrentPageAsync: Expected node, got undefined`, because `figma.root.children.find(p => p.name === '<your page>')` returned `undefined`: you are in the wrong file, the page was not deleted. **Always check `fileContext.fileName` in the return value.**
2. `figma_take_screenshot` falls to REST and returns `403 Invalid token`, which looks like an expired personal access token (see "Failure surface to track" below) but here it is only a consequence of the wrong target.

**Fix in two steps, in this order:**

- **Write:** pass an explicit `fileKey` to `figma_execute`. It runs against that file without touching the active target, so it works even with the bridge pointing somewhere else.
- **Visual read:** `figma_navigate({url, lock: true})`. The `lock` PINS the target; without it the drift comes back. After pinning, `figma_capture_screenshot` (plugin, exportAsync) works with no token at all.

**Before any conclusion about a leak:** sweep the intruder file for nodes with the names from YOUR plan before assuming damage. In the incident of 2026-08-17 the write died at `setCurrentPageAsync`, which comes BEFORE any `create*`, and nothing leaked into the other file, confirmed by a sweep of its 8 pages, not by assumption.

## Manual checklist (escalation step 4 only)

Surface this when auto-recovery has exhausted its retries:

```
Bridge still down after 4 attempts. Manual steps:

1. Figma DESKTOP (not browser) running with a file open
2. Plugins > Development > "Figma Desktop Bridge" (the one WITHOUT the warning icon) > Run
   - If not listed, import from ~/.figma-console-mcp/plugin/manifest.json
3. Leave the plugin window OPEN
4. Reply "bridge is up" and I will re-probe.
```

After the user confirms, re-probe ONCE. Do not loop further.

## Proactive trigger (start-of-session)

When a session opens and the first user message implies Figma work (mentions Figma, a Figma URL, a known alias, or "open" + a project name), proactively run PROBE (Step 1) before the user has to.

If disconnected, run `figma-open.sh` with the most recent cached URL (`<state-dir>/figma-bridge-last-url`) or ask which file.

## Adding a new project alias

When the user mentions a new project (e.g. "open the Figma file for new-project") and the alias is not in `<state-dir>/figma-files.json`:

1. Ask for the Figma URL in one line.
2. Add the entry under `files` with `"validated": null` (`figma-add.sh` does exactly this):
```json
"new-project": {
  "url": "https://www.figma.com/design/<fileKey>/<name>",
  "key": "<fileKey>",
  "label": "New Project - <short desc>",
  "type": "design",
  "validated": null
}
```
3. Run `figma-open.sh <alias>`.
4. Confirm with the user that the right file opened. If yes, set `"validated"` to today's date.

## Failure surface to track (cheap diagnostics first)

Before running any recovery script, if `figma_get_status` returns disconnected, glance at:

- `pgrep -x Figma`: is Figma even running?
- `claude mcp list | grep figma-console` (Claude Code, server registered as `figma-console`): is the MCP server installed?
- `lsof -t -i tcp:9223-9232 -s TCP:LISTEN`: which servers hold which ports?

If `pgrep` shows zero Figma, the recovery is just OPEN (not RESTART). If the MCP server is not listed, surface the install instructions (https://github.com/southleft/figma-console-mcp) and stop. If multiple servers hold ports across the range, read `figma-status.sh`: pids under `orphans=` are leftovers with no live owner (deep recovery clears them), pids under `other_sessions=` are the multi-session race: close the other Claude Code windows.

**Not every Figma failure is the bridge: REST token vs OAuth (validated 2026-06-14).** `figma_take_screenshot` (figma-console) renders via the Figma REST API, which uses the MCP server's `FIGMA_ACCESS_TOKEN` (the personal access token). When that token expires it returns `403 "Invalid token"` / `403 "Token expired"`: this is **NOT a bridge failure**, do NOT run resets. The WebSocket bridge (writes and `figma_capture_screenshot`) and the **official Figma MCP server (remote, OAuth, separate auth)** keep working. To screenshot or export anyway, use the official server: `download_assets(fileKey,nodeId,defaultScale:2)` or `get_screenshot(fileKey,nodeId)` return a short-lived `figma.com/api/mcp/asset/...` URL, then `curl -o file.png "<url>"` (no token, no base64). `whoami` confirms the OAuth identity even with the token dead. Refreshing the token (Figma > Settings > Security) is the long-term fix but is a USER action.

As of figma-console-mcp v1.40.8, `figma_take_screenshot` uses the Desktop Bridge plugin when it is connected and falls back to the REST API, so the 403 shows up when the call goes through REST (bridge down, or pointing at another file). `figma_capture_screenshot` always uses the plugin runtime and needs the bridge.

**`figma_get_comments` is also gated by the REST token**: same 403 when the token expires (seen 2026-06-18). Worse: **comments are NOT in the Figma Plugin API at all**, so the bridge and `figma_execute` can never read them. To read comments with a dead token: the official Figma MCP server (OAuth) if it is connected, else ask the user to paste the comments or refresh the token. Do not promise to read a stakeholder's comments without checking the token first.

## The TWO bridge layers (do not conflate them)

This skill mostly fixes layer 2. Layer 1 failures look identical from the user's chair ("the bridge will not connect") but have a different fix and **cannot be fixed mid-session by this skill**, because this skill works THROUGH the figma-console tools, which do not exist if layer 1 failed.

1. **MCP server registration in the agent session** (boot-time). Claude Code handshakes each MCP server ONCE at session start and freezes the tool list. If `figma-console` crashed at boot, its tools are absent for the whole session: in Claude Code, with the server registered as `figma-console`, `ToolSearch "select:mcp__figma-console__figma_get_status"` returns nothing, and there is **no in-session tool** to re-register them. Re-registration requires the USER to run `/mcp` and reconnect, or to restart Claude Code.
2. **Bridge plugin + WebSocket inside Figma Desktop** (runtime). This is what `figma_get_status`, `figma-open.sh` and the osascript menu click own. The agent CAN fix this layer itself.

**Diagnostic when the figma-console tools are entirely missing (not just disconnected):**

- `claude mcp list | grep figma-console` (server registered as `figma-console`) shows `Failed to connect`: layer 1 boot crash.
- Most common cause seen: **corrupted npx install cache**. The server crashes on spawn with `npm error ENOTEMPTY: directory not empty, rename '.../_npx/<hash>/node_modules/...'`.
- Reproduce + read the real error, with `FIGMA_ACCESS_TOKEN` already in the environment: `cd /tmp && (echo "" | npx -y figma-console-mcp@latest 2>&1 & P=$!; sleep 15; kill $P) | head -40`. A healthy boot logs `All MCP tools registered successfully` + `MCP server started successfully on stdio transport`.
- **Fix the cache:** move the corrupted dir aside: `NPX="$(npm config get cache)/_npx"; mv "$NPX/<hash>" "$NPX/<hash>.corrupt.bak"` (prefer `mv` over `rm -rf`; the latter is often permission-gated in agent setups). Re-test the boot command; it should now register the tools. The fix is **permanent**: future sessions connect clean.
- **Do NOT stop here: there is a fallback that does NOT depend on the user (validated 2026-08-20: 16 screens written with zero native Figma tool).** The tools vanish from the session, the SERVER does not: it is an ordinary stdio MCP server, so start an instance of your own and speak JSON-RPC to it.
  `WS_PORT=<free port> HTTP_PORT=8791 node scripts/mcp-direct/daemon.mjs &`,
  then the plugin trigger osascript (Step T), and call it through
  `python3 scripts/mcp-direct/fx.py <file.js>` (figma_execute) and
  `python3 scripts/mcp-direct/shot.py <nodeId> <out.png> [scale>=0.5]` (screenshot). The plugin connects to ALL live servers in the 9223-9232 range, one WebSocket per server, so this **does not steal the bridge** from another session. Free port: `lsof -nP -iTCP -sTCP:LISTEN | grep -E '922[3-9]|923[0-2]'`. `fx.py` and `shot.py` read `HTTP_PORT` like the daemon does. The HTTP endpoint is local and token gated: it refuses requests with an `Origin` header, wants `content-type: application/json` and a bearer token that the daemon writes to `<state-dir>/mcp-direct-<HTTP_PORT>.token` at boot; `fx.py` and `shot.py` send both. Stop the daemon when the work is done. Details in [scripts/mcp-direct/README.md](scripts/mcp-direct/README.md). Only escalate to the user if THIS also fails.
- **Then tell the user (only they can finish it this session):** "The MCP cache is repaired and the server boots clean now. Run `/mcp`, pick figma-console, Reconnect (keeps this session), or restart Claude Code, then say go." Do NOT loop the plugin-trigger osascript for this: the plugin layer was never the problem.

## Optional: watchdog LaunchAgent

`scripts/figma-watchdog.sh` polls `<state-dir>/figma-reconnect-signal` every 2 seconds and clicks the plugin menu when the file appears. It is meant to run as a LaunchAgent with the label `com.figma-maxxing.bridge-watchdog`; the template is `scripts/com.figma-maxxing.bridge-watchdog.plist.template`.

It is optional and off by default. `figma-open.sh` and `figma-bridge-reset.sh` check `launchctl list` for that label: if it is loaded they touch the signal file, if not they click directly with `osascript`. Installing it is a user decision; never load or unload it on your own initiative. Install, permissions and removal: [references/watchdog.md](references/watchdog.md).

## Tools owned by this skill

- `figma_get_status`: probe
- `figma_list_open_files`: which Figma files the bridge sees
- `figma_reconnect`: cheap reconnect attempt (informational as of v1.40.8, see Step 4)
- `scripts/figma-status.sh`: local snapshot (ports, sessions, cached URL, plugin drift)
- `scripts/figma-open.sh <alias|url|list>`: open the file + trigger the plugin
- `scripts/figma-add.sh <url> [alias] [label]`: register an alias
- `scripts/figma-bridge-reset.sh <alias|url>`: kill this session's server + open + trigger; gentle by default; `FIGMA_FULL_RESET=1` only after the user agreed to a Figma restart
- `scripts/mcp-direct/`: direct client for the layer 1 fallback
- `scripts/figma-watchdog.sh` + the plist template: optional watchdog
- `<state-dir>/figma-files.json`: canonical alias registry
- `<state-dir>/figma-bridge-last-url`: cache of the most recent target

## Hard rules

1. **Always Figma Desktop**, never the browser. All `open` calls use `open -a "Figma" <url>`.
2. **Always verify with `figma_get_status` after dispatch.** Script exit 0 != bridge connected.
3. **No fabricated success metrics.** "Validated 2026-05-23" or "untested" only. Never "~80%".
4. **Adding a new alias requires the URL from the user, not invention.**

## Canon

The full recipe is self-contained in THIS skill and the scripts in its `scripts/` directory: when the recipe changes (the user validates a new approach, a Figma version breaks the current method), the skill and the scripts change together. Tell the user and propose the edit to both (or a pull request upstream); do not silently edit an installed copy, which the next install may overwrite.
