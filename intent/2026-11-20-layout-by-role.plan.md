---
status: planned # draft → planned → building → verified (plan accepted by the owner, 2026-11-21: "Chấp nhận", the boundary change included)
---
# Plan: folders by role (APS-91)

Intent: `intent/2026-11-20-layout-by-role.md`. Ticket: Plane APS-91. All work is HARD here: the main session builds it, and the hard-reviewer reviews it.

Building starts only after PR #86 (APS-88) and the branch `aps-89-userflow-public-only` are merged into `main`. The branch for the build starts from `main` after both merges.

## Files
1. **The moves** (`git mv`; file names unchanged):

   | From | To |
   |---|---|
   | `rores/global/*`, `rores/agents/*` | `rules/global/*`, `rules/agents/*` |
   | `hooks/agent-guard.py`, `hooks/pin.json`, `hooks/autonomous-settings.json` | `hooks/1prompt/` |
   | `gates/session-gates.py` | `hooks/gates/` |
   | `guard/owner-token-guard.py` | `hooks/owner-token-guard/` |
   | `saveit/saveit-hook.py` | `hooks/saveit/` |
   | `graph/graph-hook.py` | `hooks/graph/` |
   | `loop/loop-stop.py`, `loop/loop-wake.py` | `hooks/loop/` |
   | `loop/loop.py` | `tools/` |
   | `scripts/dispatch.py`, `sdlc-check.py`, `plane.py`, `progress-diagram.py`, `hil-report.py` | `tools/` |
   | `scripts/install.py`, `check.py`, `sync-public.py`, `switch-model.py`, `github-boundary.py`, `github-boundary.json`, `cost-report.py`, `model-prices.json` | `maint/` |
   | `public-sync.json` | `maint/` |
   | `scripts/switch-test.py`, and everything in `switch-test/` | `maint/switch-test/` |

2. **The paths each file uses to find another**, in every script and its self-test:
   - `maint/install.py`: its sources.
   - `maint/check.py`: every path it checks or runs. The pin check compares `hooks/1prompt/<name>` with `hooks/<name>` in an `ambysto-1prompt` clone, whose own layout is unchanged.
   - `maint/sync-public.py`: `CONFIG` becomes `maint/public-sync.json`. Its `replace` and `public_only` entries are renamed (`rores/global/…` becomes `rules/global/…`).
   - `maint/switch-model.py` and `maint/switch-test/switch-test.py`: the kit's paths.
   - `maint/github-boundary.py` and `maint/cost-report.py`: their data files, which stay beside them.
   - `tools/*`: their siblings.
   - `hooks/loop/loop-wake.py` finds `loop.py` through the run's judge. That becomes `judge.parent / "loop.py"`, since both now sit in `tools/`.
   - `tools/loop.py resume` points a reopened run's `judge` at the `sdlc-check.py` beside it, so a run closed before the move can still be resumed. This is the one change beyond a path string, and it exists only because of the move.
   - The hooks' self-tests: the repo paths they build.
3. **`.claude/boundary.json`:** `protected` changes from `hooks/*` to `hooks/1prompt/*`.
   - `fnmatch`'s `*` crosses `/`, so after the move `hooks/*` would also protect this repo's own hooks.
   - `hooks/1prompt/*` keeps exactly the files protected today: the 1prompt copy.
   - **This changes a protected list's text, not its set, and the owner accepts it with this plan.**
4. **The prose:**
   - `rules/global/CLAUDE.md`, the global block every session loads: about 10 commands;
   - `rules/agents/*.md`;
   - every `skills/*/SKILL.md` that names a path of this repo (`sdlc`, `system-map`), and `skills/starter-kit/context-config.md` if it names one of ours;
   - `README.md` and `docs/internals.md`;
   - the citations in `docs/map/*.json`, then a re-render.
5. **`CLAUDE.md`:**
   - It opens with `## Where things live`: one row per job, giving the path.
   - The jobs: write a builder's contract, check an intent or a plan, run or wake a one-prompt run, move a ticket, draw progress, read the owner log, install, verify this repo, sync the public copy, switch the model, test a model switch, set GitHub rules, the cost report, the hooks (one row per install folder), the rules and agents, the skills, the map, intents.
   - Every other path in `CLAUDE.md` is renamed too.
6. **`maint/check.py` checks the table.** Every file under `rules/`, `hooks/`, `tools/` and `maint/` must be named in the `## Where things live` section of `CLAUDE.md`, by its own path or a folder above it (`hooks/loop/`). `__pycache__` is ignored.
   - The public copy has its own `CLAUDE.md` (public-only), so the public sync PR adds the same table there by hand. Its rows name `rules/global/` for the public-only `AGENTS.md` and `GEMINI.md`.
7. **Outside this repo, after the merge:**
   - ambysto-memory: lesson `long-run-coding-is-1prompt` names old paths. One PR fixes it, for the owner to merge.
   - Run `install.py --global --settings` from the merged `main`.
   - The public sync. Sync never moves public-only files, so `rores/global/AGENTS.md` and `GEMINI.md` are moved by hand to `rules/global/` in the public PR.

