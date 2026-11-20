---
name: system-map
description: Writes and updates a repo's committed map in docs/map/ (an Architecture view grouped by domain, a Docs view of sources of truth and derived documents, and runtime request paths), every part citing the code it stands for, checked for citations, coverage and fresh renders, and kept current by converge. Use when the owner says "map this repo", "system map", "draw the architecture of the repo", "/system-map", or when converge lists `map:` gaps. Not for one flow drawn from an intent (the sdlc skill), not for a one-off diagram nobody keeps.
---

# /system-map

A map is a picture of a whole repo that a reader can trust. It lives in the repo, in `docs/map/`. Its JSON files are the source of truth, and the HTML files are renders of them. Every part on the map cites the code or text it stands for, and a check proves three things: the citations still point at that code, every code file is on the map or left out with a reason, and the HTML is a fresh render. Once a repo has a map, `converge` runs that check on every plan that changes the repo, so the map cannot go stale quietly.

## What you need
- **`ambysto-graph`** on `PATH`. It draws the Architecture and Docs views, and every check needs it. Without it, go to "Without ambysto-graph" below.
- **The check:** `python3 <coding-playbook>/scripts/sdlc-check.py map <repo>`, from the coding-playbook repo your global instructions name.
  - Exit 0: nothing listed.
  - Exit 1: it lists items to fix.
  - Exit 2: nothing was checked (no `ambysto-graph`).

## The layout
Everything lives in `docs/map/`:

```text
docs/map/
  map.json                  the index
  architecture.json + .html the Architecture view (always)
  docs.json + .html         the Docs view, or not needed
  runtime-<path>.json + .html  one per runtime path, or not needed
```

`map.json`:

```json
{"views": {"architecture": "architecture.json",
           "docs": "docs.json",
           "runtime": ["runtime-checkout.json"]},
 "left_out": {"tools/bench.py": "a benchmark, not part of the system"}}
```

- **`docs`:** a file name, or `{"not_needed": "<reason>"}`.
- **`runtime`:** a non-empty list of file names, or `{"not_needed": "<reason>"}`, for example "a library with no request path".
- **`left_out`:** code files you choose not to draw, each with a real reason.
- **Names:** `<name>.json` beside `map.json`.
- No other keys.

## Steps

1. **Skeleton (no LLM tokens).** Run `ambysto-graph overview --dir <repo>`, under a memory cap on a big repo. It lists the clusters, the entrypoints and the hotspots. This is the raw list of what exists, not the map.

