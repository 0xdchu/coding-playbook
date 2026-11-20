---
status: verified # draft → planned → building → verified (plan accepted by the owner, 2026-11-21: "Chấp nhận", the boundary change included)
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
     - Built: only a `judge` whose file no longer exists is re-pointed. Re-pointing every judge would move a run that deliberately uses another checkout's judge, which the loop-stop self-test does (its fake `plane.py` sits beside a fake judge).
   - `maint/switch-test/switch-test.py`: the kit is its own folder, and the void markers are built from the kit's folder name (`switch-test/cases`, …). So a read of the kit through any checkout or either layout still voids a run.
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
   - The main checkout `~/work/ambysto/coding-playbook`, whose `tools/` the global block names: when it is on `main` with nothing uncommitted, `git pull --ff-only`; otherwise leave it and tell the owner (owner decision 2026-11-21).
   - Run `maint/install.py --global --settings` from the merged `main`, then `--check`.
   - Before the public sync starts: what-to-build's CoS (`cos/finish.py`, `cos/night_runner.py`, `cos/cos_sync.py`; the `cos-*` timers run them from the live checkout `~/work/0xdonniechu/what-to-build`) calls `plane.py` in the public clone. The sync works in that same clone: `git mv` and `--write` remove `scripts/plane.py` from its work tree at once. So that checkout must already hold the lookup that tries `tools/` first and `scripts/` second, which works in both layouts. Done 2026-11-21: what-to-build PR #103 merged (e9bf926), and the live checkout was pulled to it. The owner merges that repo's PRs. Its `projects/RER/CLAUDE.md`, `GEMINI.md` and (follow-up PR #104, cc732f3) the RER copy of the sdlc skill name the new paths. Those paths do not exist in the public clone until the public sync lands, so an RER session that runs `clarify` in that window gets "No such file" (fourth review; accepted, the window closes with the sync). The second and third reviews found this consumer: it builds the path from parts, so no grep saw it.
   - The public sync, on a branch of the public clone:
     - `git mv rores/global/AGENTS.md rores/global/GEMINI.md rules/global/` and commit, before `--write`. Otherwise `--write` deletes them: they are no longer public-only under their old names, and no `review` line reports them missing.
     - `--write`, then by hand: the paths in the public-only `CLAUDE.md`, `README.md`, `AGENTS.md`, `GEMINI.md`, `rules/global/AGENTS.md`, `rules/global/GEMINI.md` and `design-systems/README.md`; the table in its `CLAUDE.md`; the two `.sync-source.json` review records renamed to their `rules/global/` keys (or `--reviewed` both after reading them).
     - Its `maint/check.py`, then the owner merges.
     - After the owner's merge: put the public clone back on `main` and `git pull --ff-only`, because the `cos-*` units read it (fourth review). Delete the merged sync branch.
   - `maint/github-boundary.py` keeps the CODEOWNERS header it generates byte for byte (`… scripts/github-boundary.py.`), so repos already set up stay equal under `--check` (third review). Its output equals `main`'s for all 12 repos.
   - For the owner after the public merge: `~/.codex/AGENTS.md` and `~/.gemini/GEMINI.md`, the Codex and Gemini copies of the global rules, still name the old paths of the public clone. They differ from their public sources beyond the paths, so they are not overwritten. The same goes for the owner's own notes, which this work does not edit (fourth review). `~/.hermes/skills/claude-code-imports/sdlc/SKILL.md` names `<coding-playbook>/scripts/sdlc-check.py`. `~/.hermes/memories/MEMORY.md` and `~/.hermes/skills/management/plane-task-spec-standard/SKILL.md` name the private `~/work/ambysto/coding-playbook/scripts/…`, which breaks as soon as the main checkout is pulled. `aipub`'s `intent/2026-11-19-app-mockup.plan.md` is another repo's history.

## Risks
1. **A one-prompt run open at the move** keeps the old judge path, so its Stop hook can no longer find `converge`.
   - **Check:** just before the merge, no run file under `~/.claude/1prompt-runs/` points at a run that is open. Today 2 runs exist, both closed. A run closed earlier is re-pointed by `loop.py resume` (Files 2).
2. **A path missed in a script.** **Check:** `maint/check.py` runs every self-test, and Proof 5 installs over the current install.
   - Built: on `main`, `check.py` started four self-tests (`sync-public`, `session-gates`, `loop-wake`, `cost-report`) but never read their results. The third review found that `sync-public`'s had broken in the move. `check.py` now reads every self-test it starts, and a planted failure proves it. Still as on `main`: a self-test that hits its timeout raises `TimeoutExpired`, a traceback with a non-zero exit, not a FAIL line (fourth review, MINOR; left for a later ticket, since the exit is non-zero either way).
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
   git grep -nE '(^|[^/A-Za-z0-9_.-])(rores/|scripts/[a-z-]+\.(py|json)|loop/loop(-stop|-wake)?\.py|gates/session-gates\.py|graph/graph-hook\.py|guard/owner-token-guard\.py|saveit/saveit-hook\.py|hooks/(agent-guard\.py|pin\.json|autonomous-settings\.json)|switch-test/|public-sync\.json)' -- . ':!intent' ':!docs/reviews' ':!maint/public-sync.json' ':!maint/switch-test/*/*/task.md'
   ```

   It prints nothing. Paths installed under `~/.claude/hooks/…` do not match, since a `/` comes before them.
   A second grep covers what that rule cannot see, a path written after the repo's name or its placeholder (`~/work/ambysto/coding-playbook/scripts/…`, `<coding-playbook>/scripts/…`). It prints nothing too:

   ```
   git grep -nE '(coding-playbook>?)/(rores/|scripts/[a-z-]+\.(py|json)|loop/loop(-stop|-wake)?\.py|gates/|guard/|saveit/|graph/graph-hook|hooks/(agent-guard|pin|autonomous)|switch-test/|public-sync\.json)' -- . ':!intent' ':!docs/reviews' ':!maint/switch-test/*/*/task.md'
   ```

   The switch-test history (`known.md` and `runs/`) is renamed too (owner decision 2026-11-21: "Sửa cả lịch sử", after the first review). Each case's `task.md` is not history but the live prompt a candidate gets on a clone at the case's own commit, where the old paths are the real ones. So the three `task.md` files keep them, and both greps exclude them (`':!maint/switch-test/*/*/task.md'`). The second review found this, and the owner chose that fix (2026-11-21). `maint/switch-test/README.md` says which files hold which paths.
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

1. PASS: both greps print nothing, the switch-test history included, except the three `task.md` prompts (above). The first review found three `<coding-playbook>/scripts/sdlc-check.py` commands in the `sdlc` and `system-map` skills, which the first grep could not see. They are fixed, and the second grep now covers that form.
2. PASS: `git ls-tree --name-only HEAD` lists exactly `.claude .gitattributes .gitignore CLAUDE.md README.md docs hooks intent maint rules skills tools`. `ls hooks` gives `1prompt gates graph loop owner-token-guard saveit`.
3. PASS:
   - `python3 maint/check.py` passes, with the pin check run against the `ambysto-1prompt` clone.
   - It now reads all 17 self-tests it starts. Before the third review four were never read, and `sync-public`'s had broken: its scratch repos lacked the config's new `maint/` folder. That is fixed; it passes on Python 3.11, 3.12 and 3.14, and the other three pass. A planted failure of `sync-public`'s self-test in a scratch copy makes `check.py` exit 1, naming it.
   - The removed-row test, on a scratch copy without the `tools/plane.py` row: the first run passed, because the check also read the folder names in the text above the table. Fixed in 283caa9: it now reads only the table's rows, and its inline case covers that text. Rerun: exit 1, `CLAUDE.md: tools/plane.py is not named in '## Where things live'`.
   - `python3 tools/sdlc-check.py map .`: 0 gaps.
   - `tools/sdlc-check.py converge` on this plan: PASS, 0 gaps. Its `floor:` notes say assertions were removed in the old paths (`scripts/sdlc-check.py`, …). They are the renames: converge compares a file by its path and does not follow a rename, so every assertion that moved reads as removed. No test was deleted; the self-tests run as before through `maint/check.py`.
4. PASS: `git diff -M --name-status origin/main HEAD` gives 63 renames and 2 delete-and-add pairs: the two switch-test reports whose renamed paths changed more than half their text, so git does not pair them (their content is the old report with the paths renamed). `git log --follow` shows 18 commits for `tools/sdlc-check.py`, the oldest from 2026-11-10; 22 for `hooks/gates/session-gates.py`, from 2026-11-11; and 52 for `rules/global/CLAUDE.md`, from 2026-10-16.
5. PASS on a scratch `HOME` holding a copy of `settings.json`, `CLAUDE.md`, `agents/`, `hooks/` and `skills/`:
   - Installed from `origin/main` (`scripts/install.py --global --settings`): `--check` exit 0.
   - Installed from this branch (`maint/install.py --global --settings`) over it: `--check` exit 0.
   - The `settings.json` hook entries and the list of installed files are identical before and after.
   - The real `~/.claude` is checked after the merge.
6. PASS: every repo path the global block names exists: `tools/dispatch.py`, `tools/sdlc-check.py`, `tools/hil-report.py`, `maint/switch-model.py`, `hooks/loop/loop-wake.py`, and `~/work/ambysto/coding-playbook/tools/{loop,plane,progress-diagram}.py`.
7. PASS, 8 of 8. A fresh Sonnet 5.5 agent was given only `CLAUDE.md` and the file list, and answered:
   - contract `tools/dispatch.py`;
   - converge `tools/sdlc-check.py`;
   - owner log `tools/hil-report.py`;
   - ticket `tools/plane.py`;
   - progress `tools/progress-diagram.py`;
   - start a run `tools/loop.py`;
   - install `maint/install.py`;
   - public copy `maint/sync-public.py` with `maint/public-sync.json`.
   It found each one in the table. It inferred only that `start` is one of `loop.py`'s commands.
8. PASS, on a scratch clone of public `main`:
   - This branch's `maint/sync-public.py --write` (source `HEAD`) wrote 64 renames and 5 updates, and the leak scan did not refuse.
   - Then by hand: `rores/global/AGENTS.md` and `GEMINI.md` moved to `rules/global/`, the paths in the public-only `CLAUDE.md`, `README.md`, `AGENTS.md` and `GEMINI.md` renamed, and the table added.
   - Its `python3 maint/check.py` passes, with 13 skills.
   - The real public PR does the hand steps listed in Files 7, which the first review made precise: `git mv` the two public-only rule files before `--write`, `design-systems/README.md`, and the `.sync-source.json` keys.
9. PASS: ambysto-memory PR #50 updates `long-run-coding-is-1prompt`, for the owner to merge. The other lessons name scripts only by file name, which stays true.

Review: hard-reviewer, four rounds (the owner authorised rounds 3 and 4). Rounds 1 to 3 FAIL, every issue fixed above. Round 4 PASS at ba187db with four MINORs, recorded in Files 7 and Risk 2. Just before the merge, no one-prompt run is open: two are closed, and a third points at no run file.
