# Rigor detectors

Load when running the Rigor lens of the `figma-slop-check` skill. The 15 precision detectors in full: for each one, how to capture the data, what counts as a failure, what does not, and how to cross-reference. Plus what data to collect in one read-only pass before running them.

Each detector has a capture method (how you get the data), a failure rule (what counts as a failure) and an output (how to report it). This is not "run it mentally": execute through the figma-console MCP server and compare.

Scales belong to the project. Read them from the file's variables, the project's token docs, or the project map (`figma-map.md`). The scales printed below are invented examples that only illustrate each rule, not a universal canon: swap them for your own design system's scales before you judge anything.

Severity words (critical, high, medium, low) and the finding classes are defined in `references/severity-and-exceptions.md`. Where a detector says "report it as an observation", see "Observations" in that file for the class it takes.

## Collecting the data

### Refresh state first

Call `figma_search_components` at the start. Node ids are session specific and may be stale. If the Bridge is disconnected, run the `figma-bridge-doctor` skill and stop.

### The read-only pass

Write a short read-only `figma_execute` script of your own that walks every descendant of the target and returns one flat record per node. Read one screen per call and merge the per-screen results afterwards: a dump of every descendant with its fills, strokes and effects grows fast, and a multi-screen target makes a payload that can overflow the context, hit the `figma_execute` timeout (5000 ms by default, 30000 ms maximum, set with `timeout`) or hit the output cap described in [`figma-canon/references/figma-execute-atomicity.md`](../../figma-canon/references/figma-execute-atomicity.md).

What each record carries:

- **Identity:** `id`, `name`, `type`, the parent id and the depth in the tree.
- **Box:** `width`, `height` and the node `opacity`.
- **Auto layout:** the 4 paddings, `itemSpacing`, `layoutMode`, `primaryAxisSizingMode`, `counterAxisSizingMode`, `layoutSizingHorizontal`, `layoutSizingVertical` and `layoutPositioning`.
- **Radii:** `cornerRadius` and the 4 per-corner radii.
- **Paints:** for each fill and stroke, the type, the hex color, the paint opacity (and the weight on strokes), plus the id and the name of the bound variable when there is one. Resolve the name with `figma.variables.getVariableByIdAsync`, which also reaches library variables that a local collection listing does not show, and cache it per id.
- **Effects:** type, radius, offset, color, spread and visibility.
- **Text (TEXT nodes only):** `characters`, `fontName`, `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing` and `textStyleId`.
- **Icons:** the size of every node whose name starts with `icon-` or `Icon/`.
- **Instances (INSTANCE nodes only):** `isInstance: true`, the main component id and key, `componentProperties`, and `isDetachedFromComponent: true` when no main component resolves. Leave the `isInstance` key off every other node.
- **Detached copies (FRAME nodes only):** `detachedInfo` when it is not null (`{type: 'local', componentId}` or `{type: 'library', componentKey}`). Figma turns a detached instance into a FRAME, so this is the trace a detach leaves.
- **Tokens:** whether the node has any bound variable at all.
- **Modes (once per run, not per node):** a `_modes` list with the name of each variable collection and its mode names, so the run can tell when it is mode-blind.

Two canon rules apply to this read. Record a mixed value (`figma.mixed`, a Symbol) as the string `"mixed"`, because a Symbol in the returned object fails the whole call. Resolve the main component with `getMainComponentAsync()`, because the sync `mainComponent` getter throws in dynamic-page mode. Both are in [`figma-canon/references/plugin-api-anomalies.md`](../../figma-canon/references/plugin-api-anomalies.md) ("figma.mixed (Symbol)" and "mainComponent is sync-only").

Bring the data back with `return`, the only output channel the canon accepts ([`figma-canon/references/plugin-api-data.md`](../../figma-canon/references/plugin-api-data.md)), and pass `timeout: 30000` for a dense screen. Do not log it with `console.log`: the optional precheck hook warns on `console.log(`.

Save the JSON to `.figma-slop-check/runs/<YYYY-MM-DD>-<screen-slug>.json` in the project (create the directory if it does not exist). It is useful for a diff between runs.

If the result has more than 100 nodes, group by the parent id before processing so the context does not overflow.

This pass does not need `x` and `y`. Detector 12 reads `section.children` in its own read-only `figma_execute` call.

### Running the detectors

The detectors consume the JSON. That part is pure agent logic, with zero Bridge calls. Run them in sequence for clarity of output, not for cost. Capture the findings in detector order so the punch list stays grouped by type.