## Risks
1. **A one-prompt run open at the move** keeps the old judge path, so its Stop hook can no longer find `converge`.
   - **Check:** just before the merge, no run file under `~/.claude/1prompt-runs/` points at a run that is open. Today 2 runs exist, both closed. A run closed earlier is re-pointed by `loop.py resume` (Files 2).
2. **A path missed in a script.** **Check:** `maint/check.py` runs every self-test, and Proof 5 installs over the current install.
3. **A path missed in prose.** **Check:** the `git grep` of Proof 1.
4. **A running session still has the old global block in its context,** loaded at its start, so it runs an old command.
   - **Check:** it fails at once with "No such file" (no stub hides it).
   - The install right after the merge gives every new session the new paths, and the merge summary tells the owner.
5. **The hook pin check** reads the wrong side after the move. **Check:** `check.py`'s pin check passes, with the `ambysto-1prompt` clone next to this repo.
6. **The public copy:**
   - The public-only files under `rores/` are left behind. **Check:** Proof 8 builds the public tree, and its `check.py` and table check pass.
   - The public `CLAUDE.md` has no table. **Check:** the same.
7. **Another branch opened during the build** conflicts with the move.
   - **Check:** the build starts right after the two merges, and `git` follows renames on a rebase.
   - The merge summary names any open branch.
8. **The table check is too strict** for a new file. **Check:** it names the missing file and the section to add it to; a self-test case covers this.
9. **`git log --follow` loses history** when a moved file also changes a lot. **Check:** Proof 4.

## Tasks

### T1 (main) Move the files and fix the paths in the code
- allow: `rules/**` `rores/**` `hooks/**` `tools/**` `maint/**` `scripts/**` `loop/**` `gates/**` `graph/**` `guard/**` `saveit/**` `switch-test/**` `public-sync.json` `.claude/boundary.json`
- check: `python3 maint/check.py`

### T2 (main) The prose, the table and its check, and the map
- allow: `CLAUDE.md` `README.md` `docs/internals.md` `docs/map/**` `skills/**` `rules/**` `maint/check.py`
- check: `python3 maint/check.py`
- check: `python3 tools/sdlc-check.py map .`

## Proof

1. No old path is left. Run this from the repo, excluding `intent/` and `docs/reviews/`: (O3)

   ```
   git grep -nE '(^|[^/A-Za-z0-9_.-])(rores/|scripts/[a-z-]+\.(py|json)|loop/loop(-stop|-wake)?\.py|gates/session-gates\.py|graph/graph-hook\.py|guard/owner-token-guard\.py|saveit/saveit-hook\.py|hooks/(agent-guard\.py|pin\.json|autonomous-settings\.json)|switch-test/|public-sync\.json)' -- . ':!intent' ':!docs/reviews' ':!maint/public-sync.json'
   ```

   It prints nothing. Paths installed under `~/.claude/hooks/…` do not match, since a `/` comes before them.
2. The layout: (O1)
   - `git ls-tree --name-only HEAD` lists exactly `.claude .gitattributes .gitignore CLAUDE.md README.md docs hooks intent maint rules skills tools`;
   - `ls hooks` gives the six install folders.
3. Checks: (O2, O4)
   - `python3 maint/check.py` passes. It runs every script's self-test, the pin check against the `ambysto-1prompt` clone, and the table check.
   - Removing one row from the table makes `check.py` fail and name the file.
   - `python3 tools/sdlc-check.py map .` exits 0.
   - `converge` on this plan passes.
4. History: `git log --follow --oneline` on `tools/sdlc-check.py`, `hooks/gates/session-gates.py` and `rules/global/CLAUDE.md` shows commits from before the move. `git diff -M --stat` shows a rename for every moved file. (O4)
5. Install over the current install, on a scratch `HOME`. Copy only `settings.json`, `CLAUDE.md`, `agents/`, `hooks/` and `skills/` from `~/.claude`, never credentials. Then: (O4)
   - install from `main` before the move, and `--check` exits 0;
   - install from this branch over it, with `--global --settings`, and `--check` exits 0;
   - the hook entries of `settings.json` and the list of installed files are the same before and after (`diff`);
   - after the merge, the same holds for the real `~/.claude`.
6. Every command the global block names exists. A script pulls each `python3 <path>` from `rules/global/CLAUDE.md`, maps `~/work/ambysto/coding-playbook` to this tree, and finds every file. (O3)
7. A fresh agent (the builder's model) is given only `CLAUDE.md` and the file list. It names the file for 8 jobs taken from the global rules, and gets all 8 right. The PR records its answers. (O2)
8. The public tree. Take a scratch copy of public `main`, run `maint/sync-public.py --write` into it, add the table to its `CLAUDE.md`, and move its public-only `rores/global/AGENTS.md` and `GEMINI.md` by hand. Then: (O6)
   - `python3 maint/check.py` passes there;
   - the sync's leak scan finds nothing.
9. The lesson PR is open in ambysto-memory for the owner. (O5)

## Result

