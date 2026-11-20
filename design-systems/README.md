# Design-system library

Five modern systems, packaged so the `mockup` skill (or a person) can copy one in a single step and an LLM can
read it once. Plain CSS variables and classes; no JS, no build, no npm.

## The five-file contract

Every system folder holds exactly:

```
<system>/
  manifest.json     name, source, version, date, license, font, accent, dark, components[]
  tokens.css        colours, type scale, spacing, radius as CSS variables
  components.css    the curated components, plain classes
  reference.html    every component and state on one page
  LICENSE           the upstream licence text
```

`scripts/check.py` fails when a file is missing, a manifest is invalid, or a class named in `components[]` does not
appear in a `class="..."` attribute in `reference.html`.

## The five systems

| Folder | Source | Use it for | Dark | Licence |
|---|---|---|---|---|
| `shadcn/` | shadcn/ui default theme | modern SaaS, dashboards, marketing-adjacent product UI | yes | MIT |
| `radix/` | Radix Colors 3.x + Themes patterns | apps that want the Radix Themes look (soft accents, 6px radius) | yes | MIT |
| `open-props/` | Open Props 1.7.23 | playful, young products; tokens only, components are recipes | no | MIT |
| `fluent/` | Microsoft Fluent 2 tokens | Microsoft-style productivity apps, dense forms | yes | MIT |
| `carbon/` | IBM Carbon 11 | enterprise, data-dense consoles; square, accessible | yes | Apache-2.0 |
| `flex/` | flex.one (visual reference) | luxury, private banking, editorial | yes | Original MIT (no site code or assets copied) |

Choose by the work, not by taste: shadcn for a modern SaaS, Carbon for an enterprise console, Open Props for a
playful landing-adjacent app, Fluent for a Microsoft-shaped product.

## Rules

- **Copy, do not link.** The mockup copies `tokens.css` and `components.css` into its own folder and links them
  before its `styles.css`, so the page keeps working over `file://` and offline.
- **Official tokens, curated components.** Colour/type/spacing values come from the upstream package or theme;
  the components are plain-CSS recipes in the same visual language because the real libraries are React/Sass.
- **Never copy a proprietary font.** Fluent uses the Segoe UI stack, Carbon the IBM Plex Sans stack (optional);
  nothing is bundled.
- **Name the source and date in the manifest.** The library is a snapshot; re-read the upstream before trusting a
  value months later.
- **Only upstream components, or a documented recipe.** Open Props and Radix Colors ship tokens, not
  components; their folders say `kind: tokens-only` / `tokens+recipes`, and the recipes are built from the official
  tokens. `flex/` is an original interpretation of a proprietary site (`kind: inspired-recipe`): no HTML, CSS, fonts
  or images from it are copied, and the folder's LICENSE says so.

## Add a system

1. Copy the five-file shape from an existing folder.
2. Record `source`, `version` and `date` in `manifest.json`; copy the upstream LICENSE.
3. Curate tokens first, then components; every class in `components[]` must appear in `reference.html`.
4. Run `python3 scripts/check.py` and open `reference.html` at 1440 and 390.