Before running, read `_modes` from the collected data:

- If it is empty, add this footer to the output: `Mode-blind run - no variable modes detected (or library-only design system)`.
- If 2 or more modes exist, add: `Run extracted current-mode values only - token findings reflect default mode; cross-mode validation pending.`

## 1. Spacing precision (off-by-1, padding and gap drift)

**Capture:** `figma_execute` to extract `paddingTop` / `paddingRight` / `paddingBottom` / `paddingLeft`, `itemSpacing` and `counterAxisSpacing` of each relevant frame. For a cross-screen check, list all sibling frames of the section.

**Fails when:**

- Padding or gap is outside the project's spacing scale. Invented example of a scale (swap in your own): `4 · 8 · 12 · 16 · 24 · 32`. Against that scale, 17, 23 and 31 fail, and so do 7, 13 and 19.
- Padding is asymmetric without intent. `T16 R24 B16 L24` is fine (intentional). `T16 R24 B17 L24` fails (off-by-1).
- Sibling frames have different padding with no justification. Example: one row of a list with `T12 B12` and its sibling row with `T14 B12`.
- The gap between rows of one list is inconsistent. Example: 11 frames with gap 8 and 1 with gap 12.
- The page edge gutter of a section container differs from the project's gutter. Invented example of a gutter canon: `0 / 16 / 0 / 16`.

**Component vocabulary carve-outs (do not normalize, do not flag):** a scale can hold a step that exists for one component only. Invented example: a `6` gap used only inside a compact tag, next to the scale above (do not normalize it to 4 or 8). Record carve-outs like these in the project map so the next run knows them.

**Not a failure:**

- Different padding when the component is semantically different (a header versus a row).
- A larger gap at a section divider (intentional delimitation).

## 2. Radius drift

**Capture:** `cornerRadius`, or `topLeftRadius` / `topRightRadius` / `bottomLeftRadius` / `bottomRightRadius`, of every surface (cards, buttons, inputs, sheets).

**Fails when:**

- The radius is outside the project's radius scale. Invented example of a scale (swap in your own): `0 · 4 · 8 · 12 · 16 · 24 · 9999 (full)`.
- **Decimal drift** (copy-paste sloppiness, not intent): values such as `2.5`, `4.5`, `12.3` or `18.5`, and near misses such as `25` next to a `24` step. All of them snap to the nearest value of the scale.
- The same class of surface has different radii. Example: a card with r=12 on one screen and r=16 on another. If the project has not yet chosen between two candidate card radii, report it as an **observation**, not as high, until the designer decides.
- The radius is asymmetric without intent (the two top corners differ when the surface should be uniform).
- The button radius drifts between screens. A primary button always has the same radius. If it varies, it fails.

## 3. Token compliance (raw hex, no variable)

**Capture:** `figma_execute` to extract `fills` and `strokes` of each node. Check whether `boundVariables.fills` exists. If it does not, the value is a raw hex.

**Fails when:**

- A raw hex sits where a matching variable exists. Example: `#16181D` typed straight into the fill when `color/surface/card` points to that same hex.
- A color matches no token of the design system. Example: `#FF3A3D` when the token is `#FF3B30`.
- A stroke has no bound token.
- Mixed use: the same concept (primary text, for example) bound to a variable in one place and raw in another.
- A token name does not exist in the file's variable collections. That is a hallucinated token: reject it. The same applies to a text style name that does not exist in the file.

**Exception:** a raw value on any translucent fill (paint opacity below 1), such as a button pill tinted at 18% or an icon badge, because binding a variable through `setBoundVariableForPaint` resets the paint opacity to 1 and a token cannot carry the opacity. See "setBoundVariableForPaint stomps explicit opacity" in [`figma-canon/references/plugin-api-anomalies.md`](../../figma-canon/references/plugin-api-anomalies.md). The same exception covers translucent black overlays that a project keeps raw on purpose.

**How to cross-reference:**

1. `figma_get_variables` on the page to list every token.
2. For each raw hex in the frame, look for an exact match in the token map.
3. Report every hex that had a token available and did not use it.

## 4. Terminology drift (cross-screen, plus glossary lock)

**Capture:** `figma_execute` extracting the `characters` of every TEXT node of the frame, grouped by screen. Compare with the project's glossary, if it has one.

**Fails when (glossary lock):**

- A string contradicts the project's glossary: a locked product term replaced by a generic synonym, a protected noun translated, or a locked capitalization changed. Protected nouns are never translated and never re-capitalized.

