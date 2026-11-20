---
status: verified (plan accepted by the owner, 2026-11-20: "To T1") # draft → planned → building → verified
---
# Plan: spec quality in /sdlc (APS-82)

Intent: `intent/2026-11-20-spec-quality.md`. Ticket: Plane APS-82. All work is HARD here: the main session builds it, and the hard-reviewer reviews it.

## Files
1. `scripts/sdlc-check.py`:
   - `clarify` takes the intent's path, and checks the `## Coverage` bullets, the `Flow:` line and the flow files;
   - `converge` traces the plan's Proof items to the intent's Outcome items;
   - the docstring and the self-tests change to match.
2. `skills/sdlc/SKILL.md`:
   - Phase 1: the template with `## Coverage` and the `Flow:` line; when a flow is needed and how to draw it; the fresh-reader step and its fixed prompt; what to leave out; what `clarify` now checks.
   - Phase 2: Proof items name `(On)`.
   - Phase 4: `converge` traces Outcome items to Proof items.
3. `rores/global/CLAUDE.md`: the Tools line for `ambysto-graph` names the flow commands.
4. `docs/internals.md`, `README.md`: the `sdlc-check.py` rows.
5. `intent/2026-11-20-spec-quality.*.flow.*`: this intent's flow, re-rendered if the JSON changes.

## Design
- **Coverage.**
  - `## Coverage` holds top-level bullets `- <Label>: <text>`. Indented lines under a bullet belong to it.
  - The six labels are exact: `Who`, `Trigger`, `Main path`, `Branches and failures`, `Data and states`, `Limits`.
  - A bullet is empty when its text, with a leading `N/A:` removed, is blank or only `N/A`, `TBD` or `?` (any case). A bare `N/A` with no reason is empty.
  - A label given twice is a gap. Other bullets are allowed.
- **The `Flow:` line.**
  - It is exactly one line, outside code fences, that starts `Flow: `.
  - `not needed: <reason>` needs a non-empty reason.
  - Any other text must name one or more files in backticks, matching `<intent stem>.<name>.flow.json`, with no `/`, so a name cannot point outside the intent's folder.
  - Every `<intent stem>.*.flow.json` in the folder must be named.
- **The flow tool.**
  - `ambysto-graph` from `PATH`; otherwise `~/.claude/skills/graph/scripts/graph.py` run with the same Python; otherwise none.
  - Each named file runs `validate <file>`. A non-zero exit is a gap, with the tool's first error lines.
  - Then `render <file> -o <temp>` with no other flag. A missing `.flow.html`, or bytes that differ, is a gap. The gap gives the command that renders it again.
  - Each tool call has a 60 s timeout.
  - With no tool, the note `flows not checked: no flow tool installed` is printed and PASS stays PASS. The note is never a check.
  - Rendering twice, from two different folders, was measured to give identical bytes (sha256 13cf08d9…).
- **The tracing.**
  - `converge` finds the intent as it does today: the plan's name without `.plan`.
  - When that intent has `## Coverage`:
    - the Outcome items are the top-level numbered lines (`numbered()`, column 0);
    - each Proof item's first line may hold `(O1, O3)`;
    - an Outcome item that no Proof item names is a gap;
    - a name with no matching Outcome item is a gap.
  - With no intent, or an intent without `## Coverage`, it prints the note `<intent>: no ## Coverage; Outcome items not traced`.
- **The intent's flows are the plan's own** (added during the build): `converge` counts `<intent stem>.*.flow.json` and `.flow.html` beside the intent with the plan and the intent, so no task has to allow them; another intent's flows still need a task.
- **Hard-review round 1 fixes** (added during the build):
  - **Flow names.** A flow file belongs to the longest intent stem it extends.
  - **`not needed`.** A `not needed` line that names a flow fails.
  - **Links.** A flow that is a link fails.
  - **Line endings.** The HTML is compared with CRLF read as LF.
  - **Empty bullets.** `N/A.`, `TBD.` and empty sub-bullets count as empty.
- **Hard-review round 2 fixes** (added during the build):
  - **HTML links.** The `.flow.html` link check names the right file.
  - **Names given twice.** A flow named twice is checked once.
  - **Older intents.** The round-1 exception for intents approved before Coverage was dropped, by owner decision after round 2: an approved intent without Coverage fails `clarify` like any other.
- **The fresh-reader prompt** sits in the skill word for word. It is the prompt this intent's trial used (PR #79), with the file paths left blank.
- The skill stays universal. It calls the tool "the flow tool your global instructions name, or the `graph` skill". Only `sdlc-check.py` and the global block name `ambysto-graph`.

## Risks
- **A running one-prompt loop on an old plan suddenly fails `converge`.**
  - Tracing applies only when the intent has `## Coverage`.
  - Check: Proof 4 runs every existing plan through the old and the new `converge` and compares the results.
- **A false "stale" HTML fails `clarify`.** This happens when the flow was rendered by the other tool (the Python skill draws different HTML) or with a theme flag.
  - The gap names the exact command that renders it again.
  - The skill says to render with the same tool, with no flags.
  - Check: a self-test case.
