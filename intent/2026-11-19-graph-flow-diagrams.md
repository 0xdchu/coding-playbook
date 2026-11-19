---
status: draft   # draft → approved → planned → building → verified → shipped (PR #n)
---
# Flow diagrams that are exact and easy to read: steps on one model, fragments, real flowcharts

Design for the flow diagrams of the graph skill (`/graph`, today installed as the `ambysto-graph` skill; not one of this repo's skills yet). It lives here, in `coding-playbook`, as an intent only; the diagram engine it describes is `ambysto-graph` (the code-graph and diagram tool the global instructions' Tools section names). Where the engine work is built, and whether the skill joins this repo's skills, is decided with the plan.

## Problem
`ambysto-graph` promises diagrams of how a system works that a human can trust. Today the two flow modes fall short:

- `sequence` draws numbered-in-order arrows between lifelines, but has no return or async arrows, no `alt` / `loop` / `opt` / `par` frames, no notes, no emphasis on the step that matters, and actor cards are tall and empty. Steps are ordered by array index; `step` is never shown.
- `workflow` places steps on a 3-column grid, so a linear flow reads in the wrong order. Decisions are rectangles, branch labels get lost, connectors run through other cards, and back edges (retry, "next scheduled run") cross the whole canvas. `validate` reports such a diagram as VALID with 0 warnings, although the engine's first design promised label-route and crossing checks.
- Nothing ties a flow step to the system it describes. An agent can draw `API -> Supabase: write ticket` with no edge between them in the code or in the architecture view, and the diagram looks just as certain as a proven one.

Reference outputs the owner wants to reach (screenshots shared in the owner's request, not attached here): a numbered purchase-flow sequence across Buyer, Stripe, API, Supabase and Resend with one highlighted webhook step; a top-down onboarding flowchart with a Yes/No decision and a scheduled-run loop; a run-and-billing sequence with self-calls, an `alt [not enough] / [enough]` frame and a nested `loop [each prompt x engine]`.

## What we take from three tools (studied 2026-11-19)
- **Structurizr DSL** (Apache-2.0): one model, many views; a view only selects, so views never drift. A dynamic-view step must match an existing model relationship, else the build fails; a step in the reverse direction of an edge already shown is a reply (dashed). One edge can be told with a per-step description. Not taken: its DSL and Java parser, Graphviz/dagre, stored manual x/y, the deployment model, and parallel numbering that reuses integers (ambiguous).
- **LikeC4** (MIT): the fragment vocabulary (marked experimental in its docs) `alt` with `when`/`else` branches, `opt`, `loop`, `break`, `par`, nestable, with rules such as no `par` directly in `par`; structural step ids (`step-02:alt.01:when.01`); per-step notes; a walkthrough player (next/previous step with highlight); a constraint-based sequence layout; drift detection by layout hash. Not taken: the Langium DSL, the React/Mantine/xyflow runtime, Graphviz WASM, hand-saved `.snap` layouts. LikeC4 lets steps ignore the model; we do not.
- **Ilograph** (proprietary; ideas only, never its YAML format, docs text or look; its key names are quoted here only to identify the ideas): step kinds for a call, a call that returns (return drawn automatically) and an async send (dashed, no control transfer); named, nestable sub-sequences; walkthrough slides that inherit the previous slide's state; a detail level for progressive disclosure; perspectives that reuse one resource tree. Not taken: auto-sizing by relation count, hover-only descriptions, sequence perspectives that ignore the layout orientation.
- **None of the three** has flowchart decisions, verified `path:line` evidence on steps, or an index of the real code. Those are ours to build.

## Outcome
1. **Steps on one model.** A flow diagram (`sequence` or `workflow`) declares its participants and edges once, and its ordered `steps` reference them. `validate` fails a step whose endpoints have no declared edge (in either direction; reverse = reply), unless the step is marked `external` (a person or third-party service with no code to cite). An internal edge used by a step carries `sources` verified against `--repo-root`, or is marked `heuristic` and drawn as such.
2. **Step kinds.** `call`, `call-return` (dashed return drawn by the renderer), `async` (dashed, for webhooks and events), `reply`, `self` (self-call loop on a lifeline). Steps carry an optional note and an `emphasis` flag.
3. **Fragments.** `alt` (with labelled branches), `opt`, `loop`, `par`, `break`, nestable, drawn as labelled frames around the steps they contain. `validate` rejects an empty fragment, `par` directly inside `par`, and an `alt` with fewer than two branches.
4. **Numbering.** Steps are numbered `1, 2, 3` at top level and `2.1, 2.2` inside a fragment, shown on every arrow; an author may override a label but not create duplicate numbers.
5. **Real flowcharts.** `workflow` nodes take a `shape` (`start`, `step`, `decision`, `end`). The layout is a deterministic layered top-down graph (left-to-right on request): the main path runs straight down, branches spread sideways, back edges route on the outside. `validate` fails a decision whose outgoing edges are unlabelled or fewer than two, an unreachable node, a connector that crosses a node card, and a label that overlaps a route.
6. **Walkthrough.** The viewer gets a step-by-step mode (next/previous, keyboard), highlighting one step or flowchart node at a time with its note and verified source snippet.
7. **Auto sequence keeps working.** `render --auto --mode sequence --from --to` emits the new IR, with every step tied to a proven or heuristic graph edge.
8. The skill (`SKILL.md`) teaches agents to write these diagrams, with the three reference flows as worked examples.

## Constraints
- Same promises as v1: offline single binary, no network in the binary or the HTML, read-only on sources, secrets never rendered, deterministic output for the same input.
- The IR stays strict JSON with `deny_unknown_fields`. Changes are additive; existing v1 diagrams still validate and render the same, or the plan says exactly which ones change and why.
- No new layout runtime (no Graphviz, ELK, dagre, React). Layout stays in Rust.
- English output by default.

## Out of scope
- A text DSL (Structurizr- or LikeC4-style) on top of the JSON IR.
- Several views in one HTML file with drill-down between them (Ilograph perspectives, LikeC4 `navigateTo`); considered for a later intent.
- Deriving flowcharts automatically from code control flow (`if`/`match` inside a function).
- Saved manual layouts or drag-and-drop editing.
- C4 deployment views.

## Owner decisions (2026-11-19)
- A step whose endpoints have no declared edge is a `validate` error, unless the step is marked `external`.
- Several views in one HTML (perspectives, drill-down) is a later intent.
- Flowcharts run top-down by default; left-to-right on request.
- The default `sequence` look follows the owner's "User Flow" reference: dark, compact actor boxes, numbered labels above arrows, one emphasised step in an accent colour; the light theme stays available.

## Open questions
None.
