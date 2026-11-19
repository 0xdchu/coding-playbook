---
status: building   # draft → planned → building → verified
---
# Plan: flow diagrams for the graph skill (`skills/graph/`)

Intent: `intent/2026-11-19-graph-flow-diagrams.md` (approved). Built here in standard-library Python. The Rust engine gets the same features under its own intent and plan in its own repo; this plan does not change it.

## Decisions this plan makes
- **The IR is the shared contract.** The JSON format below is written so the Rust engine can read the same files later; `SKILL.md` documents it as a format, not as this script's internals.
- **One skill folder, plain scripts.** `skills/graph/SKILL.md`, `skills/graph/scripts/*.py`, one HTML template, `examples/` and `tests/`. The installer already copies every file of `skills/<name>/` to `~/.claude/skills/<name>/`, so the skill runs as `python3 ~/.claude/skills/graph/scripts/graph.py …`.
- **CLI.** `graph.py validate <ir.json> [--repo-root <dir>] [--json]`, `graph.py render <ir.json> -o <out.html> [--repo-root <dir>] [--theme dark|light]` (render validates first and refuses an invalid diagram), `graph.py from-trace <trace.json> -o <ir.json>`, `graph.py --self-test`. Exit 0 valid or written, 1 invalid, 2 usage or refused.
- **IR** (strict: an unknown field fails with its JSON path):
  - top level: `kind` (`sequence` | `workflow`), `title`, `subtitle?`, `theme?`, `direction?` (`down` default | `right`, workflow only).
  - `participants` (sequence): `id`, `label`, `external?` (a person or third-party service), `sources?`.
  - `edges` (the model, sequence): `id?`, `from`, `to`, `label?`, `provenance?` (`proven` | `heuristic`), `sources?`.
  - `steps` (sequence, ordered): a step `{from, to, label, kind?, note?, emphasis?, external?, number?, edge?}` (`edge` picks one edge by `id` when a pair has several; error `unknown-edge` or `edge-mismatch`) with `kind` `call` (default) | `call-return` | `async` | `reply` | `self`; or a fragment `{fragment: alt|opt|loop|par|break, label, steps}`, where `alt` and `par` take `branches: [{label, steps}]` instead of `steps`.
  - `nodes` (workflow): `id`, `label`, `detail?`, `shape` (`start` | `step` | `decision` | `end`), `note?`, `sources?`; `links`: `from`, `to`, `label?`.
  - `sources`: `{path, line, end_line?, label?}`, repo-relative.