**Fails when (cross-screen drift, more subtle and more damaging):**

- Plural inconsistency: "Orders" on one screen, "Order" on another for the same concept.
- Capitalization variance: "Order history" versus "Order History" versus "order-history" for the same label.
- A verb on one screen and an adjective on another ("Enable" versus "Enabled"). Pick one.
- Punctuation drift: "View details" versus "View details." (a period that comes and goes on labels).
- Tense drift: "Manage team" versus "Managing team" for the same button.
- Title case versus sentence case mixed across buttons and titles.

**Misspellings that live in the design system:** when a token, style or component name in the library carries a typo, the binding keeps that spelling. Do not correct it inside a binding and do not auto-fix it on the canvas. Flag it as a list for the designer.

**Output:** the list of strings that appear 2 or more times with variations, plus which form should be the canonical one.

## 5. Icon size drift

**Capture:** `figma_execute` listing every `icon-*` node (or every component with the `Icon/` prefix). Extract `width x height`.

**Fails when:**

- The icon size is outside the project's icon scale. Invented example of a scale (swap in your own): `16 · 20 · 24 · 32`, with a larger size accepted only where the project allows it as a decorative badge, outside the chrome scale. Against that scale, 18 and 22 fail.
- The same semantic icon appears in different sizes for no reason (a chevron-right at 16 in one row and at 20 in an identical row).
- An emoji or a text glyph is used as an icon. Icons are instances of the file's icon component (instance swap), never emoji and never text.

**Observation, then ask:** when the project's icon canon fixes a stroke style (for example: single stroke, rounded, outlined) but no numeric stroke width, report a stroke width variation between sibling icons as an observation and ask the user which one is canon (a chevron at 1.5 versus 2 is a question, not a fix).

**Source mix:** when icons come from more than one source (instances from a downloaded SVG set versus raw vector frames), list the sources in the punch list so the designer can choose the long-term library.

## 6. Frame size and structure mismatch

**Capture:** `figma_execute` to extract `width x height`, `layoutMode`, `primaryAxisSizingMode` and `counterAxisSizingMode` of each screen frame of the section.

**Fails when:**

- Screens of the same family have inconsistent widths (430 on one, 393 on another) with no justification.
- The height is arbitrary when it should be AUTO (a frame with a fixed height of 932 that should hug its content).
- `counterAxisSizingMode: "AUTO"` (hug contents) is set where it should be `"FIXED"`. On a screen frame, `FIXED` holds the full width of the device. For a child that should stretch to its parent, read `layoutSizingHorizontal` instead: `"HUG"` where it should be `"FILL"` (fill container). Either case causes lopsided auto layout.
- `layoutMode` is mixed between sibling frames for no reason.
- The section background equals the frame background (no visual separation).

## 7. Layer naming

**Capture:** list every child name, recursively.

**Fails when** (the canon is [`figma-canon/references/naming-canon.md`](../../figma-canon/references/naming-canon.md)):

- Figma defaults: `Rectangle`, `Vector`, `Frame`, `Group`, `Ellipse`, `Rectangle 91`.
- A component name has no `/` (use `Button/Primary`, not `Button-Primary`).
- A layer name has a slash that is not a variant (`btn/primary` on a layer: use the middle dot, `btn-primary · Label`).
- A root frame has no `NN-name` prefix (`01-home` is fine, a loose `home` fails).
- PascalCase on an internal layer (reserved for components).
- Human text glued into a kebab name (`btn-Add another item` fails, `btn-primary · Add another item` is fine).
- A device prefix in the frame name (`iPhone 14 - 01-...` is redundant).

If the project map defines a different layer convention, the project map wins (see "Project-specific canon defers to project map" in the naming canon).

## 8. Component instance versus detached copy

**Capture:** the flags `isInstance`, the main component id and `isDetachedFromComponent` in the collected data, plus `detachedInfo` on FRAME nodes. Only INSTANCE nodes carry `isInstance: true`; any other node has no `isInstance` key.

**Fails when:**

