# Privacy

Short version: this project collects nothing. There is no telemetry, no analytics, no account and no server run by the author. Your Figma token and your files stay on your machine and with the services you already use.

## What the author receives

Nothing. No script, hook or skill in this repository sends data to the author or to any service the author runs. There is no usage tracking, no crash reporting and no "phone home" check for updates.

The only things the author can see are the ones you choose to post publicly on GitHub: issues, discussions and pull requests. Those are public. Keep client names, file keys, tokens and screenshots of work you do not own out of them.

## What stays on your machine

| What | Where | Written by |
| --- | --- | --- |
| Your Figma personal access token | An environment variable, your system keychain, or your agent's MCP configuration if you registered the server with `-e FIGMA_ACCESS_TOKEN=...` | You. No script in this repository writes it to a file or prints it. |
| File aliases and the last opened URL | `${FIGMA_MAXXING_STATE_DIR:-~/.config/figma-maxxing}` | `figma-bridge-doctor` scripts, only for files you add |
| The `mcp-direct` bearer token | `<state-dir>/mcp-direct-<HTTP_PORT>.token`, mode `0600`, deleted when the daemon exits | `daemon.mjs`, only while you run it |
| Advisory lock files | `~/.cache/figma-maxxing/locks` (or `FIGMA_LOCK_DIR`) | `figma_lock.py` |
| Precheck log | The file you name in `FIGMA_PRECHECK_LOG`. Off by default, and it never contains the script | `figma-canon-precheck.py` |
| Copied skills | The skills directory you install into | `install.py` or your installer |

Delete any of these at any time. Nothing else depends on them.

## Network

The skills, the hook, the installer and the bridge scripts connect only to `127.0.0.1`: the `mcp-direct` clients (`fx.py`, `shot.py`) talk to their local daemon. That daemon, the only listener in this repository, binds `127.0.0.1` and nothing else.

One maintainer script is the exception. `scripts/check_api.py`, which CI and contributors run to check Plugin API names, downloads the pinned `@figma/plugin-typings` from registry.npmjs.org and verifies its sha512. It is not part of the skills or the plugin, and it sends nothing about you.

Using the skills does involve services outside this repository, each under its own terms:

- **Figma.** `figma-console-mcp` (a third-party server you install yourself) and some skill steps call Figma with your token, for example the REST API at `api.figma.com` to read comments. That is the same access you already give Figma.
- **Your AI agent's model provider.** When your agent reads a Figma file, the content it reads (layer names, text, comments, screenshots) goes into the agent's context and so to the model provider you use. That is how any AI agent works, not something these skills add. Use a provider and plan whose data terms fit the files you open.
- **Install tools.** GitHub, a plugin marketplace or the `skills` CLI serve the files to you and keep their own logs and counts. skills.sh, for example, shows an install count for this repository.

## The llms.txt prompt

Pasting the "Paste this into your AI" prompt into a chat AI sends that prompt to the chat service, and the AI then reads `llms.txt` from GitHub. The page holds design rules only; it asks for nothing about you and carries no tracking.

## Contact

Questions about privacy: open an issue. Anything sensitive, such as a token you think leaked through one of these scripts: report it privately as described in [SECURITY.md](SECURITY.md).

This policy changes only through a commit to this file, so its history is the change log.
