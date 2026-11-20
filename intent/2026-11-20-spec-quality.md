---
status: shipped (PR #79) # draft → approved → planned → building → verified → shipped (PR #n)
---
# Spec quality in /sdlc: a coverage list, a flow drawn from the intent, a fresh reader, and Outcome traced to Proof

Ticket: Plane APS-82.

## Problem
Phase 1 of `/sdlc` asks a few questions, fills a five-part template, and `sdlc-check.py clarify` fails while a `[NEEDS CLARIFICATION]` marker or an open question remains. That catches the gaps the writer knows about. Nothing catches the rest:
1. **A gap nobody marked.** A missing failure path, role, state or limit leaves no marker, so `clarify` passes and the gap reaches the plan or the code.
2. **Only the writer and the owner read the intent before the plan.** Both know the chat; a builder reads only the files, and has to guess what the text leaves out.
3. **An Outcome item can have no Proof.** `converge` checks that every Proof item has a Result. It does not check that every Outcome item is proven by some Proof item.
4. **No rule for what to leave out.** HOW details end up in the intent, and lines that change no decision and no test make it longer without making it clearer.

The flow validator (`ambysto-graph`, and the public `graph` skill) already refuses the shapes a forgotten path leaves, such as a decision with one exit or a node nothing reaches.

## Outcome
1. **Coverage list.**
   - The intent template has a `## Coverage` section with six bullets, `- <Label>: <text>`:
     - **Who**: the people, roles and systems involved;
     - **Trigger**: what starts each use;
     - **Main path**;
     - **Branches and failures**: wrong input, denied or expired, an outside service down, nothing found, a repeat or a race;
     - **Data and states**;
     - **Limits**: size, time, cost, quotas.
   - Each bullet has content, or `N/A: <reason>`.
   - `clarify` fails when the section is missing, or when a bullet is missing or empty. A bare `N/A`, `TBD` or `?` counts as empty: an open point is a `[NEEDS CLARIFICATION]` marker.
2. **A flow drawn from the intent.**
   - An intent has one `Flow:` line. It either names its flow files or says `Flow: not needed: <reason>`.
   - A flow is needed when the work has:
     - a branch point, a place where it takes one of several paths with different outcomes (yes or no, success or failure); or
     - three or more parties that act on each other (people, roles, your own systems and outside services).
   - A flow file is `intent/<date>-<slug>.<name>.flow.json`: a user flow as `workflow`, a processing flow as `sequence`. Each is committed with its rendered `.flow.html`.
   - `clarify` fails when:
     - the `Flow:` line is missing;
     - a named file is missing;
     - a `<date>-<slug>.*.flow.json` next to the intent is not named;
     - a flow has a validation error;
     - a `.flow.html` is missing, or differs from a fresh render of its `.json`.
   - `clarify` uses the installed flow tool: `ambysto-graph` on `PATH`, otherwise the `graph` skill in the installed skills folder. With neither installed, it says the flows were not checked, and never reports them as checked.
   - Flows are drawn from the intent alone, without `--repo-root`. The skill says they were not checked against code.
3. **A fresh reader before approval.**
   - Before the owner is asked to approve an intent, the main session runs one fresh agent on the builder's model. The agent is given only the intent and its flow files, with a fixed prompt written in the skill. It returns three lists:
     - the points it had to guess to build or test the work;
     - the lines that change no decision and no test;
     - the HOW details that belong in the plan.
   - Each item ends as a question to the owner, a clearer line, or a cut.
   - The intent's own PR (an intent always goes up as its own PR) records the lists and what became of each item.
4. **Outcome traced to Proof.**
   - Applies to an intent with `## Coverage`.
   - A Proof item in its plan's `## Proof` names the top-level Outcome items it proves, as `(O1, O3)`. A Proof item may name several Outcome items, or none.
   - `converge` fails when a top-level Outcome item is named by no Proof item, or when a Proof item names an Outcome item that does not exist.
   - An intent without `## Coverage` (written before this change) is reported, and passes.
5. **What to leave out.** The skill says the intent states WHAT, never HOW, and that every line should change a decision or a test. The fresh reader's second and third lists are where the cuts come from.
6. **The global block's Tools line** names the flow commands (`ambysto-graph validate` and `render` on a flow IR). A session skips the tool when `command -v` does not find it.

## Constraints
- Standard-library Python only; no new dependency.
- **HARD here:** this changes the steps of a skill every session follows, the global block, and the parser behind `converge`. The main session builds it; the hard-reviewer reviews it.
- **Proof:**
  - `check.py` self-tests prove each new refusal;
  - per this repo's Verify, a fresh agent runs the changed skill on a scratch repo, given only the skill, and the PR records where it had to guess.
- The skill stays universal, with no project's paths or names. The public copy gets the change through the usual sync.
- Existing plans keep passing `converge`. `clarify` is run only before an intent is approved, so intents already approved are not affected.

## Coverage
- Who: the main session writing an intent; the owner approving it; a builder and reviewer reading the plan later; the flow tool.
- Trigger: Phase 1 of `/sdlc` (a new intent), and `converge` at Verify.
- Main path: questions → intent with Coverage and its `Flow:` line → `clarify` → fresh reader → fixes → owner approval → plan with traced Proof → `converge`.
- Branches and failures:
  - no flow tool: the flows are reported unchecked;
  - a flow error, or a missing or stale `.flow.html`: `clarify` fails;
  - an intent without `## Coverage`: `converge` reports it and passes;
  - the fresh reader finds nothing: the PR says so;
  - a Proof item names an Outcome item that does not exist: `converge` fails.
- Data and states: intent files; `*.flow.json` and `*.flow.html` next to them; Proof lines with `(On)`.
- Limits: one fresh-reader run per intent draft, plus one more after large changes.

Flow: `2026-11-20-spec-quality.phase1.flow.json` (workflow, drawn from this intent alone, not checked against code).

## Out of scope
- Checking an intent's flow against the built code with `--repo-root`, to show what was not built. That is a later intent.
- Changes to the reviewer checklists, the task rating or the models.

## Open questions
None.