- **A flow name pointing outside the folder runs the tool on another file.**
  - Names with `/` and names not matching the stem are refused.
  - Check: a self-test case.
- **No flow tool installed is read as checked.**
  - With no tool, a note is printed and the check is never reported as passed.
  - Check: a self-test with an empty `PATH` and HOME.
- **The tool hangs.**
  - Each call has a 60 s timeout, and a timeout is a gap.
  - Check: a self-test with a fake tool that sleeps, at a short timeout.
- **The skill becomes too long for a session to follow.**
  - Check: the fresh agent in Proof 7 runs the whole new Phase 1, and the PR records each place it had to guess.
- **The public copy drifts.**
  - After the merge, `sync-public.py`, as this repo's Rules say.

## Tasks

### T1 (main) clarify checks Coverage and flows; converge traces Outcome to Proof
- allow: `scripts/sdlc-check.py`
- check: `python3 scripts/sdlc-check.py --self-test`
- check: `systemd-run --user --scope -q -p MemoryMax=4G python3 scripts/check.py`

### T2 (main) The sdlc skill, the global Tools line, and this intent's flow
- allow: `skills/sdlc/SKILL.md` `rores/global/CLAUDE.md` `intent/2026-11-20-spec-quality.*.flow.json` `intent/2026-11-20-spec-quality.*.flow.html`
- check: `python3 scripts/sdlc-check.py clarify intent/2026-11-20-spec-quality.md`
- check: `systemd-run --user --scope -q -p MemoryMax=4G python3 scripts/check.py`

### T3 (main) Docs
- allow: `docs/internals.md` `README.md`
- check: `systemd-run --user --scope -q -p MemoryMax=4G python3 scripts/check.py`

## Proof

1. `python3 scripts/sdlc-check.py clarify intent/2026-11-20-spec-quality.md` passes with the new checks: the Coverage bullets, the `Flow:` line, the flow validated, and the HTML equal to a fresh render. (O1, O2)
2. `python3 scripts/sdlc-check.py --self-test` passes, with a case for each new refusal. (O1, O2, O4)
   - Coverage: missing, a label missing, a label twice, empty, bare `N/A`, `TBD`.
   - Flow: the line missing or given twice, `not needed` without a reason, a name with `/`, a named file missing, an unnamed flow file, a validate error, the HTML missing or stale, a tool timeout, no tool (a note and PASS).
   - Tracing: an untraced Outcome item, an unknown `On`, an intent without Coverage passing.
3. Each new refusal is mutated, and the self-test catches every mutation (lesson `mutation-check-self-tests`). The count goes in the result. (O1, O2, O4)
4. Every existing `intent/*.plan.md` gives the same `converge` verdict and gaps with the script on `main` as with this branch's script. (O4)
5. `systemd-run --user --scope -q -p MemoryMax=4G python3 scripts/check.py` passes.
6. `HOME=$(mktemp -d) python3 scripts/install.py --global --settings`, then `--check` under the same `HOME`, exits 0. In that HOME, the installed global block's Tools line names the flow commands. (O6)
7. A fresh agent given only the new `skills/sdlc/SKILL.md` writes an intent and a plan, on a scratch repo, for a small feature with a branch. (O1, O2, O3, O5)
   - Expected: the six Coverage bullets, a flow that validates, its `Flow:` line, the fresh-reader step run and its lists recorded, Proof items with `(On)`, and `clarify` and `converge` passing.
   - The PR records each place it had to guess.
8. `python3 scripts/sdlc-check.py converge intent/2026-11-20-spec-quality.plan.md --checks` passes, including this plan's own tracing. (O4)
9. The hard-reviewer returns PASS. (O1, O2, O3, O4, O5, O6)

## Result

1. PASS: `clarify intent/2026-11-20-spec-quality.md`, 0 gap(s); note "flow `2026-11-20-spec-quality.phase1.flow.json`: valid, and `….phase1.flow.html` is its fresh render" (ambysto-graph).
2. PASS: `sdlc-check.py --self-test`, after the hard-review round-1 and round-2 fixes. It has a case for each new refusal:
   - Coverage: the section missing, a label missing, a label twice, a bullet inside a fence, an unindented line ending a bullet, and 10 empty forms (blank, `N/A`, `TBD`, `?`, `N/A:`, `n/a: tbd`, `N/A.`, `TBD.`, a `TBD` sub-bullet, `?`/`N/A` sub-bullets); a real sub-bullet counts as content.
   - An approved intent without Coverage fails like any other (the round-1 exception for older intents was dropped, owner decision 2026-11-20).
   - Flow names: the line missing, given twice or fenced; `not needed` without a reason; `not needed` naming a flow (the flow is then both flagged and listed as not named); no name; a name outside the folder; a slash or a backslash under the stem; an empty or dot-led middle; a longer different stem; another intent's name; a link, and an HTML that is a link (an unrelated `.html` link is not the flow's); a name given twice (checked once); a plan file is not an intent that owns flows; a named file missing; a file not named; a longer intent's flows belonging to it.
   - Flow checks: a validate error, a render failure, the HTML missing, stale, or CRLF-equal (passes), a tool timeout, and no tool (a note, PASS); `flow_tool` returns None on an empty PATH, HOME and USERPROFILE (the variables are restored, unset ones too); the CLI `clarify`, and the CLI finding the flow tool: a fake `ambysto-graph` on a scratch PATH, a fake graph skill under a scratch HOME, and neither (a note).
   - Tracing: clean, an untraced outcome, an unknown outcome, Coverage without numbered outcomes, an old intent (a note).
   - `converge`: the intent's flows count as the plan's own, while another intent's flows, including a longer stem's, and a same-named flow in another folder, do not.
