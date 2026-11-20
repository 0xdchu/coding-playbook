---
status: verified
planned: 2026-11-20 (owner, "đủ 5 bộ CSS thuần")
---
# Plan — six design systems (shadcn, Radix, Open Props, Fluent, Carbon, Flex-style)

## Files

1. `design-systems/README.md` — the five-file contract, the five systems, licence and copy rules.
2. `design-systems/shadcn/{manifest.json,tokens.css,components.css,reference.html,LICENSE}`.
3. `design-systems/radix/{manifest.json,tokens.css,components.css,reference.html,LICENSE}`.
4. `design-systems/open-props/{manifest.json,tokens.css,components.css,reference.html,LICENSE}`.
5. `design-systems/fluent/{manifest.json,tokens.css,components.css,reference.html,LICENSE}`.
6. `design-systems/carbon/{manifest.json,tokens.css,components.css,reference.html,LICENSE}`.
7. `design-systems/flex/{manifest.json,tokens.css,components.css,reference.html,LICENSE}` — original interpretation.
8. `design-systems/govuk/`, `design-systems/primer/` — removed.
9. `scripts/check.py` — required folders become shadcn/radix/open-props/fluent/carbon/flex.
10. `skills/mockup/SKILL.md` — step 2 names the six systems and their uses.
11. `skills/mockup/template/README.md` — the copy rule, six systems.
12. `README.md` — repo section names the six systems.

## Risks

| Risk | Catch |
|---|---|
| A modern library is React/Sass, so the components are a look-alike | manifest says "official tokens, curated components"; review checks values against the source |
| A licence text is missing or a font is bundled | `check.py` requires LICENSE; review checks font stacks |
| A manifest class is absent from the reference | `check.py` matches `class="..."` tokens |
| A reference breaks at 390 | headless render at 1440 and 390, no overflow, 0 console errors |
| The old folders survive | `check.py` requires exactly the five and fails on govuk/primer |

## Tasks

### T1 (main) shadcn + Radix
- allow: `design-systems/shadcn/**` `design-systems/radix/**`
- check: `python3 -c "import json;[json.load(open(f'design-systems/{n}/manifest.json')) for n in ('shadcn','radix')]"`
- check: `test -s design-systems/shadcn/LICENSE && test -s design-systems/radix/LICENSE`

### T2 (main) Open Props + Fluent + Carbon + Flex
- allow: `design-systems/open-props/**` `design-systems/fluent/**` `design-systems/carbon/**` `design-systems/flex/**`
- check: `python3 -c "import json;[json.load(open(f'design-systems/{n}/manifest.json')) for n in ('open-props','fluent','carbon','flex')]"`
- check: `test -s design-systems/carbon/LICENSE && test -s design-systems/flex/LICENSE`

### T3 (main) Remove old folders + validation
- allow: `scripts/check.py` `design-systems/govuk/**` `design-systems/primer/**`
- check: `python3 scripts/check.py`

### T4 (main) Skill + template docs
- allow: `skills/mockup/SKILL.md` `skills/mockup/template/README.md`
- check: `python3 -c "import yaml;yaml.safe_load(open('skills/mockup/SKILL.md').read().split('---')[1])"`

### T5 (main) README + reference proof
- allow: `design-systems/README.md` `README.md`
- check: `test -s design-systems/README.md`

## Proof

1. `python3 scripts/check.py` PASS, six systems validated, `govuk`/`primer` absent. (O1, O2)
2. Headless render all six `reference.html` at 1440×900 and 390×844: 0 console errors, no horizontal overflow. (O3)
3. `python3 scripts/sdlc-check.py converge intent/2026-11-20-design-systems-library.plan.md` 0 gap.
4. `skills/mockup/SKILL.md` step 2 names shadcn/Radix/Open Props/Fluent/Carbon/Flex; `wc -l` per system ≤900. (O4, O5)

## Result

1. PASS — `python3 scripts/check.py` exits 0: the six folders validated (five files, manifest keys, manifest↔reference classes), `govuk`/`primer` absent, 12 skills valid.
2. PASS — all six `reference.html` at 1440×900 and 390×844: 0 console errors, 0 horizontal overflow; screenshots inspected (light and dark panels, and the Flex hero/cream/dark sections).
3. PASS — `converge`: 0 gap.
4. PASS — `skills/mockup/SKILL.md` step 2 names shadcn, Radix, Open Props, Fluent, Carbon and Flex and the copy rule; `template/README.md` repeats it; 1,199 lines of CSS+HTML total, largest system 277 lines (Radix), under the 900 limit.

Review: the five-system pass drew an independent reviewer FAIL; all five MAJOR and three MINOR issues were fixed before this result — shadcn dark heading colour, exact-five folder check, Carbon g90 on-colour/interactive tokens and focus ring, tokens-only labelling for Open Props and Radix, destructive hover, missing-file guard, Carbon token drift (green, layer-3, blue-hover, danger, focus-inset).

The `flex/` system was added after that review as an original interpretation of flex.one: no site HTML, CSS, fonts
or images are used, the LICENSE says so, and the same file/class checks cover it; its reference was inspected at
1440 and 390.
