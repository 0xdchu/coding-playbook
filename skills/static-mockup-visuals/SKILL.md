---
name: static-mockup-visuals
description: Create or edit the visual composition of a single-screen static website mockup in code, including hero art placement, layering, cards, spacing, and responsive framing. Use when saying “adjust this hero mockup”, “move the existing mascot”, “arrange the post cards”, “make the static mockup fit 9:16”, or “render the landing mockup on mobile”. Don’t use for clickable multi-screen prototypes, production app changes, or standalone image generation without mockup placement.
---

# /static-mockup-visuals

Make the requested visual change to a static page while preserving the rest of the mockup. Input is an existing page, source material, or a screenshot with instructions; output is the smallest code or asset change that renders correctly at the requested screen sizes.

## When to use

- A landing page, homepage, or feature mockup needs one hero or section composed or adjusted.
- The request changes position, size, order, overlap, spacing, framing, or a few visual elements in an existing static page.
- A screenshot needs to be translated into a static page view for visual review.

## Don’t use when

- The request is for a clickable multi-screen prototype from a flow; use the interactive mockup workflow.
- The request is only for a standalone image with no page placement; use an image-generation workflow.
- The request changes production behavior, data, or application logic.
- The user asks for review only and no implementation.

## Read first

1. The open repository’s `AGENTS.md`, `CLAUDE.md`, or equivalent local instructions.
2. The target page source, its styles, existing assets, and any available brand or design rules.
3. The user’s screenshots and the full conversation for explicit constraints and corrections.

## Steps

### 1. Turn the request into a small change contract
- Do: list the exact elements and properties the user asked to change, the target screen sizes, and what must stay as it is. Treat examples and references as guidance only where the user says so.
- Do: distinguish moving an element from resizing it, replacing it, or rebuilding its section. Preserve its size and content unless asked to change them. Treat phrases such as “a few” as a small minority of the available items; ask for a count only when it changes the meaning or layout.
- Do: ask only when missing information changes the result materially; use clear instructions already present in the conversation.
- Done when: every planned edit maps to an explicit request and the untouched items are named.

### 2. Inspect and capture the starting point
- Do: confirm the target page and record any pre-existing working-tree changes before editing. Keep that baseline separate from the task diff; do not stage or revert existing user work. Inspect the existing components and assets, then render a baseline at the requested viewport sizes. If no sizes are specified, use 1440×900 desktop and 390×844 mobile. For an explicitly requested 9:16 frame, render at the user’s exact size or a matching 9:16 viewport.
- Do: identify whether the request concerns code layout, an existing image, or a new bitmap asset.
- Done when: the current layout and the exact edit location are visible in source and baseline screenshots.

### 3. Use the smallest suitable implementation
- Do: change position, overlap, order, spacing, grid shape, or framing in the existing HTML/CSS/SVG. Keep text, components, assets, and adjacent sections intact unless requested.
- Do: use an image-generation tool only when the user asks for new or edited bitmap art, or when a new bitmap is necessary to meet the request. Follow repository brand and image-source rules, and inspect the result at its rendered size.
- Do: use clean, official-quality source assets when the user requests platform logos; never substitute emoji, approximate marks, or blurry screenshots. If no logo is requested, don’t add one as decoration.
- Done when: only the requested elements changed, and responsive layout rules keep the composition within its frame.

### 4. Render and compare before calling it done
- Do: render the exact desktop and mobile viewports from the contract. Compare the result with the request and the baseline.
- Do: check the named positions and alignments, visible text, image bounds, stacking order, and overflow. Make sure overlaps do not obscure copy and a requested full character or card is not clipped.
- Do: inspect every touched viewport after each visual adjustment; source-code inspection alone does not prove placement.
- Done when: all explicit visual requirements pass in screenshots, no requested content is hidden or clipped, and unrelated sections still match the baseline.

### 5. Stop at the requested boundary
- Do: review the diff and changed-file list against the recorded baseline. Remove only incidental edits that can be identified as introduced by this task; preserve any pre-existing or uncertain changes and report them. Share desktop and mobile screenshots with a concise file and worktree status.
- Do: commit, push, or deploy only when the user asks or an applicable repository instruction authorizes it.
- Done when: the result is reviewable and the report says whether it is local, committed, pushed, or deployed.

## Don’t

- Don’t treat a request to move an element as permission to redesign the hero or move its containing block.
- Don’t add cards, platforms, logos, connectors, copy, numbers, badges, or decoration unless requested.
- Don’t resize or redraw an existing character for a position-only change.
- Don’t replace code-based UI with a single generated screenshot; text and controls must remain crisp and separately editable.
- Don’t claim visual alignment or responsive fit without rendering the target sizes.
- Don’t modify neighboring sections to make the requested section appear more complete.

## Done when

- Every planned change maps to the request; no unrequested additions or adjacent-section edits remain.
- The exact desktop and mobile screenshots show the requested layout with all required text and artwork visible and no unintended clipping or overflow.
- The user can review the screenshot files and knows the repository and publication status.

## Eval

| Metric | How to measure | Target |
|---|---|---|
| Scope fidelity | Compare changed elements and files with the request contract | 0 unrequested changes |
| Visual accuracy | Check each explicit position, size, order, and visibility condition in rendered screenshots | All pass |
| Mobile frame fit | Inspect the exact requested mobile aspect and dimensions for clipping and overflow | 0 failures |
| User correction count | Count scope or visual corrections needed after the first review | Trending down to 0 |

## Feedback log

| Date | What happened | What changed |
|---|---|---|
| 23/11/2026 | A fresh-agent trial changed only the static hero calendar to 4×3, removed logos, and tinted four cells; both 1440×900 and 390×693 renders were inspected | Passed with no extra edits; clarified that “a few” means a small minority, not a fixed count |
