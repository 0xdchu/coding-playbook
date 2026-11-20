---
status: approved
approved: 2026-11-20 (owner, "đủ 5 bộ CSS thuần")
---
# Design-system library: five modern systems the mockup skill can copy

Ticket: Plane APS-87.

## Problem

The `mockup` skill starts every prototype from one neutral template, so each mockup re-invents tokens and components,
screens drift between projects, and the agent spends its most expensive effort deriving colour, type and states. The
first attempt (GOV.UK + Primer) was rejected by the owner as dated; the library must use modern systems and remove the
old ones.

## Outcome

A `design-systems/` library with **five** modern systems — **shadcn/ui**, **Radix Colors**, **Open Props**,
**Microsoft Fluent 2** and **IBM Carbon 11** — packaged for an LLM to read once and copy:

```
design-systems/
  README.md                     # how to choose; what a system must contain
  shadcn/{manifest.json,tokens.css,components.css,reference.html,LICENSE}
  radix/{...}
  open-props/{...}
  fluent/{...}
  carbon/{...}
```

1. **Five systems, five files each.** Every folder carries a manifest, tokens, components, a reference page and the
   upstream LICENSE; the old `govuk/` and `primer/` folders are gone.
   - Checked by: `scripts/check.py` requires the five folders and every file.
2. **Manifest and reference stay in sync.** Every class named in `components[]` is shown in `reference.html`.
   - Checked by: `scripts/check.py` matches classes inside `class="..."` attributes.
3. **Reference pages hold at 1440 and 390.** No console error and no horizontal overflow at either width.
   - Checked by: a headless render of every page at both widths.
4. **The mockup skill copies a system in one step.** `SKILL.md` step 2 names the library and its five uses; the
   template README repeats the copy rule.
   - Checked by: reading the two files in the PR.
5. **Small enough to read once.** Each system ≤900 lines of CSS+HTML.
   - Checked by: `wc -l` per system.

## Constraints

- **Licences:** MIT for shadcn, Radix, Open Props and Fluent; Apache-2.0 for Carbon. Keep the upstream licence text
  per folder and name source, version and date in `manifest.json`.
- **Official tokens, curated components.** Radix/shadcn/Fluent/Carbon are React/Sass; a static mockup cannot load
  their components. The library takes the official colour/type/spacing values and writes plain-CSS recipes in the
  same visual language; the manifest says so.
- **No proprietary fonts bundled.** Fluent uses the Segoe UI stack, Carbon the IBM Plex Sans stack (optional).
- **Plain CSS variables and classes, no JS, no build, no npm.** A system is two stylesheets and one reference page.
- **The library never enters a mockup by remote URL.** The skill copies the files, so a page keeps working offline and
  over `file://`.
- **No invented components.** Only patterns the upstream system ships.

## Decisions

1. **Five systems, one per product shape.** shadcn for modern SaaS, Radix for app UI, Open Props for playful
   products, Fluent for Microsoft-style productivity, Carbon for enterprise consoles.
2. **Remove GOV.UK and Primer.** Owner decision 2026-11-20: they read as dated next to the modern set.
3. **Manifest is the contract.** `manifest.json` names source, licence, version, font stack, accent, dark support and
   the component classes; `check.py` holds the two in sync.
4. **The mockup copies, not links.** `tokens.css` + `components.css` are copied beside the mockup; its own `styles.css`
   keeps only layout and brand overrides.
5. **Light first; dark where the upstream defines it.** All except Open Props ship a dark theme.

## Coverage

- Who: the mockup skill and the main session choosing a system; the owner reviewing a mockup; a reviewer reading
  `reference.html`; upstream maintainers whose licence and values are cited.
- Trigger: a new mockup starts and its design language is chosen; a system is added or its manifest changes.
- Main path: pick a system from `design-systems/` → copy `tokens.css` and `components.css` into the mockup → screens
  use its classes → the reference page shows every state → `check.py` holds manifest and reference in sync.
- Branches and failures:
  - a missing manifest, LICENSE or component class: `check.py` fails;
  - a system without dark tokens: the manifest says light only, and the mockup stays light;
  - a proprietary font: the tokens use the system stack and the manifest names the substitution;
  - a copied class drifts from the reference: criterion 2 fails before a mockup uses it.
- Data and states: five files per system; light and dark tokens where upstream defines them; no runtime state.
- Limits: five systems; ≤900 lines of CSS+HTML each; MIT or Apache-2.0; no JS, build, npm or remote URL.

Flow: not needed: this work adds static CSS/HTML files and a validation rule; there is no runtime branch or three-party interaction to draw.

## Out of scope

- Migrating mockups already built on the old two systems (none shipped).
- React/Tailwind packaging of the real libraries.
- Copying fonts or imagery.
- An automated upstream sync; the library is a curated snapshot with a date.

## Open questions

None.
