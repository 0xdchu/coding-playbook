---
name: mockup
description: Build a clickable end-user mockup from a user flow, PRD or system architecture into a gallery that lists every screen, where each screen opens as a real page with hover and focus states, loading to complete states, web and mobile, light and dark, seeded demo data, and a Playwright check that proves the routes, states and overflow. Use when saying "build a mockup", "make a clickable prototype", "turn this user flow into screens", "mockup gallery", "prototype the app UI", "dựng mockup", "làm mockup", or when a user-flow or architecture artifact exists and the UI must be seen before code. Don't use when drawing a diagram or one-page explainer (use archify), when only reviewing an existing UI, or for a single static page with no interactions.
---

# /mockup

Turn a flow into something a person can click: a gallery of every screen, each opening as a real page.
Static HTML, no framework, no backend — the point is to see and approve the UI before code exists.

## When to use

- A user flow, PRD or architecture artifact exists and someone asks to "see it" as an app.
- A feature needs a clickable prototype for review, a demo, or a pricing/onboarding decision.
- You catch yourself rebuilding the same gallery + router + theme + check script a second time.

## Don't use when

- The ask is a diagram, flow chart or one-page explainer — use `archify`.
- The ask is to review an existing UI, not to build one.
- The work is one static page with no states, routes or interaction.
- The input is only a screenshot and no written flow. Ask for the flow in words or a URL first.

## Read first

1. The flow or architecture artifact (role × stage, or screen list). Name the source in the mockup README.
2. The product's existing design language (tokens, font, mascot or brand assets) if one exists.
3. `template/` in this skill: shell, tokens, router, state machine and `check.mjs`.

## Steps

### 1. List screens from the flow
- Do: one screen per role-stage where the user decides or acts; drop steps with no UI (emails, backend jobs). Group them (onboarding, core loop, billing, config, support — add or drop groups for this product).
- Done when: a table of `id · title · group · one-line purpose` exists, and every flow stage maps to a screen or is named as intentionally omitted.

### 2. Fix the design language
- Do: if the repo has `design-systems/`, pick one (shadcn for modern SaaS, Radix for app UI, Open Props for playful products, Fluent for Microsoft-style productivity, Carbon for enterprise consoles, Flex for luxury/private-banking editorial), then copy its `tokens.css` and `components.css` beside the mockup and link them before `styles.css`. Otherwise write tokens for light and dark: one accent colour, a heading face, and the asset rules (mascot size, background, one pose per screen). If the product has no brand, choose a neutral pair and say so.
- Done when: the copied system or `styles.css :root` holds every colour and font the screens use; no inline hex in screen markup.

### 3. Copy and rename the template
- Do: copy `template/` into the repo (`labs/app/`, `app-mockup/`, …), replace product name and copy placeholders.
- Do: the device frame is a 390px box inside the desktop viewport, so `@media` queries never fire inside it. Write mobile layout as `.device-mobile ...` rules (or container queries on an inner wrapper), and check at 390 for real.
- Done when: `index.html` opens over `file://` and the gallery renders without a server.

### 4. Write the demo seed
- Do: real-shaped copy for one example user, states included (`pending`, `approved`, `empty`). Seed the screen at the state where the flow **starts**, not after it — if a screen shows a connected source, either add the connect step or label the seed. Mark demo data in the README.
- Done when: `node -e "console.log(require('./data.js').screens.length)"` prints the screen count.

### 5. Render screens and the gallery
- Do: one render function per screen, registered in `RENDER`; one gallery card per screen, showing a live scaled thumbnail and Open/Mobile links. States (empty, loading, complete) live inside the screen and are reached by clicking, not as extra cards. No element `id`s inside screens — thumbnails render them more than once. Never wrap a whole screen or preview in an `<a>`; screens already contain links and buttons.
- Done when: every screen opens from the gallery, and the thumbnail matches the page.

### 6. Wire interactions and states
- Do: router, theme persistence, web/mobile toggle, and one state machine per async action (`idle → loading → complete`, plus error where real). Hover and keyboard focus must both be visible; hover changes colour and font weight.
- Done when: generate/approve/save show a spinner or skeleton, then a success state, without reload.

### 7. Prove and deploy
- Do: run `check.mjs`; rewrite its screen ids and selectors for the real screens while keeping each assertion's intent (a counter or list changes, a route renders, theme persists), adapting direction to the flow, then fix until 0 fail.
- Do: deploy only when a repo and target (Vercel/project, Pages) are given: static, root = the folder, build/install empty, output `.`, noindex header. Otherwise a green local check is done.
- Done when: `node check.mjs` exits 0, and if deployed the live URL returns 200 with the full gallery of cards.

## Don't

- Never invent testimonials, user counts, ratings or "live" numbers. Demo copy is labelled demo.
- Never describe a trade-secret mechanism in UI copy; show the surface, not the internals.
- Never add a backend, auth, analytics or a CDN script to a mockup unless asked.
- Never ship a page that only works at desktop width; 390 is part of done.
- Never call it done on screenshots alone; the check script is the proof.

## Done when

- `node check.mjs` exits 0 (routes, theme persistence, hover colour + weight, loading → complete, 1440/390 no overflow, 0 console errors).
- The gallery lists every screen, and each opens on web and mobile, light and dark.
- If deployed, the live URL is 200 and `X-Robots-Tag: noindex`.

## Eval

| Metric | How to measure | Target |
|---|---|---|
| Invoked at the right time | 5 should-invoke + 5 sound-alike-but-shouldn't phrases, count correct | ≥ 9/10 |
| Screen coverage | every stage of the source flow has a card and a route | 100% |
| Proof green | `node check.mjs` exit code | 0 every run |
| Hand fixes after the first build | count per run | down to 0 |

## Feedback log

| Date | What happened | What changed |
|---|---|---|
| 20/11/2026 | Trial 2, fresh agent on a 4-stage flow (8 screens): 53 pass, 0 fail; asked whether states get their own cards and how literal "keep every assertion" is | Step 5 one card per screen, states by click; Step 7 assertion intent; groups include billing |
| 20/11/2026 | Trial 1, fresh agent on a 4-stage flow (10 screens): 72 pass, 0 fail; guessed at mobile-frame media queries, check selectors, seed state | Added the 390px frame rule, check-selector step, seed-at-start rule, focus assertion, deploy scope |
| 20/11/2026 | Created from the aipub app mockup (11 screens, gallery + Vercel); trialed on that case | v1 |

## This skill must improve itself

1. **Eval after every run.** Grade the table; any missing step goes back into this file with one log row.
2. **Look things up occasionally.** Playwright launch flags, Vercel project settings and font URLs change.
3. **With a stronger model, rerun the trial.** Drop lines it no longer needs.
4. **When unsure, ask a human.**
