---
status: verified (plan accepted by the owner, 2026-11-20: "approve"; hard review PASS in round 5, 2026-11-21) # draft → planned → building → verified
---
# Plan: the system-map skill (APS-88)

Intent: `intent/2026-11-20-system-map.md`. Ticket: Plane APS-88. All work is HARD here: the main session builds it, and the hard-reviewer reviews it.

## Files
1. `scripts/sdlc-check.py`:
   - a new `map <repo>` subcommand runs the freshness check;
   - `converge` runs the same check in a repo that has `docs/map/`;
   - the docstring and the self-tests change to match.
2. `skills/system-map/SKILL.md`: the new skill.
3. `scripts/check.py`: `system-map` added to `SKILLS`, with its trigger prompts.
4. `skills/sdlc/SKILL.md`: Phase 4 says `converge` also checks a repo's map.
5. `README.md`, `docs/internals.md`, `CLAUDE.md`: the skill and `sdlc-check.py map` added where the skills and scripts are listed.
6. `docs/map/`: this repo's map, the pilot.
7. `public-sync.json` and `scripts/sync-public.py`: `docs/map/` never reaches the public copy (owner decisions 2026-11-20 and 2026-11-21, after the hard review):
   - The Docs view embeds the internal `CLAUDE.md` and README, and the map does not fit the public tree.
   - Listing `docs/map/` as public-only would make every sync report it for review, so the config gets a new optional key, `internal_only`. Paths under it are never published and never listed for review, and a public file under one is deleted.
   - An internal-only entry equal to, inside or around a public-only entry refuses the config, and so does an unknown key.
   - The script refuses to run when its own file differs from its copy at the source ref, or is missing there (third and fourth reviews). This stops any later copy that is behind; it cannot stop a copy older than the check itself, which would still publish `docs/map/`.
   - The owner accepted that window (2026-11-21: "Chấp nhận khe hở") until APS-91 moves the config to `maint/`, which every older copy refuses. Until then the hand-read diff is the screen, and the main session runs each sync from a checkout at `origin/main`.

## Design
**The map's layout.** Everything lives in `docs/map/`:
- `map.json` is the index. Its keys:
  - `views.architecture`: a file name; required.
  - `views.docs`: a file name, or `{"not_needed": "<reason>"}`.
  - `views.runtime`: a non-empty list of file names, or `{"not_needed": "<reason>"}`.
  - `left_out`: an object of code-file path to reason.
  - Any other key is an error.
- Each view is a `<name>.json` file with its rendered `<name>.html` beside it.
  - Architecture and Docs are ambysto-graph architecture IR (`"mode": "architecture"`). Runtime flows are flow IR (`"kind": "sequence"`).
  - The IR refuses unknown fields, so the index and the list of files left out cannot live inside a view. That is why `map.json` exists.

**`sdlc-check.py map <repo>`** lists each item below and exits 1 when it lists anything, 0 when nothing.
- **No `ambysto-graph` on `PATH`:** prints `map not checked: no ambysto-graph` and exits 2.
- **The index:** `map.json` is missing, not JSON, or has a wrong key, a missing view, an empty reason, or an empty runtime list.
- **Each view:**
  - the file a view names is missing, or its mode or kind is wrong;
  - its `.html` is missing;
  - `ambysto-graph validate --repo-root <repo> <view>` exits non-zero (the tail of its output is the item);
  - the `.html` differs from a fresh `render <view> --repo-root <repo> -o <temp>`, with CRLF normalised. Render is deterministic across folders (checked 2026-11-20). It embeds the cited code, so an edit inside a cited range also makes the HTML stale: re-rendering costs no LLM tokens.
- **Citations:**
  - every Architecture and Docs node, every non-external runtime participant and every runtime edge has at least one source;
  - every source has a `label`;
  - the cited lines (`line` to `end_line`, or `line` alone) contain the label as exact text, otherwise the item is "moved".

  Every runtime step between two participants matches an edge, by its `edge` id or by its two ends, and that edge carries the citation. Two steps need none: a step to itself, and a step between two outside parties. `validate` exempts a step an outside party starts, so the check does not rely on it.
  A view whose nodes, steps or sources have the wrong type is an item, not a crash.
- **Docs marks:** each Docs node has exactly one of the badges `source of truth`, `derived`, `internal`, `schema`.
- **Coverage:**
  - The parsed code files come from the index `overview` is built on: `ambysto-graph index --json <repo>` names `index_path` (its `schema_version` must be 1), and the files are those whose entry is marked `parsed` (a parsed file with no symbols counts too).
    - When that count differs from `coverage.parsed_code_files`, the item is "cannot list the parsed code files", so a change of format fails closed.
    - The entrypoints come from the same index, because `overview` cuts its list to fit its token limit.
  - Each parsed file is cited by an Architecture node, or is in `left_out` with a reason.
  - A `left_out` path that is not a parsed code file is an item, and so is one that is also cited.
  - Each entrypoint is cited by an Architecture source on its file whose range covers the entrypoint's line. Entrypoints in a left-out file are not required: a file left out cannot have its entrypoint cited.
