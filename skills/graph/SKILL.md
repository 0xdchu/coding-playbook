---
name: graph
description: Draw how a system works as one offline HTML diagram - numbered sequence diagrams (who calls whom, in order, with alt, loop, par frames, webhooks and replies) and flowcharts with decisions and loops - where every step is checked against declared links and cited code lines. Use when asked for a sequence diagram, a user flow, a request flow, a flowchart, or "draw how X works".
---

# /graph

Turn a description or a codebase into a diagram a person can trust: each arrow either matches a link you declared (with the code lines that make it) or is marked external. The script checks the diagram before it draws it and refuses one that breaks a rule.

Scripts: `python3 ~/.claude/skills/graph/scripts/graph.py` (below: `graph.py`). Standard library only, no network; the HTML it writes loads nothing from outside.

## 1. Pick the kind
- **sequence**: several parties exchange messages in order (a purchase, a login, a webhook, a job run). Use fragments for conditions and repeats.
- **workflow**: one actor moves through steps and decisions (onboarding, a pipeline, a review loop).
If the request covers both, draw two files.

## 2. Gather the facts before drawing
- In a repo: find each interaction in the code and note `path` and `line` for it. Do not draw a call you cannot point to unless an external party (a person, a third-party service) makes it.
- From a description only: draw what was said; mark people and outside services `external: true`; cite nothing.
- From a code-graph tool that prints a call trace as JSON (`paths[0].steps[]` with `from_name`, `from_file`, `from_line`, `to_name`, `to_file`, `to_line`, `provenance`, `site_file`, `site_line`): `graph.py from-trace trace.json -o diagram.json` gives a starting sequence; edit labels so a person can read them.

## 3. Write the IR (JSON)
Sequence:
```json
{"kind": "sequence", "title": "User flow",
 "participants": [{"id": "buyer", "label": "Buyer", "external": true},
                  {"id": "pay", "label": "Payments", "external": true},
                  {"id": "api", "label": "API"},
                  {"id": "db", "label": "Database"}],
 "edges": [{"from": "api", "to": "db", "label": "write", "sources": [{"path": "src/orders.py", "line": 42}]}],
 "steps": [{"from": "buyer", "to": "api", "label": "click buy"},
           {"from": "pay", "to": "api", "label": "webhook: paid", "kind": "async", "emphasis": true},
           {"fragment": "alt", "branches": [
              {"label": "new buyer", "steps": [{"from": "api", "to": "db", "label": "write user + ticket"}]},
              {"label": "known buyer", "steps": [{"from": "api", "to": "db", "label": "add ticket"}]}]}]}
```
- `edges` is the model: declare each link your code makes once, with `sources`, including calls to outside services. A step must match an edge (either direction; the reverse is drawn as a reply) unless it is marked `external: true`, starts at an `external` party (a click, a webhook arriving) or is `kind: "self"`.
- Step `kind`: `call` (default), `call-return` (return drawn for you), `async` (dashed: events, webhooks, queues), `reply`, `self` (a party working on its own: from = to).
- Fragments: `opt`, `loop`, `break` take `label` and `steps`; `alt` and `par` take `branches` (two or more, each `label` and `steps`). Nest freely, but not `par` directly in `par`.
- Numbers are given for you: `1, 2, 3`; inside fragment 3: `3.1, 3.2`. `number` overrides a shown number (no duplicates).
- `note` (shown in the walkthrough panel) and `emphasis` (accent colour) on any step. Emphasise one or two steps at most.

Workflow:
```json
{"kind": "workflow", "title": "Onboarding",
 "nodes": [{"id": "a", "label": "1. Sign up", "detail": "name + website", "shape": "start"},
           {"id": "q", "label": "Can it connect?", "shape": "decision"},
           {"id": "y", "label": "Write via API"}, {"id": "n", "label": "Paste JSON"},
           {"id": "r", "label": "Review", "sources": [{"path": "app/review.py", "line": 10}]}],
 "links": [{"from": "a", "to": "q"}, {"from": "q", "to": "y", "label": "Yes"},
           {"from": "q", "to": "n", "label": "No"}, {"from": "y", "to": "r"}, {"from": "n", "to": "r"}]}
```
- `shape`: `start`, `step` (default), `decision`, `end`. Every link out of a decision has a label; a decision has two or more. Every node is reachable from a start node. A link back to an earlier node is a loop and is routed outside. `"direction": "right"` lays it out left to right.

Any field not shown here is an error, reported with its JSON path.

## 4. Check, then draw
```
graph.py validate diagram.json [--repo-root <repo>] [--json]
graph.py render diagram.json -o diagram.html [--repo-root <repo>] [--theme dark|light]
```
- With `--repo-root`, every cited `path:line` must exist inside that repo; secret-shaped files (`.env`, keys, `secrets/`) and cited lines that hold a token, key or password literal are refused. An edge from an internal party without sources is drawn grey dashed as unproven and warned about.
- `render` validates first and refuses a diagram with errors, including layout errors (a route through a box, labels on top of each other).
- Fix every error. Fix warnings unless you can say why one stays, and say it.

## 5. Hand it over
Give the path of the HTML file. In it: `←`/`→` walk the steps one by one with notes and code snippets, `T` switches dark/light, `E` exports the SVG. Say which steps are external or unproven, so the reader knows what was not checked against code.