- A layer whose name matches a canonical component (for example `Button/Primary`, `Card/Elevated`, `Icon/16/Chevron-Right`) is not an INSTANCE (no `isInstance: true`). It is a detached copy. High.
- A FRAME has a non-null `detachedInfo`. It was detached from that component, whatever its name. High. Report the component id or key it names, so the fix can re-instance it.
- An INSTANCE has `isDetachedFromComponent: true`, which the read-only pass sets when no main component resolves for it. Same problem. High. This rule never fires on a detached copy, because a detached copy is no longer an INSTANCE: the `detachedInfo` rule above covers that case (blind demo, 2026-10).
- The same visual concept repeats N times but only M are instances (M < N). Drift. Report it as an observation, not as high like the two bullets above. The component exists, so the canon covers the case: classify it by the loss test like any other finding (`references/severity-and-exceptions.md`).
- An instance points at a test or scratch component instead of the canonical library component. Reject it.

**Why it matters:** detached copies are the largest silent source of design system drift. A copy is visually identical at the moment it is made, and becomes a snowflake as soon as the main component is updated.

## 9. Variant property mismatch

**Capture:** `componentProperties` on INSTANCE nodes, plus the canonical definition: the main component, or the project's component docs if it has them. The read-only pass does not capture the allowed properties and their values. Read them in one read-only `figma_execute` call:

```js
const inst = await figma.getNodeByIdAsync("123:456");
if (!inst || inst.type !== "INSTANCE") return { error: "not an instance" };
const main = await inst.getMainComponentAsync();
if (!main) return { error: "no main component" };
const defs = main.parent && main.parent.type === "COMPONENT_SET"
  ? main.parent.componentPropertyDefinitions
  : main.componentPropertyDefinitions;
return defs;
```

Or call `figma_get_component_details` on the component.

**Fails when:**

- The instance has a property name that is unknown (not on the main component). Medium.
- The instance has a property value outside the allowed enum (for example `State="weird"` when the enum is `[default, hover, pressed, disabled]`). High.
- A required property is not set (for example a Button with no `Variant`). Medium.

## 10. Typography drift

**Capture:** on TEXT nodes, `fontName`, `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`, `textStyleId`.

**Fails when:**

- The same text role (label, body, caption) appears in two places with a different `fontWeight` or `fontSize`. Example: the label of one row at `16/400` and the label of its sibling row at `16/500`.
- A text has no `textStyleId` when the canon has a matching text style (an ad hoc raw font). Medium.
- The font family is inconsistent (one family on one screen, another family on the next), or a family outside the project's type system appears. High.
- The line height in px differs between body texts that should be equal. Medium.
- A text style name does not exist in the file (a hallucinated style). Reject it.

## 11. Glass only over content

Run this detector only when the file uses a glass effect.

**Capture:** list every node with a glass effect applied (`effects[].type === "GLASS"` in the collected data). For each one, walk up the tree to the root of the screen and collect the `fills` of the parent chain and the frame size of the immediate parent.

**Fails when:**

- A glass surface sits directly on a full-screen opaque fill (the parent is a frame at least as large as the screen viewport AND its fill is solid and opaque). High. Glass there becomes a fancy blur with no real refraction: there is no content underneath to distort.
- A glass card fills the entire screen, with no chat, video, list, photo or map behind it. High. Replace it with a solid surface color from the project's tokens.
- Glass sits on glass (stacking with no visual separation of at least 1 elevation step). Medium.
- The fill of the glass surface has an opacity above 0.85 (`fills[].opacity` in the collected data; the node `opacity` is 1 on almost every node, so it does not measure this). It turns pseudo-opaque and loses the glass affordance. Medium.
- The project defines glass weights (for example thin, regular, thick), each assigned to a class of surface, and a surface uses a weight that belongs to another class. Medium.

**How to cross-reference:**

1. If the project keeps its glass parameters as constants, read them with `figma_get_variables` and confirm they hold. Drift in any constant is high.
2. Walk the parent chain to detect whether a TEXT node, an image fill, a map, or a content instance sits under the glass. If the chain has only a solid fill, it fails.

**Not a failure:**

- Glass on an onboarding or empty state with a gradient behind it (the gradient counts as real content for refraction).
- Thin glass as a pinned badge over real content.

## 12. Frame-name label clearance (section spacing)

**Capture:** list the direct children of a SECTION (or of a handoff grid FRAME), sort by `y`, and compute the gap between `prev.y + prev.height` and `next.y`.

**Fails when:**

- The gap between two frames adjacent in y is under **80px**. High. In Figma's design view the name of each frame renders as a label positioned ABOVE the frame. With a small gap the label lands on top of the content of the frame above.
- This applies to EVERY pair of adjacent frames in the y column: a screen and the caption right below it, a caption and the next row of screens, a summary frame and its caption, a sub-cover and its screens.
- 80 is the floor. The **recommended value is 100**, a safety margin for longer labels such as "caption · 03-item-editor (placeholder)".