- **Timeouts:** `index` 600 s, each `validate` or `render` 60 s. A timeout is an item.

**`converge`:**
- When `<repo>/docs/map/` exists and the branch changes a path that is not the plan, its intent or the intent's flows (paths under `docs/map/` count), `converge` runs the map check. Each item becomes a gap `map: <item>`.
- Exit 2 (no `ambysto-graph`) becomes the note `map not checked: no ambysto-graph`, and is not a gap.
- In a repo without `docs/map/`, nothing changes. A branch that deletes `docs/map/` gets the note `map not checked: this branch deletes docs/map/`.

**The skill** (`skills/system-map/SKILL.md`):
- The steps of Outcome 6, the no-tool path of Outcome 7, and the layout above.
- How to draw each view:
  - **Architecture:** boundaries are domains, `sublabel` is the "why" line, the badge `canonical` marks a source of truth, outside services go in their own boundary, and edges are labelled.
  - **Docs:** boundaries are the four marks.
  - **Runtime:** the flow rules of the `graph` and `ambysto-graph` skills, with `sources` and `--repo-root`.
- A fresh-reader prompt adapted from the sdlc one, given the map files only.
- Running `sdlc-check.py map` before asking the owner.
- The map going up in its own PR.

The skill is universal, and its description is written so it does not collide with `graph` (check.py's ranking test runs in the public copy too).

## Risks
1. **The index file's format is ambysto-graph's own** (`schema_version` 1), not a public API.
   - **Check:** the count must equal `coverage.parsed_code_files`. Otherwise the item fails closed, and a self-test proves it.
2. **`converge` gets slower** in a repo with a map, since it runs `index`, then `validate` and `render` per view.
   - **Check:** time `map .` on the pilot (Proof 3) and record it.
3. **A stale map blocks every plan that touches code in a repo with a map** (an owner decision).
   - **Check:** the stale-map proof (4) shows the fix is a re-render or a citation edit. Neither needs an LLM.
4. **The new skill's description collides with `graph` or `sdlc`** in check.py's ranking test.
   - **Check:** `check.py` here, and in a public tree with `graph` (Proof 9).
5. **A self-test passes on a broken check.**
   - **Check:** mutation testing of the new self-tests (lesson `mutation-check-self-tests`, Proof 2).
6. **The pilot map is wrong but valid** (the check cannot judge meaning).
   - **Check:** a fresh reader and the owner's verdict (Proof 7).

## Tasks

### T1 (main) The map check in sdlc-check.py, and converge
- allow: `scripts/sdlc-check.py`
- check: `python3 scripts/sdlc-check.py --self-test`
- check: `python3 scripts/check.py`

### T2 (main) The skill, check.py, and the docs
- allow: `skills/system-map/**` `scripts/check.py` `skills/sdlc/SKILL.md` `README.md` `docs/internals.md` `CLAUDE.md`
- check: `python3 scripts/check.py`

### T3 (main) The pilot map of this repo
- allow: `docs/map/**` `public-sync.json` `scripts/sync-public.py`
- check: `python3 scripts/sdlc-check.py map .`

## Proof

1. `python3 scripts/sdlc-check.py --self-test` and `python3 scripts/check.py` pass. Using a fake `ambysto-graph`, the self-test covers:
   - each index error;
   - a missing or wrong view and a missing HTML;
   - a validate failure, a stale HTML and a timeout;
   - each citation item: no source, no label, moved;
   - a Docs mark missing or doubled;
   - each coverage item: an uncited file, a left-out file with no reason, a left-out file that is not parsed code or is also cited, an uncited entrypoint, an entrypoint in a left-out file not required, and a count mismatch;
   - exit 2 with no tool;
   - `converge`: no `docs/map/` means no check; a change to the plan or intent only means no check; a code change runs the check and its items are gaps; no tool gives a note and passes. (O2, O3, O4, O5)
2. Mutation testing of the new map and converge code: every mutation is caught, and the count is recorded. (O4, O5)
3. `python3 scripts/sdlc-check.py map .` on this repo with the pilot map exits 0 and lists nothing; its run time is recorded. (O1, O2, O3)
4. Stale map, on a scratch clone with the pilot map:
   - renaming a cited function makes `map` list the moved citation and the stale HTML;
   - `converge` on a scratch plan that changes that file fails with `map:` gaps;
   - fixing the citation and re-rendering clears them. (O4, O5)
5. With `ambysto-graph` off `PATH`, `map .` exits 2 with `map not checked`, and `converge` on the same scratch plan passes with that note. (O5, O7)
6. A fresh agent, given only `skills/system-map/SKILL.md` and a scratch repo, follows the skill. The PR records where it had to guess. (O6, O7)
7. The pilot PR records the questions asked, the fresh reader's lists and what became of them, and the owner's verdict on whether the map is right. (O8)
8. `HOME=$(mktemp -d) python3 scripts/install.py --settings`, then `--check` under the same `HOME`, exits 0 with the new skill installed.
9. `check.py` passes in a public tree (a copy of public `main` with this branch's scripts and skills), where `graph` and `mockup` are present.

## Result

1. PASS: `sdlc-check.py --self-test` passes, and `check.py` passes with 10 skills. The map and converge cases run through a fake `ambysto-graph`. After the hard review, cases were added for:
   - a parsed file with no symbols, an index of another schema, a malformed view and a blank label;
   - runtime steps that match no edge: from an outside party, marked external, inside a branch, or naming an unknown edge id;
   - a step between two outside parties, an entrypoint past the cited range, and a symlinked view;
   - converge with the intent's flow only, with no tool (no gap at all), and on a branch that deletes `docs/map/`.
   After the second review, cases were added for:
   - a step inside a `loop`;
   - a step that borrows the reverse edge although an outside party starts it, or although it is marked external;
   - a NUL byte in a path;
   - fragments nested 3000 deep;
   - a malformed Architecture view: one item, no coverage.
   After the third review, the deep-nesting cases are built as text and also cover a view and a `map.json` too deep to parse; the self-test passes on Python 3.11, 3.12 and 3.14.
   `sync-public.py --self-test` passes on the same three, with cases for:
   - an internal-only folder in report mode (not published, not reviewed; a public file under it is listed for deletion) and in `--write` (a file under it that matches a leak pattern does not refuse the write; the public copy is deleted);
   - each bad config: a bad path, not a list, an overlap either way, an unknown key;
   - a script that differs from its copy at the source ref, in report and write mode with HEAD holding an equal copy (refused); one missing at the source ref of its own repo (refused); an equal copy (runs).
2. PASS: 78 out of 78 mutations of the map and converge code were caught, after the three reviews. That includes the survivors each review named. One more mutation was dropped as equivalent: only the Architecture view stores ranges. `sync-public.py`'s `internal_only`, unknown-key and self-copy checks: 13 out of 13 mutations caught, including both delete filters and the self-copy check in write mode, against HEAD, and against an uncommitted edit.
3. PASS: `map .` exits 0 with 0 gaps (6 views, 20 parsed code files, 2 left out, 26 entrypoints) in 0.21 s, using the installed `ambysto-graph` rebuilt after APS-89 (PR #21, merge 1043dba). Three findings came out of the pilot:
   - the index took the helper `tool_said` for an MCP-tool entrypoint, so it was renamed `output_tail`;
   - the architecture render was not byte-stable, which was fixed in APS-89;
   - while the review fixes were being made, the check itself caught the pilot map going stale (`sdlc-check.py main` moved), and that was fixed in the map.
4. PASS, on a scratch copy with the pilot map. Renaming `cmd_new` in `scripts/dispatch.py`:
   - made `map` list three moved citations and two stale HTML files (exit 1);
   - made `converge` on a scratch plan allowing that file fail with the same five gaps, each prefixed `map:`.
   Fixing the labels and re-rendering cleared both: `map` and `converge` then pass.
5. PASS: with `ambysto-graph` off `PATH`, `map .` prints `map not checked: no ambysto-graph` and exits 2. `converge` on the same scratch plan passes with that note.
6. PASS: a fresh agent (Sonnet 5.5), given only the skill and a scratch repo of 4 Python files, wrote a map that `map` passed on the first full attempt. It had to guess six points:
   - the IR field names;
   - where the step numbers go;
   - a repo with no docs;
   - how to find where an entrypoint ends;
   - when Docs is not needed;
   - whether warnings matter.
   Each guess now has a line in the skill.
7. PASS: the owner's verdict on the pilot map, 2026-11-20: "Đúng, dùng được" (right, usable). The PR records the questions asked and the fresh reader's lists.
8. PASS: `HOME=$(mktemp -d) install.py --settings` then `--check` both exit 0, and `system-map` is among the installed skills.
9. PASS: `check.py` in a public tree passes with 13 skills, and no trigger collides. The tree was public `main` (8a25b82, which adds `userflow`) with this branch's `scripts/` and `skills/`, plus public's own `userflow` public-only entry in check.py. That entry comes from separate work, branch `aps-89-userflow-public-only`. `check.py` was not changed after the review.