3. PASS: 47 of 47 mutations caught, one per refusal or rule (`scratchpad/mut2.py`, each run in a scratch copy).
   - Round 1 claimed 20 of 20, but the hard-reviewer found 7 mutations its cases missed (the stem prefix, the render failure, the backslash, the empty or dot middle, the Coverage fence, the unindented line, and `not needed` naming a flow). Each now has a case.
   - Round 2 found 6 more:
     - the `.flow.html` link check named the wrong file, and is now fixed;
     - the CLI's tool discovery could be broken in 3 ways unseen;
     - the folder compare in converge's ownership;
     - the `.plan.md` exclusion.
     Each now has a case, and the hard-reviewer's own `mutate2.py` probes are caught too.
   - The explicit slash and backslash test was redundant with `flow_owner`'s name pattern, so it was removed; the pattern is what gets mutated now.
4. PASS: all 17 existing plans give the same `converge` gap lines, verdict and exit code with `main`'s script (81a4137) and this branch's (re-run after the round-2 fixes).
   - `clarify` on the older intents differs, as decided. 14 of the 22 pass `main`'s `clarify`; none pass the new one, because they have no Coverage or `Flow:` line.
   - The owner chose this on 2026-11-20 after round 2, instead of an exception for older intents. `clarify` is run only before approval, and no approved intent here is waiting for its plan.
5. PASS: `check.py` (4 agents pinned, reviewer bodies equal, hooks self-tested, 9 skills valid, settings defaults valid), re-run after the round-1 fixes.
   - The first run failed in the progress-diagram self-test, because ambysto-graph refuses `mode: workflow` since the flow IR.
   - APS-83 fixed that separately (PR #80, merged 81a4137), and this branch is up to date with it.
6. PASS: `HOME=$(mktemp -d)` `install.py --global --settings` exit 0, then `--check` exit 0. The installed global block has the `validate <ir>.json` Tools text, and the installed sdlc skill has the fresh-reader step.
7. PASS: a fresh agent had only the new skill (copied to a scratch folder) and a scratch Flask repo, with the request "reset a forgotten password by email". (O1, O2, O3, O5)
   - **What it produced.** The six Coverage bullets, a `workflow` user flow and a `sequence` calls flow (both valid), and the `Flow:` line. `clarify` PASS, with both flows "valid, fresh render". It wrote a plan whose 9 of 10 Proof items name Outcome items. `converge --base main` gave no tracing gap; its only gaps were that no code is built yet.
   - **Tracing works on its plan.** Removing `(O3)` from its plan gives "outcome 3 is named by no Proof item".
   - **The fresh reader.** Run on the builder's model over the agent's intent and flows, it found 10 guesses that `clarify` cannot see: case-insensitive email matching, response timing for unknown addresses, whether the rate limit counts failed sends, a sliding or fixed hour, and others. It also found 4 cuts and 4 HOW items.
   - **Where the agent guessed in Phase 1, and the fixes made to the skill:**
     - where the answers go: written into the intent where they apply;
     - "render with no flags": only `-o`;
     - when one flow is enough;
     - `external` in a workflow: it applies only to sequence participants.
   - **Where it guessed in Phase 2.** "Each item names" wrongly implied that every Proof item must name one. The skill now says an item that proves none names none. Its other Phase 2 guesses are about text this change did not touch: the plan's status-line format, who accepts the plan, and `forbid`. They are left as they are.
8. PASS: `converge intent/2026-11-20-spec-quality.plan.md --checks`, 0 gap(s). This plan's own Proof items trace all six Outcome items, and each task's `check:` commands passed.
9. PASS: hard-reviewer, round 3: no BLOCKER, no MAJOR, 3 MINOR. Round 1 FAILed (2 MAJOR, 5 MINOR) and round 2 FAILed (2 MAJOR, 3 MINOR); the owner chose a third round. The round-3 MINORs are left as they are and named in the PR:
   - `flow_tool`'s order (`ambysto-graph` before the graph skill) has no case with both present;
   - an older approved intent now fails `clarify` if it is planned after the merge (none is waiting);
   - `- Limits: 1. TBD` reads as empty.
