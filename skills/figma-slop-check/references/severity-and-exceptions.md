# Severity, classes and exceptions

Load when compiling the punch list of the `figma-slop-check` skill, or when the user accepts or rejects an item of it. Covered here: the severity ladder, the three finding classes, the delta rule, the accepted drift file, the exception ledger, the expected false positives, and how to cite the canon.

Severity says how much it hurts. **Class says what to do.** Every finding carries both.

## Severity ladder

- **Critical:** the patterns rated Critical in the Severity scoring table of [`figma-canon/references/ai-slop-signatures.md`](../../figma-canon/references/ai-slop-signatures.md) (WCAG auto-fails, default Figma names), a frame collapsed completely (width=1 or height=0), and a gate closed without the visual verification. Hardcoded colors, missing auto layout and detached instances are High in the punch list (as in that table), but they are auto-fails of [`figma-canon/references/quality-rubric.md`](../../figma-canon/references/quality-rubric.md), so any one of them still blocks a PASS.
- **High:** breaks explicit canon (a raw hex where a token exists, a glossary violation, padding outside the scale).
- **Medium:** drift between sibling frames (off-by-1, capitalization variance, icon size mismatch).
- **Low:** naming drift that does not affect the render (a layer name outside the canon while the frame is visually correct).

When you present the punch list, **order it by severity, highest first**.

## Finding class (three ways)

The test is **loss**: what is lost when the found value is swapped for the canonical one?

- **exact:** a swap with no loss. The found value has an identical equivalent in the canon (same hex, same string, same number). It is only not bound or not applied. Example: a raw hex `#16181D` where the variable `color/surface/card` points to the same hex. Action: **fix it**. Delta = 0.
- **approximation:** a swap with a measurable loss. The value does not exist in the scale and gets pulled to its neighbor. Example: padding `14` in a scale that goes `12 · 16`. Action: **fix it and record the delta**. Delta = `+2` (found minus canonical).
- **new decision:** no swap is possible. The canon does not cover the case and no existing value is the right answer. Example: glass over a full-screen opaque fill (detector 11), when no surface token exists for that situation. Action: **do not fix it**. Escalate to the designer with the explicit question.

Watch the case that fools you: padding `14` when the sibling frames use `12` is still an **approximation**, not exact. The `12` being obvious settles where to snap. It does not erase the 2px delta the screen had.

**What this changes:** without the class, the default of every finding is "fix it". With the class, only **exact** gets fixed on its own. **approximation** gets fixed and leaves a numeric trail. **new decision** is pending design work disguised as a bug, and fixing it without deciding is makeup that makes legacy look like a system.

### Observations

Some detectors say "report it as an observation". That word marks a finding that is not a high failure, and it is not a severity of its own. Its class depends on the canon:

- **The canon does not settle the case** (an undecided card radius in detector 2, a stroke width the canon never fixed in detector 5): the observation is a **new decision**. It goes into the punch list with that class, ordered with the others, with the explicit question of what the canon should be. It never becomes a loose footer note that nobody reads, and it never becomes a silent fix.
- **The canon settles it** (detector 8, a concept that is only sometimes an instance of a component that exists): classify it by the loss test above, like any other finding.

## Delta is mandatory on an approximation

Delta = found value minus canonical value, signed, in the unit of the detector (px, pt, count). `delta +1`, `delta -2`, `delta +0.5`. Without the delta, the approximation turns into a generic "medium" and the debt evaporates.

**Delta is never summed.** Different units do not add up, and opposite signs cancel: `+2px` with `-2px` would give zero and read as "no debt". The summary carries the **count** of approximations and the largest absolute delta, never a total.

## Accepted drift is not an exception

Approximations that the user accepts accumulate in `.figma-slop-check/drift-accepted.json` in the project, **not** in the exception ledger. If the file does not exist, create it with `{ "version": 1, "accepted": [] }`. Each entry is `{ id (drift-NNN), detector, nodeId, found, canon, delta, acceptedAt }`.

The difference between the two files matters:

| | Exception ledger (`.figma-slop-check/exceptions.json`) | Accepted drift (`.figma-slop-check/drift-accepted.json`) |
|---|---|---|
| Effect | **Silences** the detector | **Counts** the deviation |
| Meaning | Intentional deviation, it is local canon | Known debt, still to be paid |
| Leaves the punch list? | Yes, with a footer line | No, it comes back with its delta until it is paid |

Confusing the two turns a backlog into an amnesty.

One point the field rule leaves open: it appends an approximation to this file when the fix is applied (see "On failure" in the skill), and it also treats every entry as debt that comes back with its delta until it is paid. It does not say when an applied entry counts as paid. Ask the designer when that matters, and never use this file to silence a finding.

Never record accepted drift in a file that another tool generates. The next run of the generator overwrites it and the delta disappears in silence, which is exactly what this section exists to prevent. A generator may READ the accepted drift file and consolidate it. The direction is that one, never the reverse.

`.figma-slop-check/` is a folder at the root of the project. Create it on the first accepted item.

