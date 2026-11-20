---
status: shipped (PR #91) # draft → approved → planned → building → verified → shipped (PR #n) (approved by the owner, 2026-11-20: "approve")
---
# Layout by role: rules/, hooks/, tools/, maint/, so an agent finds each file by its job

Ticket: Plane APS-91.

## Problem
1. **Hooks are spread over six top-level folders.**
   - The folders are `gates/`, `graph/`, `guard/`, `hooks/`, `loop/` and `saveit/`.
   - Their names do not say they are hooks. They do not match where `install.py` puts them (`~/.claude/hooks/<name>/`).
   - `hooks/` holds only the agent-guard copy from 1prompt, with its pin and its boundary settings.
2. **`scripts/` mixes two jobs.**
   - Some are commands the main session runs every day: `dispatch.py`, `sdlc-check.py`, `plane.py`.
   - Others are tools that keep this repo itself in order: `install.py`, `check.py`, `sync-public.py`, `switch-model.py`.
   - An agent looking for "the command the rules tell me to run" has to read all twelve.
3. **Odd names and loose parts at the top.**
   - `rores/` holds the rules installed into `~/.claude`, but its name says nothing.
   - `switch-test/` sits at the top, away from its runner `scripts/switch-test.py`.
   - `public-sync.json` sits at the top, away from `scripts/sync-public.py`.
4. **No single place says where things live.** An agent learns the layout by listing folders and reading README.

## Outcome
1. **Top-level folders, each with one job:**
   - `rules/`: what `install.py` copies into `~/.claude`, namely `global/` (the global block and `settings-defaults.json`; on the public side also its `AGENTS.md` and `GEMINI.md`) and `agents/`. It was `rores/`.
   - `skills/`: unchanged.
   - `hooks/<name>/`: every file installed under `~/.claude/hooks/`, in a folder named exactly as its install folder. That means:
     - `hooks/1prompt/`: `agent-guard.py`, `pin.json`, `autonomous-settings.json`;
     - `hooks/gates/`, `hooks/owner-token-guard/`, `hooks/saveit/`, `hooks/graph/`;
     - `hooks/loop/`: `loop-stop.py` and `loop-wake.py`, both installed there.
   - `tools/`: exactly these six commands, which the main session runs in its daily work: `dispatch.py`, `sdlc-check.py`, `loop.py`, `plane.py`, `progress-diagram.py`, `hil-report.py`. `loop.py` is run from the repo and is not installed.
   - `maint/`: what keeps this repo and its installs in order. That is `install.py`, `check.py`, `sync-public.py` with its config, `switch-model.py`, `github-boundary.py` with its config, `cost-report.py` with its prices, and `maint/switch-test/`: the model-switch kit, holding its runner `switch-test.py` and everything now in `switch-test/`.
   - `docs/` and `intent/`: unchanged. `intent/` stays flat, since `converge` finds an intent by its plan's name.
   - At the top only: `CLAUDE.md`, `README.md`, `.gitignore`, `.gitattributes`, and `.claude/` (repo settings for the session gates, unchanged).
2. **`CLAUDE.md` opens with a "Where things live" table:** one row per job ("write a builder's contract", "check a plan against its branch", "install", "sync the public copy", …) giving the path. `check.py` fails when a file under `rules/`, `hooks/`, `tools/` or `maint/` is not named in the table, by its path or its folder's.
3. **No old path is left.**
   - `git grep` finds no old path outside `intent/` and `docs/reviews/`. An old path is a moved file's old repo path, or one of the old folders written as a path: `rores/`, `scripts/`, the top-level `switch-test/`. `intent/` and `docs/reviews/` are history and stay as written.
   - The paths are updated in the global rules, the agent files, the skills, README, `docs/internals.md`, the map in `docs/map/`, `public-sync.json`, the scripts and their self-tests.
   - No stub or forwarding file is left at an old path: a command that names one fails with "No such file" at once.
4. **Behaviour unchanged.**
   - Every self-test, `check.py` and `sdlc-check.py map .` pass. The map check and `docs/map/` come from the APS-88 build, which is merged before this starts.
   - `~/.claude` starts as installed from `main` just before the move. Running `install.py --global --settings` over it then leaves `--check` at exit 0, and the installed hook paths and settings entries are the same as before.
   - Files move with `git mv`, so `git log --follow` keeps each file's history.
5. **Lessons.** Each lesson in ambysto-memory that names an old path is updated in one PR there, for the owner to merge.
6. **The public copy follows.**
   - `sync-public.py` brings the new layout to the public repo; the public-only skills stay where they are.
   - `sync-public.py`'s own leak scan finds nothing.
   - The owner pushes and merges on the public side.

## Constraints
- Building starts only after the APS-88 build (PR #86) and the branch `aps-89-userflow-public-only` are merged into `main`. Then no open branch has to be rebased across a mass rename.
- Folders and their contents move; file names stay. No script changes behaviour. The only code edits are the paths each file uses to find another.
- Paths installed under `~/.claude` do not change, so a running session's hooks keep working through the move.
- **HARD here:** the global rules every session follows, the installer and the public copy all change together. The main session builds it; the hard-reviewer reviews it.

## Coverage
- Who: the main session that builds the move; every later session and subagent that runs a command the rules name; the owner, who reinstalls, merges the lesson PR and the public PR; `install.py`, `check.py`, `sync-public.py`, `converge` and its map check.
- Trigger: the owner asks for the folders to be ordered by role; building starts once the two open branches are merged.
- Main path: the open branches merge → move the folders with `git mv` → fix every path → the "Where things live" table → self-tests, `check.py`, the map check → install over the current install → review → merge → lessons PR → public sync.
- Branches and failures:
  - a path missed in a script: its self-test, `check.py`, or the install over the current install fails;
  - a path missed in prose: `git grep` for the old folders lists it;
  - a citation in `docs/map/` points at an old path: the map check lists it;
  - a session started before the move runs an old command: "No such file", and the reinstalled global rules give the new path;
  - another branch opened during the build: it rebases on the move, or the build waits.
- Data and states: the repo tree before and after the move; `~/.claude` before and after the install; the lesson PR; the public PR.
- Limits: no LLM cost beyond building and reviewing; one install; one public sync.

Flow: not needed: a move of files with one straight path and no user-facing steps.

## Out of scope
- Renaming files, merging or splitting scripts, or changing what any script does.
- Ordering `intent/` into subfolders.
- Changing the install locations under `~/.claude`, or 1prompt's own layout.
- Other repos' layouts.

## Open questions
None.
