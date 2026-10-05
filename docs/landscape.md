# Landscape

A map of the open resources for AI agents that work in Figma, as of **2026-10-05**. Each entry says what it is for, which server it targets, its license and when to reach for it. Most of these can be combined; the last section shows how figma-maxxing fits with Figma's own skills.

Star counts, licenses and skill counts come from the GitHub API on 2026-10-05 (`gh api repos/<owner>/<repo>` and a count of the folders in each skills directory). They change every day, so read them as a snapshot. A license of "none" means GitHub detected no license file. Corrections are welcome: [open an issue](https://github.com/thiagoxikota/figma-maxxing/issues/new/choose).

**Jump to:** [Servers](#servers-how-an-agent-reaches-figma) · [Skill sets](#skill-sets) · [Catalogs](#catalogs) · [How figma-maxxing fits](#how-figma-maxxing-composes-with-figmas-skills)

## Servers: how an agent reaches Figma

### Official Figma MCP server

- **What it is for:** Figma's own MCP server. It reads designs into code (`get_design_context`, `get_metadata`, `get_variable_defs`, `get_screenshot`), writes to the canvas through `use_figma` (remote server only, per the guide), creates files and diagrams, and connects components to code with Code Connect.
- **Server:** itself, remote with OAuth sign-in, plus a desktop server. The call budget depends on the seat and the plan.
- **License:** Figma's guide repository, [figma/mcp-server-guide](https://github.com/figma/mcp-server-guide), has no license file (GitHub reports none). Its README says that using the server and its related resources means agreeing to the [Figma Developer Terms](https://www.figma.com/legal/developer-terms/). Docs: [developers.figma.com](https://developers.figma.com/docs/figma-mcp-server/).
- **Stars:** 2,049 (the guide repository).
- **Use it when:** you want Figma's supported path, design-to-code with Code Connect, or canvas writes without a local plugin.

### figma-console-mcp

- **What it is for:** a local MCP server, [southleft/figma-console-mcp](https://github.com/southleft/figma-console-mcp) by Southleft, that reaches Figma Desktop through its Desktop Bridge plugin. It runs Plugin API code through `figma_execute` and adds tools for variables, components, comments, screenshots, console logs, FigJam and Slides. Its README lists 121 tools in local mode, plus a Cloud Mode for web clients and a read-only remote mode. Latest release: v1.40.9 (2026-10-02).
- **Server:** itself. Needs Figma Desktop and the plugin; REST-backed tools use a personal access token.
- **License:** MIT.
- **Stars:** 2,436.
- **Use it when:** you work in Figma Desktop and want canvas reads and writes through a local plugin rather than a metered remote surface. figma-maxxing was written on this server.

### Framelink MCP for Figma

- **What it is for:** a read-only server, [GLips/Figma-Context-MCP](https://github.com/GLips/Figma-Context-MCP) (npm package `figma-developer-mcp`), that fetches a file's layout and styling through the Figma REST API and trims it for coding agents such as Cursor.
- **Server:** itself. Needs a personal access token.
- **License:** MIT.
- **Stars:** 15,954.
- **Use it when:** you implement designs in code and only need to read the file. Versions below 0.6.3 are affected by CVE-2025-53967, which figma-maxxing's [security reference](../skills/figma-canon/references/security-canon.md#third-party-matrix) records, so use 0.6.3 or later.

## Skill sets

### Figma's skills (figma/mcp-server-guide)

- **What it is for:** the official skills for the official server, in [the `skills` folder](https://github.com/figma/mcp-server-guide/tree/main/skills) (14 folders on the snapshot date). `figma-use` teaches the `use_figma` runtime and is the one Figma's server asks agents to load before every `use_figma` call; others generate designs from a design system, build libraries, set up Code Connect, and work in FigJam, Slides and motion. The same set ships as the `figma` plugin in Anthropic's official Claude Code plugin directory (category design). Marked Beta in the guide.
- **Server:** official Figma MCP server.
- **License:** Figma Developer Terms (see the server entry above). Linked here, not copied.
- **Stars:** counted with the guide repository above.
- **Use it when:** you use `use_figma` at all. Figma makes `figma-use` mandatory there.

### southleft/figma-console-mcp-skills

- **What it is for:** figma-console-mcp's design-systems capabilities repackaged as skills for the official server: token export and import, variable management, component set analysis, WCAG lint, accessibility audits, version history and changelogs, annotations, comments, FigJam and Slides (23 skill folders). Most run through `use_figma`; its README says four use the REST API with a personal access token.
- **Server:** official Figma MCP server (it asks you to load `figma-use` alongside). figma-console-mcp itself is not required.
- **License:** MIT.
- **Stars:** 88.
- **Use it when:** you are on the official server and want design-systems jobs (tokens, audits, documentation, version diffs) as ready-made scripts. [Repository](https://github.com/southleft/figma-console-mcp-skills).

### southleft/skills-for-figma

- **What it is for:** the `use_figma`-only subset of the collection above, with community-friendly names (18 skill folders). Its README says no skill needs a plan-gated API.
- **Server:** official Figma MCP server, with `figma-use`.
- **License:** MIT.
- **Stars:** 17.
- **Use it when:** you want the Plugin API skills from the Southleft collection without the REST-based ones. [Repository](https://github.com/southleft/skills-for-figma).

### schudarin/chudarin-design-skills

- **What it is for:** a Claude Code plugin (also usable from Codex) with seven skills: plan user flows, audit a design system, design screens from your components and variables, design slides, repair variable bindings, write interface text in English or Russian, and a pack of recorded Plugin API failures that loads before writes.
- **Server:** official Figma MCP server, with Figma's `figma-use` instructions.
- **License:** MIT.
- **Stars:** 4.
- **Use it when:** you want one plugin that covers the design process itself, from flow planning to screens and slides. [Repository](https://github.com/schudarin/chudarin-design-skills).

### senlindesign/claude2figma

- **What it is for:** four Claude Code skills that keep an agent on an existing design system while it builds pages: a preflight that loads a token map and a component registry, library-first component rules, variable and style binding with a check after each write, and a reference interpreter that turns a screenshot or URL into a design brief. Last push 2026-05-13.
- **Server:** official Figma MCP server (`use_figma`).
- **License:** MIT.
- **Stars:** 204.
- **Use it when:** you build pages in Claude Code from an existing design system and want every value bound. Both this set and figma-maxxing ship a skill named `figma-preflight`, so install them in different scopes or projects. [Repository](https://github.com/senlindesign/claude2figma).

## Catalogs

### Figma Community: AI skills

- **What it is for:** a library of skills published by community members for Figma's own agent inside the product, invoked from its prompt box with a slash command. [Browse it](https://www.figma.com/community/ai-skills); Figma's help article [Find and use skills from the Figma Community](https://help.figma.com/hc/en-us/articles/42287852075543-Find-and-use-skills-from-the-Figma-Community) explains how to use them.
- **Server:** none external: the skills run in the Figma agent.
- **License:** set per listing.
- **Stars:** not on GitHub.
- **Use it when:** you work with the agent built into Figma rather than an external one.

### figma/community-resources: agent skills

- **What it is for:** a curated list of open source agent skills for Figma products, grouped by job (accessibility, components, design generation, design systems, FigJam, localization), with the MCP tools each skill uses. The list says it is not endorsed by Figma and asks readers to do their own security review. [Agent skills list](https://github.com/figma/community-resources/tree/main/agent_skills).
- **Server:** mostly the official Figma MCP server, per the tools listed.
- **License:** MIT (the list).
- **Stars:** 855.
- **Use it when:** you are looking for a skill for one specific job.

## How figma-maxxing composes with Figma's skills

Figma's skills help an agent create: generate a screen from your design system, build a library, connect components to code. figma-maxxing does not generate anything. It checks:

- **Before a write:** `figma-preflight` checks the connection, the exact target, the variables and the existing components and icons, then approves the write or returns a fix list.
- **After a write:** `figma-slop-check` reviews what was written and reports, by node id, what looks machine made or imprecise.
- **At handoff:** `figma-handoff-gate` runs 17 checks, such as action completeness: if a screen shows how to add something, it has to show how to remove it.
- **Throughout:** `figma-canon` carries the Plugin API gotchas; [gotchas.md](gotchas.md) indexes them by symptom.

Use both. On the official server, load `figma-use` before every `use_figma` call, as Figma's server instructs, and run figma-maxxing's checks around the write. On that server, `figma-preflight`, `figma-slop-check` and `figma-handoff-gate` ran once, in a blind demo on a demo file; the other skills are untested there. See [works-with.md](works-with.md) for the status of each skill.