- **Model rule.** A sequence step is valid when an edge `from → to` is declared, or `to → from` is (then it is drawn as a reply), or the step is marked `external`, or the step starts at an `external` participant (a person or third-party service acting: a click, a webhook arriving), or `kind` is `self`. A step that starts at an internal participant needs an edge even when it calls an external service, because the call is in the code. A step that an external party starts never matches an edge in reverse (a webhook is not the reply to a call our code made). Anything else is the error `step-without-edge`. An edge that starts at an internal participant and has no `sources` is drawn dashed-grey as unproven when the diagram is checked against a repo (`--repo-root`), with the warning `edge-without-source`; without a repo root no source can be verified, so neither is shown. The exemptions for steps that start at an external participant and for `self` steps go beyond the owner's wording ("a step marked external") and are named for the owner's approval of this plan. In a workflow the links are the model itself: there is no separate edge list, and node `sources` are verified like edge sources (the plan narrows outcome 1 this way for workflows).
- **Numbering.** Top-level steps and fragments take `1, 2, 3…`; a fragment numbered `N` numbers what it contains `N.1, N.2…` across all its branches in order; nested fragments add a level. `number` overrides the shown label only; a duplicate shown number is an error.
- **Sequence layout** (User Flow look): compact actor boxes in declaration order at top, dashed lifelines, one row per step, label centred above its arrow, number prefix; `call-return` draws the return arrow dashed on the next row; `async` dashed with an open head; `self` a loop on the lifeline; fragments are labelled frames spanning the participants they touch (plus padding), nested frames inset; `emphasis` uses the accent colour.
- **Workflow layout** (deterministic layered graph): back edges found by DFS from `start` nodes in declaration order; ranks by longest path; in-rank order by 4 barycentre sweeps with declaration order breaking ties; the first outgoing link of a node keeps its column, so the main path runs straight; decisions are diamonds; links are orthogonal; back edges route in a channel outside the nodes. Coordinates are rounded to 0.5 px.
- **Layout contract.** Each layout module returns the layout dict documented in `graph_geometry.py` (shapes, routes, labels, all coordinates rounded); `graph_svg.py` draws only that dict, so the gates check exactly what is drawn.
- **Geometry gates** run after layout on the coordinates that are drawn: a route segment through a node box that is not its endpoint (`route-through-node`), two labels overlapping, or a label over a node or over a route it does not name (`label-overlap`); crossings are counted and reported.
- **Sources are read safely.** Paths resolve under `--repo-root` with no `..` escape and no symlink leaving it; files on a secret skip list (`.env*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `.npmrc`, `.pypirc`, `.netrc`, `secrets/`, `.ssh/`, `.aws/`, `.gnupg/`) are refused, not read; a cited range whose text matches a secret shape (token prefixes such as `ghp_`, `sk-`, `AKIA`, a private key header, or `password`/`secret`/`token`/`api_key` assigned a literal) is refused (`source-secret-content`), so a key in `settings.py` is not rendered either; a line past the end of the file is an error; snippets are at most 30 lines. Without `--repo-root`, sources are shown as plain references and the warning `sources-not-verified` is given.
- **Viewer.** One HTML file: the SVG is drawn in Python (the same coordinates the gates checked), with inline CSS and plain JavaScript: dark/light (`T`), walkthrough (`←`/`→`, `Esc`) highlighting one step or node with its note and source snippet, click for the same panel, `E` to export the SVG. No URL to anything outside the file.
- **Trace import.** `from-trace` reads the JSON a code-graph tool prints for a call trace: `paths[0].steps[]` with `from_name`, `from_file`, `from_line`, `to_name`, `to_file`, `to_line`, `provenance`, `site_file`, `site_line`. Participants are the files, steps are the hops, each edge carries the call site as its source and keeps its provenance. The shape is documented in `SKILL.md` without naming a tool.
- **Universal only.** `SKILL.md`, the scripts and the examples name no project, tool or path of the owner's.

## Prerequisite outside this repo (maintainer's internal copy, its own account and rules; done, APS-80)
This repo's `scripts/check.py` and `scripts/sync-public.py` come from the internal copy, and the sync deletes any public file it does not list as public-only. Before this plan's build could merge here, the internal copy got (merged, reviewed there):
- `sync-public.py`: a `public_only` entry ending in `/` covers every file under that folder; self-test cases for it.
- `public-sync.json`: `skills/graph/` and `intent/2026-11-19-graph-flow-diagrams.plan.md` as public-only.
- `check.py`: a skill folder listed as public-only (`graph`) is allowed when present: its frontmatter and trigger words are checked like the others, and `skills/graph/scripts/graph.py --self-test` runs; when absent (the internal copy) nothing fails.
- `docs/internals.md`: both behaviours described.
Rated HARD there (the sync decides what is published). T1 brought the result here, with this plan (the sync commit of this plan's PR).

## Files
1. `scripts/check.py`, `scripts/sync-public.py`, `docs/internals.md`, `.sync-source.json` (synced, T1)
2. `skills/graph/scripts/graph_ir.py`, `graph_validate.py`, `graph_sources.py`, `graph_geometry.py` (T2)
3. `skills/graph/scripts/graph_sequence.py` (T3, layout only)
4. `skills/graph/scripts/graph_workflow.py` (T4, layout only)
5. `skills/graph/scripts/graph.py`, `graph_svg.py`, `graph_trace.py`, `graph_viewer.html` (T5)
6. `skills/graph/SKILL.md`, `skills/graph/examples/*.json`, `skills/graph/tests/**` (T2 to T6)
7. `README.md` (one line: the tenth skill) (T6)

## Risks
- The sync deletes the skill or the plan: T1 dir-prefix rule with self-test cases; Proof 10 runs the real sync report after merge.
- A secret or a file outside the repo ends up in a shared HTML: `graph_sources.py` refusals with negative fixtures (Proof 3); T2 is done by the main session and reviewed by hard-reviewer.
- The layout looks wrong although the gates pass: screenshots of the three references in the PR for the owner (Proof 2).
- A network reference slips into the HTML: Proof 6 scans every rendered file.
- The skill tells sessions to do something new: `SKILL.md` is a skill's steps, HARD here; hard-reviewer, plus a fresh-agent run (Proof 11).
- `graph` collides with an installed skill name: checked before T6 (`~/.claude/skills/graph` absent today).

## Tasks

### T1 (main) Bring the internal prerequisite here by sync
- allow: `scripts/check.py` `scripts/sync-public.py` `docs/internals.md` `.sync-source.json`
- check: `python3 scripts/check.py`

### T2 (main) IR, validator, safe source reader, geometry gates
- allow: `skills/graph/scripts/graph_ir.py` `skills/graph/scripts/graph_validate.py` `skills/graph/scripts/graph_sources.py` `skills/graph/scripts/graph_geometry.py` `skills/graph/tests/**`
- check: `python3 skills/graph/scripts/graph_validate.py --self-test`
- check: `python3 skills/graph/scripts/graph_geometry.py --self-test`

### T3 (builder, parallel) Sequence layout
- allow: `skills/graph/scripts/graph_sequence.py` `skills/graph/tests/sequence/**`
- forbid: `skills/graph/scripts/graph_ir.py` `skills/graph/scripts/graph_validate.py` `skills/graph/scripts/graph_sources.py` `skills/graph/scripts/graph_geometry.py`
- check: `python3 skills/graph/scripts/graph_sequence.py --self-test`

### T4 (builder, parallel) Workflow layout
- allow: `skills/graph/scripts/graph_workflow.py` `skills/graph/tests/workflow/**`
- forbid: `skills/graph/scripts/graph_ir.py` `skills/graph/scripts/graph_validate.py` `skills/graph/scripts/graph_sources.py` `skills/graph/scripts/graph_geometry.py`
- check: `python3 skills/graph/scripts/graph_workflow.py --self-test`

### T5 (builder) SVG, CLI, viewer, trace import
- allow: `skills/graph/scripts/graph.py` `skills/graph/scripts/graph_svg.py` `skills/graph/scripts/graph_trace.py` `skills/graph/scripts/graph_viewer.html` `skills/graph/tests/cli/**`
- check: `python3 skills/graph/scripts/graph.py --self-test`

### T6 (main) SKILL.md, the three reference examples, README and CLAUDE.md skill lists
- allow: `skills/graph/SKILL.md` `skills/graph/examples/**` `README.md` `CLAUDE.md`
- check: `python3 scripts/check.py`
- check: `python3 skills/graph/scripts/graph.py validate skills/graph/examples/user-flow.json`
- check: `python3 skills/graph/scripts/graph.py validate skills/graph/examples/core-flow.json`
- check: `python3 skills/graph/scripts/graph.py validate skills/graph/examples/run-billing.json`

## Proof
1. `python3 scripts/check.py` passes here (it runs the graph self-test) and in the internal copy.
2. The three references (`user-flow`, `core-flow`, `run-billing`) validate with 0 errors and 0 warnings and render; a screenshot of each, dark and light, is in the PR.
3. Each negative fixture fails with its named rule: `unknown-field`, `step-without-edge`, `alt-one-branch`, `par-in-par`, `empty-fragment`, `duplicate-number`, `decision-unlabelled`, `decision-one-branch`, `unreachable-node`, `route-through-node`, `label-overlap`, `source-outside-root` (`..` and a symlink), `source-line-past-end`, `source-secret` (`.env`), `source-secret-content` (a key literal in an ordinary file).
4. `core-flow` renders with 0 `route-through-node`, 0 `label-overlap`, and steps 1 to 3 at the same x.
5. Rendering each reference twice gives identical bytes (sha256).
6. No rendered file contains `http://`, `https://`, `<link`, `src=` to anything but `data:`, or `url(` to anything but `#` or `data:`.
7. A checksum of the `--repo-root` tree is equal before and after `validate` and `render`.
8. A captured trace JSON converts with `from-trace`, validates, and shows heuristic hops as unproven.
9. `HOME=$(mktemp -d) python3 scripts/install.py --settings`, then `--check` under the same `HOME`: `skills/graph` installed, no drift.
10. After the merge, the internal `sync-public.py` report is `IN STEP` and `skills/graph/` is still on public `main`.
11. A fresh agent given only `SKILL.md` draws the User Flow from a prose description; where it had to guess is recorded in the PR.

## Result
