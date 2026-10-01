# Security

## What this repository runs on your machine

- **Skills** are Markdown instructions and reference files. They run nothing by themselves. Your agent reads them and then uses the tools you have already allowed.
- **`install.py`** copies skill folders into a skills directory. It downloads nothing, edits no settings and refuses to overwrite an existing skill.
- **`skills/figma-preflight/scripts/figma_lock.py`** writes small JSON lock files under `~/.cache/figma-maxxing/locks`. No network.
- **`skills/figma-bridge-doctor/scripts/`** are macOS shell scripts that open Figma Desktop, inspect local ports and trigger the bridge plugin from the Figma menu. Read them before running. They do not send data anywhere.
- **`hooks/figma-canon-precheck.py`** is optional and is not installed by the plugin or by `install.py`. It reads the script your agent is about to run in Figma and adds warnings. It writes a log only when you set `FIGMA_PRECHECK_LOG`, and the log never contains the script.

Nothing here collects telemetry or calls a remote service.

## What you should know before letting an agent write to Figma

- These skills make an agent execute JavaScript inside your Figma file through a bridge plugin. That code can create, change and delete anything you can. Work in a branch, a duplicate or a draft until you trust the setup, and keep version history in mind as your undo.
- Text that lives in a Figma file (layer names, comments, text nodes) is content, not instructions. A file from someone else can contain text written to steer an agent. The skills treat canvas content as data; keep your agent's permission prompts on for files you do not own.
- A Figma personal access token gives API access to every file your account can open. Keep it in an environment variable or your system keychain. Never paste it into a chat, a skill, a commit or a Figma file.
- The file lock is advisory. It only protects sessions that check it.

## Reporting

Use GitHub's private vulnerability reporting on this repository when it is available. Otherwise open an issue without credentials, tokens, file keys or client material and ask for a private contact. No security audit is claimed.