## Exception ledger

A persistent ledger for intentional deviations. It lives in `.figma-slop-check/exceptions.json` in the project. It is local to the project, not to the skill: exceptions are about this design system.

- Each entry is `{ id, detector, scope (nodeId or nodePath), deviation, reason, addedBy, addedAt, expiresAt? }`.
- **The reason is mandatory.** Without it, reject the entry.
- **The scope is mandatory.** A catch-all (no `nodeId` and no `nodePath`) is rejected: it would silence the whole detector.

```json
{
  "version": 1,
  "exceptions": [
    {
      "id": "exc-001",
      "detector": "spacing | radius | token | terminology | icon | frame | layer-naming",
      "scope": {
        "nodeId": "123:456",
        "nodePath": "01-home / hero / btn-primary"
      },
      "deviation": {
        "found": "padding T17 R16 B17 L16",
        "canon": "scale (4,8,12,16,20,24,32,40,48)"
      },
      "reason": "Hero button uses 17pt vertical to match 8pt grid + 1pt cap visual correction.",
      "addedBy": "agent",
      "addedAt": "2026-05-07",
      "expiresAt": null
    }
  ]
}
```

Fields:

- **id:** unique and monotonic (`exc-001`, `exc-002`, ...). Used to revoke later.
- **detector:** which detector this suppresses. Match it exactly.
- **scope:** what the exception applies to. `nodeId` is the most specific and suppresses only that node. `nodePath` is a slash-joined name path, broader: it suppresses any node whose ancestry matches. Use one or the other; `nodeId` wins if both are present.
- **deviation:** the `found` and `canon` strings to match. Compare the text of the finding against them by substring.
- **reason:** required, a human explanation.
- **addedBy / addedAt:** provenance. `addedAt` is an ISO date. `addedBy` defaults to the agent when the agent appends in session; the user can ask for another value.
- **expiresAt:** optional ISO date. After it, the exception is ignored. Use it for a temporary tolerance during a redesign.

Do not add to the ledger:

- "It looks fine" as the reason. That is not a reason: reject it.
- A catch-all scope, or the suppression of a whole detector (a `detector` with no scope). Both silence the detector entirely: reject them.
- An exception that survives more than about 6 months without being revisited. Set `expiresAt` if it is temporary.

### Ledger workflow

When the user accepts a finding as intentional:

1. Read the ledger (create it with `{ "version": 1, "exceptions": [] }` if it does not exist).
2. Append an entry with the next `exc-NNN` id.
3. Write it back and validate the JSON. Confirm the exc id to the user so it can be revoked later.

When a rigor pass runs:

1. Load the ledger (skip silently if it is absent).
2. For each finding, compare against the active exceptions (not expired, scope matches, deviation matches by substring).
3. Suppressed findings leave the punch list, but one line goes in the footer: `Suppressed by ledger: N findings (exc-001, exc-007). Say "show suppressed" to see them.` That is a natural language command, not a slash command.

### Revoke

The user says "remove exc-003" or "revoke that exception": remove the entry. No soft delete. The ledger stays short and readable.

## Expected false positives

- **Intentional padding outside the scale**, when the user explicitly deviated ("this screen uses 17 because X"). Accept it once. If it comes back, record it in the exception ledger.
- **Glossary "violated" in demo or placeholder copy.** Check whether the screen is a placeholder before reporting.
- **Token mismatch on a work-in-progress screen.** If the frame name ends in `/wip` or `/draft`, lower the severity from high to medium.
- **A real component spec with many fields.** The density check targets meta cards about a flow, not a component spec that legitimately needs more fields.
- **The user asked for it.** A request for a "detailed", "complete" or "exhaustive" list turns the density check off. A request for a summary turns the trailing summary check off. Work on a pull request document (not chat) turns the markdown header check off.

Before calling any card slop, inconsistent or dead space, apply the Sibling-check rule of [`figma-canon/references/ai-slop-signatures.md`](../../figma-canon/references/ai-slop-signatures.md): inspect at least 2 siblings of the same class. The flagged item is often the canon.

## How to cite the canon

Every finding must point to where the expected value is written. Use the sources in this order, preferring the most structured one available:

1. **Machine-readable registries** of tokens and components, when the project has them.
2. **The project's design docs and the project map** (`figma-map.md`): token docs (color, typography, spacing, radius, elevation, motion), the component inventory with its variants, the glossary and voice guide, the layer naming convention. For layer naming with no project rule, cite [`figma-canon/references/naming-canon.md`](../../figma-canon/references/naming-canon.md).
3. **The file's Figma variables.** They are the live source of truth for tokens. Use them when the registry and the docs diverge, and resolve the difference before reporting the finding.

For a live component count, call `figma_get_design_system_summary` instead of quoting a number written in a doc.

If the project keeps a list of known contradictions or of items already resolved, check it before reporting: the finding may already be settled.

If the canon does not cover the case, the finding goes out with the class **new decision** and the explicit question of what the canon should be.
