---
status: shipped (PR #86) # draft → approved → planned → building → verified → shipped (PR #n)
---
# system-map: a committed map of a repo, drawn as Architecture, Docs and Runtime Flow views, kept current by converge

Ticket: Plane APS-88.

## Problem
1. **No picture of a whole system that a reader can trust.**
   - `ambysto-graph render --auto` draws code structure only: clusters named after folders, with no domains and no line saying why a part exists.
   - A diagram an agent writes by hand is checked by nobody. It can name code that does not exist and leave parts out.
2. **Pictures go stale.** Nothing tells a session that the code changed under a diagram, so a picture that was right last month is trusted after it stopped being right.
3. **Docs and diagrams drift apart.** A prose architecture doc and a diagram drawn beside it are two things to keep in step, and only one of them gets updated.

## Outcome
1. **A skill, `system-map`, writes a repo's map under `docs/map/`.**
   - The map has one JSON file per view. Each file is the source of truth for its view and is committed with its rendered HTML.
   - The views:
     - **Architecture:** the system's parts grouped by domain, each with one line saying why it exists; the outside services the system uses; the links between parts, each labelled.
     - **Docs:** the repo's documents and the code files that are a source of truth. Each has one mark, its main role: source of truth, derived, internal or schema. The links between them are labelled (generates, documented by, defers to).
     - **Runtime flow:** one flow IR `sequence` per request or command path the owner names.
   - The Architecture view is always drawn. The Docs or Runtime flow view may instead be recorded in `docs/map/` as `not needed: <reason>`, with no JSON or HTML file, for example a runtime flow in a library with no request path.
   - The list of code files left out (Outcome 3) is also kept in `docs/map/`.
2. **Every citation in a map is checked.**
   - Every part, document and step cites the code or text it stands for: a file, a line or line range, and the name of what it cites.
   - `ambysto-graph validate --repo-root <repo>` passes on every view: no citation names a missing file or a line out of range.
3. **Coverage.**
   - Every file that `ambysto-graph overview` counts as parsed code (whatever languages it supports) is cited by a part of the Architecture view, or named in the list of files left out, with a reason.
   - Every entrypoint `overview` lists is cited.
4. **A freshness check.** A command in this repo (`ambysto-graph` itself is not changed) lists, for a repo with `docs/map/`:
   - each validation error;
   - each citation whose cited line range no longer contains, as exact text, the name it gives (the code moved);
   - each code file that is neither cited nor left out;
   - each HTML file that is not a fresh render of its JSON, by the same rule `clarify` uses for an intent's flows.

   It uses no LLM, and exits non-zero when it lists anything.
5. **`converge` keeps the map current.**
   - In a repo with `docs/map/`, when the branch changes any file besides the plan and its intent (files under `docs/map/` count), `converge` runs the freshness check, against the same base it already uses. Each item it lists is a gap, so the plan fails until the map is updated on the same branch.
   - With no flow tool installed, `converge` says the map was not checked, never reports it as checked, and does not fail on it.
6. **The skill's steps.**
   - Get the skeleton from the flow tool (no LLM tokens).
   - Read the repo's intents, docs and `CLAUDE.md`.
   - Ask the owner 3 to 5 questions, each with a best guess: the domains, what is a source of truth, which runtime paths to draw.
   - Write the views and run the freshness check.
   - Run a fresh reader on the map, and settle each point it had to guess.
   - Get the owner's approval, then commit the map in its own PR.
   - To update a map: the same steps, starting from the items the check lists.
7. **Without `ambysto-graph`,** the skill says that the Architecture and Docs views and the checks need it. It draws only the runtime flows, with the `graph` skill, into `docs/map/`, commits them in their own PR as on the main path, and never says a map was checked when it was not.
8. **Pilot.** The skill is run on this repo (coding-playbook) and its map is committed. The PR records where the agent had to guess, and the owner's verdict on whether the map is right.

## Constraints
- Standard-library Python only; no new dependency.
- **HARD here:** this adds a skill every session can follow and changes what `converge` fails on. The main session builds it; the hard-reviewer reviews it.
- The skill is universal (no project's paths or names), lives in this repo, and reaches the public copy through the usual sync.
- Existing plans in repos without `docs/map/` keep passing `converge` unchanged.

## Coverage
- Who: the main session running the skill; the owner, who answers its questions and approves the map; a fresh reader; the flow tool (`ambysto-graph`, or the `graph` skill for flows only); later sessions and reviewers who read the map; `converge`.
- Trigger: the owner asks for a map of a repo (`/system-map`, "draw the architecture"); `converge` at Verify in a repo that has `docs/map/`.
- Main path: skeleton → read intents and docs → questions → write the views → freshness check → fresh reader → owner approval → map PR → later plans: `converge` runs the check → the map is updated on the same branch.
- Branches and failures:
  - no `ambysto-graph`: runtime flows only, and the map is reported as not checked;
  - a citation names a missing file, a line out of range, or code that moved: the check lists it;
  - a code file is neither cited nor left out: the check lists it;
  - an HTML file is not a fresh render: the check lists it;
  - the owner rejects a grouping: the view is rewritten and checked again;
  - a view the repo has no use for: `not needed: <reason>`;
  - a repo without `docs/map/`: `converge` runs no map check.
- Data and states: `docs/map/` with one JSON and one HTML file per view; the list of files left out, with reasons; the check's list of items, which become `converge` gaps.
- Limits: the freshness check uses no LLM tokens. Writing or updating a map costs main-session tokens, once per map and once per update. One fresh-reader run per map draft.

Flow: `2026-11-20-system-map.skill.flow.json` (workflow, drawn from this intent alone, not checked against code).

## Out of scope
- Lanes in the flow IR, and one page that joins the views as tabs. These belong to a later `ambysto-graph` ticket, if the pilot shows they are needed.
- A data map or ERD view.
- Redrawing a map without a session: no hook rewrites `docs/map/` on its own.
- Checking an intent's flows against the built code.

## Open questions
None.