**Not a failure:** a gap inside an auto layout PARENT (children of a frame that has a `layoutMode`), because the frame name of the child does not render on its own. Only the parent name renders. This detector is only for free-positioned children of a SECTION or of standalone frames.

**How to cross-reference:**

1. `figma_execute` extracts `section.children`, sorted by y.
2. For each adjacent pair, compute `next.y - (prev.y + prev.height)`.
3. Report every gap under 80 with the pair of node ids and the measured gap.

**Extra output:** if 3 or more pairs fail, suggest one batch correction (re-lay out all the row gaps at 100) instead of one fix per pair.

For a new handoff section built with right-side annotations, the spacing constants in [`figma-canon/references/handoff-format.md`](../../figma-canon/references/handoff-format.md) (Spacing canon) apply. This detector keeps the legacy floor that the same file still accepts for sections without per-screen annotations.

## 13. Caption FILL-in-HUG structural audit

**Capture:** list every caption frame (named `caption · <screen>` in these examples; use your project's caption naming from the project map, or this capture finds zero frames and the detector passes falsely). For each one, walk the children recursively collecting `layoutMode`, `layoutSizingHorizontal` and `layoutPositioning` of each node.

**Fails when** (the canon is [`figma-canon/references/handoff-format.md`](../../figma-canon/references/handoff-format.md), Caption layout):

- The caption frame contains a HORIZONTAL + HUG text stack whose TEXT children (badge + title) have `layoutSizingHorizontal=FILL`. High. The HUG parent caps the FILL children at the width of the smallest sibling (usually the badge, about 80px), which forces the title to wrap into 2 or 3 lines. If body and triggers are `layoutPositioning=ABSOLUTE` with a fixed y below, the wrapped title renders on top of the body.
- Body or trigger TEXT nodes have `layoutPositioning=ABSOLUTE` while the caption frame is a VERTICAL auto layout. Medium. Mixing absolute with auto flow is fragile: any change in the height of the text stack breaks the alignment.
- The caption frame is fixed on both axes and a long body text exceeds the fixed height. Medium (the text clips).

**How to cross-reference:**

1. For each caption frame, dump the children tree with sizing modes.
2. Detect the pattern `text-stack HUG > [TEXT badge FILL, TEXT title FILL]` and report it.
3. Detect any TEXT with `layoutPositioning=ABSOLUTE` whose parent has a `layoutMode` other than `NONE` and report it.
4. Suggest the fix: badge + title to HUG, body + triggers to AUTO + FILL.

**Validation:** this detector does not replace a screenshot. After the fix, capture every affected caption individually (not a sample), because a text overflow check does not catch overlap between distinct nodes.

## 14. Layout collapse (auto layout sized wrong)

**Capture:** a recursive walk of the target frames. For each FRAME or INSTANCE child of a VERTICAL auto layout parent, compute the ratio `child.width / parent.width`.

**Fails when:**

- A container child (a frame with `children.length > 0`, leaving out buttons and icons) has `width < parent.width * 0.7` AND `parent.layoutMode === 'VERTICAL'`. **High.** It typically collapsed to the width of its content when it should have stretched to the width of the parent.
- A root frame has a height under 100 with no justification. Medium (sized wrong).
- A frame has width=1 or height=0. Critical (collapsed completely).

**Root cause:** `layoutAlign='STRETCH'` set BEFORE `parent.appendChild(child)` fails silently. [`figma-canon/references/auto-layout-canon.md`](../../figma-canon/references/auto-layout-canon.md) documents the same ordering trap for `layoutSizing*=FILL`.

**Recovery (a write, so it needs approval):**

```js
child.layoutSizingHorizontal = 'FILL';
child.layoutSizingVertical = 'HUG';
```

## 15. Visual screenshot verification (mandatory before closing)

**Capture:** `figma_capture_screenshot` on 3 to 5 representative frames of the batch. Not all of them: that wastes tokens.

**Fails when:**

- Any screenshot shows overlap, visual collapse, label on label, a photo cropped wrong, a broken gradient, or obvious misalignment. **High.**
- The visual verification is skipped and the work is declared ready on the strength of the other detectors. Critical. The detectors above read node data, not pixels: they miss visual collapse, overlap between distinct nodes, bad crops and visual regression.

**Cadence:** pick 1 frame per category (a form, a list, a dashboard, a multi-section screen, and the dark outlier if there is one). 5 screenshots cost about 200KB of context.
