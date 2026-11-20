# Eval case 1 — a four-stage flow

**Task (what you say to a fresh agent):**

> Build a clickable mockup from this flow for a small B2B product, using /mockup:
> 1. Sign up with work email.
> 2. Connect one data source and see it sync.
> 3. Generate a weekly report and approve it.
> 4. Hit the free plan limit and upgrade.
> Show every screen in a gallery, with a mobile frame, light and dark, and hover/loading states. Put it in /tmp/mockup-eval.

**Expect (check without reading the code):**

- `index.html` opens over `file://` and the first screen is a gallery listing at least 4 screens.
- Each card has Open and Mobile; both open the screen (hash route), and the chrome shows the screen name.
- `node check.mjs` exits 0 and covers routes, theme persistence after reload, hover colour + font weight, a loading → complete action, no horizontal overflow at 390, 0 console errors, reduced motion.
- The flow stages map 1:1 to screens, or the missing stage is named as intentionally omitted.
- No invented numbers, testimonials or "live" counts; demo data is labelled.

Record in the feedback log: which steps the fresh agent missed, how many places you fixed by hand, and update this case if the flow stops matching the skill.