2. **Meaning.** Read the repo's `CLAUDE.md`, `README`, `docs/`, and its `intent/` files (newest first). Note:
   - the domains (what the system does, in the owner's words, not the folder names);
   - what each part is for;
   - which files are a source of truth, which are derived from them, and what the outside services are.

   A repo with none of these files: read each code file's docstring or header comment and its entrypoints, and say so in your questions.

3. **Ask the owner 3 to 5 questions,** each with your best guess so one word confirms it:
   - the domains and which parts go in each;
   - what the source of truth is where two places hold the same fact;
   - which request or command paths to draw as runtime flows (the 1 to 3 that matter most);
   - which code files to leave out, and why.

   Write each answer into the map.

4. **Write the views.**
   - **Architecture** (`"mode": "architecture"`):
     - `boundaries`: `{"id", "label", "layer"}`, one per domain, plus one for outside services;
     - `nodes`: `{"id", "label", "sublabel", "boundary", "layer", "sources", "badges", "row", "col"}`. `sublabel` is one line: why the part exists, not what the file is called. `badges` is a list: `["canonical"]` on a node that is a source of truth;
     - `edges`: `{"from", "to", "label"}` between parts; an Architecture edge takes no `sources`. Put numbers in the labels ("1. credential", "2. kill switch") only when the numbered edges form one path;
     - `layer` is one of `frontend`, `backend`, `database`, `security`, `messagebus`, `cloud`, `external`; pick one per boundary so each domain has its own colour;
     - `row` and `col` place a node on the grid, and a boundary wraps its nodes, so give each domain its own block of cells. Put the host or entry part on the left and outside services on the right. Placing by hand often halves the connector crossings that `validate` warns about.
   - **Docs** (`"mode": "architecture"`):
     - one node per document, and per code file that is a source of truth;
     - each node has exactly one badge from `source of truth`, `derived`, `internal`, `schema` (its main role), in `badges`;
     - a repo whose only documents are comments in the code: `"docs": {"not_needed": "<reason>"}`;
     - edges are labelled `generates`, `documented by` or `defers to`;
     - boundaries group the marks.
   - **Runtime** (`"kind": "sequence"`), one per path:
     - follow the `ambysto-graph` skill's flow IR rules. In short: `participants` `{"id", "label", "external", "sources"}`; `edges` `{"from", "to", "label", "id", "sources"}`; `steps` `{"from", "to", "label"}`, with `"edge": "<edge id>"` when two edges join the same pair, `"kind": "self"` for a step to itself, and `{"fragment": "alt", "branches": [{"label", "steps"}]}` for a choice;
     - people and outside services are `external` participants;
     - every edge carries `sources`;
     - every step between two different participants matches an edge.
   - **Citations:**
     - every Architecture and Docs node, every non-external participant and every runtime edge has `sources`;
     - each source has `path`, `line`, `end_line` when the part spans lines, and `label`: the exact name found in those lines (the function, class or heading);
     - to cite an entrypoint, cite its function from its `def` line to its last line (read the file for the end), or cite the `main` lines that dispatch the commands;
     - the check reads those lines and reports the citation as moved when the label is no longer there.
   - **Coverage:**
     - every code file `ambysto-graph` parses must be cited by an Architecture node, or be in `left_out`;
     - every entrypoint (`main`, a CLI command, a route) must be inside an Architecture citation's line range on its file.

     Prefer citing to leaving out: leave a file out only when drawing it would add noise (fixtures, a benchmark, a one-off script).

5. **Render and check.**
   - Render each view: `ambysto-graph render docs/map/<name>.json --repo-root . -o docs/map/<name>.html`, with no other option.
   - Then run `sdlc-check.py map .` and fix every item it lists. A validate error, a moved citation, an uncited file or an uncited entrypoint is fixed in the JSON; a stale HTML is fixed by rendering again.
   - Repeat until it exits 0. A `validate` warning (label collision, crossings) does not fail the check; fix it when it hurts reading.
   - Look at the rendered Architecture page before going on: a map that passes the check can still be hard to read.

6. **Fresh reader.** Run one fresh agent with none of this chat, on the model your builder agent uses, read-only, with this prompt:

   ```text
   You are a fresh reader of a system map. Read ONLY the files in <repo>/docs/map/ (the JSON files; skip the HTML) and nothing else.
   Imagine you must explain this system to a new engineer from the map alone. Return two numbered lists, at most 300 words in all:
   A. Guesses: each point you had to guess (a part whose purpose is unclear, a link whose meaning is unclear, a domain that mixes two concerns), quoting the node or edge.
   B. Gaps: each thing a reader would expect on a map of this kind that seems missing (a part with no link, an outside service with no caller).
   Write "none" for an empty list. Do not invent problems to fill a list.
   ```

   Each item ends as a question to the owner, or a clearer `sublabel` or label. Then render and check again.

7. **Owner approval, then its own PR.**
   - Show the owner the HTML files.
   - The map goes up as its own PR. The PR body records: the questions you asked and the answers, the fresh reader's lists and what became of each item, and the check's output.

## Updating a map
When `converge` lists `map:` gaps, or the owner asks for an update:
- run `sdlc-check.py map .`;
- fix each item, as in step 5;
- for a new part, ask the owner which domain it belongs to, unless it is clear from the intent being built;
- render, check, and commit on the same branch as the change that made the map stale. So the plan's task that changes code also allows `docs/map/**`.

A re-render alone fixes a stale HTML. The HTML embeds the cited code, so an edit inside a cited range also needs one.

## Without ambysto-graph
Say so to the owner: the Architecture and Docs views and every check need `ambysto-graph`.
- Draw only the runtime flows, with the `graph` skill, as `docs/map/runtime-<path>.json` with their `.html`.
- Write `map.json` naming them, with no Architecture view yet. Tell the owner the map is unfinished: once `ambysto-graph` is installed, `sdlc-check.py map` lists the missing Architecture view, and the next session finishes the map from step 1.
- Commit them in their own PR, as on the main path.
- Never say the map was checked: `sdlc-check.py map` exits 2, and `converge` notes "map not checked".

## Rules
- The JSON files are the source of truth. Never edit an HTML file by hand.
- A map states what the code does today, cited. A plan or a wish goes in an intent, not on the map.
- One map per repo.
