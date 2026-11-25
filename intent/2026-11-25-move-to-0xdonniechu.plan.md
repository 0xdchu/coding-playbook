status: building # draft → planned → building → verified

# Plan: move coding-playbook and 1prompt to 0xdonniechu (APS-97)

Intent: `intent/2026-11-25-move-to-0xdonniechu.md` (approved 2026-11-25).

Two working trees: **P** = the private clone `~/work/ambysto/coding-playbook` (source, read-only after T1), **Q** = the public clone `~/work/0xdonniechu/coding-playbook` (where the merged tree is built, commits as 0xdonniechu). Q's branch rule is `(feat|fix)/…`; the merged tree replaces it with the new Plane key, so the branch is `cpb-1-merge-internal` (renamed from `feat/merge-internal` once the new rule was in the tree).

## Files

In order of work:
1. Plane: a new project `CPB · Coding Playbook` (T1).
2. In Q, on `cpb-1-merge-internal`: every file of P's `main` (copied from `git archive`, not the work tree), Q's own files kept; then
   - `CLAUDE.md` (P's, rewritten: repo is public, what a merge publishes, merge rule, identity, Plane CPB, no sync row, no Ambysto rules row), `README.md` (Q's, plus the rows P's README has), `.claude/branch-name.json` (`cpb-[0-9]+-…`, no push to main);
   - `rules/global/CLAUDE.md`: `~/work/ambysto/coding-playbook` → `~/work/0xdonniechu/coding-playbook`;
   - `maint/check.py`: public-only skills become ordinary skills (`SKILLS` gains graph, mockup, userflow, static-mockup-visuals); the sync and github-boundary self-tests and checks go; a leak check over every tracked file (patterns moved from `public-sync.json` into `maint/leak-patterns.json`, plus `/home/[a-z]`); the 1prompt pin check looks for `../1prompt`;
   - `maint/install.py`: never writes into an installed skill folder that is a symlink resolving outside this repo; prints `skipped <name>: symlink to <target>` instead;
   - removed: `maint/sync-public.py`, `maint/public-sync.json`, `maint/github-boundary.py`, `maint/github-boundary.json`;
   - `hooks/1prompt/pin.json` `repo` → `0xdonniechu/1prompt`; `maint/install.py`, `maint/check.py` comments naming `ambysto/1prompt`;
   - `docs/internals.md` (sync and boundary sections out, leak check and install skip in), `README.md` table rows for removed files;
   - `maint/switch-test/` probes and cases naming `ambysto/coding-playbook` or `ambysto-1prompt`: new paths;
   - `docs/map/*`: re-rendered with the `system-map` skill after the edits, so its citations hold;
   - every `/home/<user>` in tracked files → `~`.
3. GitHub `ambysto/ambysto-governance` (new, private) and its clone `~/work/ambysto/ambysto-governance`: `github-boundary.py`, `github-boundary.json` (the 11 repos; `coding-playbook` dropped from the list), `README.md`, `CLAUDE.md` (T3).
4. 1prompt (T4): GitHub transfer `ambysto/1prompt` → `0xdonniechu/1prompt`; clone moved to `~/work/0xdonniechu/1prompt`, remote reset, repo-local identity removed; its `CLAUDE.md` loses the `ambystobot` rule and gains the playbook's merge rule, by a PR there. To match the owner's merge rule, its main ruleset drops code-owner review and last-push approval (a PR, no force push, no deletion and the tag lock stay), `.github/CODEOWNERS` goes, and the `ambysto` and `ambystobot` collaborators are removed. Its scrub list holds the owner's handle, so no file there names the new owner.
5. Outside any repo (T4, T6): `~/.local/bin/gh` (drop the `ambysto-1prompt` and `ambysto/1prompt` cases), `~/work/ambysto/CLAUDE.md` (drop coding-playbook and 1prompt from the bot bullet and anywhere else), `~/.claude/` through `install.py` from Q.
6. Other repos (T7): the repos listed in the ticket, `ambysto-memory` among them (PR, owner merges).
7. Last (T8): archive `ambysto/coding-playbook` on GitHub; its clone `~/work/ambysto/coding-playbook` stays on `main`, read-only, for the switch-test kit (owner, 2026-11-25). `~/work/ambysto/ambysto-1prompt` is already gone (moved in T4).

## Risks

1. **Installer writes into BYFA.** `~/.claude/skills/mockup` and `userflow` are symlinks into `~/work/0xdonniechu/BYFA-skills`; the merged tree has its own `skills/mockup` and `skills/userflow`, and today's installer would back up and overwrite BYFA's files through the link. **Check:** install.py skips them (T2); after `install.py`, `git -C ~/work/0xdonniechu/BYFA-skills status --porcelain` is empty and `readlink` of both links is unchanged. Which copy of the two skills is canonical stays a separate owner decision (out of this intent's scope).
2. **A session without hooks.** Hooks run from `~/.claude/hooks`, not from the repo (checked: no hook command in `settings.json` names a repo path), so removing P does not break them. **Check:** `install.py --check` from Q exits 0 before T8, and a headless `claude -p` smoke run after T6.
3. **Something private is published.** **Check:** the new leak check in `check.py` on Q's branch, plus a manual read of the files that only P had (`git diff --stat` of the merge commit), plus a grep for the owner's product names and e-mail; hard-reviewer review before the merge. The merge to Q's main is the point of no return.
4. **The global block names the old path between T6 and the last session that started before it.** Sessions started earlier keep their loaded text; `dispatch.py` and `plane.py` calls at the old path fail after T8. **Check:** T8 runs only after `ps` shows no other `claude` process with a cwd under `~/work/ambysto/coding-playbook`; the owner is told to restart open sessions.
5. **1prompt transfer not accepted.** **Check:** `gh api repos/0xdonniechu/1prompt --jq .full_name`; until it prints, T4's local steps wait and the pin still says `ambysto/1prompt` (Q's `pin.json` change lands with T4's commit, not T2's).
6. **Pin check after the folder move.** `check.py` reads `../ambysto-1prompt` today. **Check:** `check.py` from Q with `~/work/0xdonniechu/1prompt` present prints no "no clone" note.
7. **ambysto-governance loses a working tool.** **Check:** `python3 github-boundary.py --self-test` passes in the new repo, and a `--check` (read-only) run against the 11 repos reports no drift.
8. **Branch rules.** P requires `aps-N-…`, Q requires `(feat|fix)/…` until the merged `branch-name.json` lands. T2 uses Q's current rule; later work uses `cpb-N-…`.

Design: not needed: no new component, data store or outside service; one new private repo holds an existing script and its config.

## Tasks

### T1 (main) Plane project CPB
- allow: `intent/2026-11-25-move-to-0xdonniechu.plan.md`
- check: `python3 tools/plane.py projects`

### T2 (main) Build the merged tree in the public clone
- allow: `**`
- check: `python3 maint/check.py`
- check: `python3 maint/install.py --check`

### T3 (main) ambysto-governance
- allow: `intent/2026-11-25-move-to-0xdonniechu.plan.md`
- check: `python3 maint/check.py`

### T4 (main) Transfer 1prompt
- allow: `hooks/1prompt/pin.json` `maint/check.py` `intent/2026-11-25-move-to-0xdonniechu.plan.md`
- check: `python3 maint/check.py`

### T5 (main) Review and merge to public main
- allow: `intent/2026-11-25-move-to-0xdonniechu.plan.md`
- check: `python3 maint/check.py`

### T6 (main) Install from the new clone and smoke-test
- allow: `intent/2026-11-25-move-to-0xdonniechu.plan.md`
- check: `python3 maint/install.py --check`

### T7 (main) Update other repos
- allow: `intent/2026-11-25-move-to-0xdonniechu.plan.md`
- check: `python3 maint/check.py`

### T8 (main) Archive and remove the old clones
- allow: `intent/2026-11-25-move-to-0xdonniechu.plan.md`
- check: `python3 maint/install.py --check`

## Proof

1. Q's main tree equals P's main tree (paths rewritten) plus Q's own files, with the three shared files as Outcome 1 says: a script compares `git ls-tree -r` of both against the merge commit and lists every difference with its reason. (O1)
2. `python3 maint/check.py` on Q's main passes, including the leak check over every tracked file; `git grep -nE '/home/[a-z]'` and a grep for the owner's product names on Q's main find nothing unexplained. (O1, O7)
3. `gh api repos/ambysto/coding-playbook --jq .archived` prints `true`; `~/work/ambysto/coding-playbook` is on `main`, clean, and named only by the switch-test kit. (O2)
4. `gh api repos/ambysto/1prompt --jq .full_name` prints `0xdonniechu/1prompt`. (O3)
5. In both new clones `git config user.name` prints `0xdonniechu` and `git remote get-url origin` names `0xdonniechu`; `~/work/ambysto/ambysto-1prompt` does not exist. (O4)
6. `python3 maint/install.py --check` from Q exits 0; `grep -c 'ambysto/coding-playbook\|ambysto-1prompt' ~/.claude/CLAUDE.md ~/.local/bin/gh ~/.claude/hooks/loop/loop-wake.py` prints 0 for each; `pin.json` names `0xdonniechu/1prompt`. (O5)
7. A headless `claude -p` session in a scratch repo runs a Bash call, `python3 ~/work/0xdonniechu/coding-playbook/tools/dispatch.py --help`, and `loop.py status` without an error; BYFA-skills is clean and its two symlinks unchanged. (O6)
8. A tracked test file with a fake `ghp_` token makes `check.py` fail; removing it makes it pass. (O7)
9. Q's `CLAUDE.md` has the sections "What a merge publishes" and the merge rule; `grep -n 'coding-playbook\|1prompt' ~/work/ambysto/CLAUDE.md` finds nothing. (O8)
10. `plane.py projects` lists `CPB`; Q's `.claude/branch-name.json` pattern starts with `cpb-`. (O9)
11. `ambysto/ambysto-governance` exists, private; its self-test passes and a read-only check runs; `git grep -n ambysto-gate` in Q finds nothing from the boundary config. (O10)
12. `grep -rIl 'ambysto/coding-playbook\|ambysto-1prompt' ~/work` lists only history (intent files, changelogs, the archived clone is gone), and the Ambysto PRs and the `ambysto-memory` PR are open or merged, linked in APS-97. (O11)
13. Q's `README.md` says how to install from the public clone and names what came in from the private repo (read it, section "Install"). (O5)

## Result


1. PASS. Private `origin/main` (b7b3586, APS-98 included) against this branch: only-private are the six removed files (`maint/sync-public.py`, `maint/public-sync.json`, `maint/github-boundary.py`, `.json`, `docs/map/runtime-sync.json`, `.html`); only-here are the public files (AGENTS and GEMINI copies, `design-systems/` 31, `skills/graph/` 76, `skills/mockup/` 12, `skills/userflow/` 2, `skills/static-mockup-visuals/` 1, two public intents and plans), this plan and `maint/leak-patterns.json`; files in both differ only where this work edits them (CLAUDE.md, README.md, branch-name.json, internals, map, pin, check.py, install.py, the global block, this intent) and in `intent/2026-11-10-sdlc-tasks-converge-clarify.md`, which keeps the public wording without the upstream repo names.
2. PASS. `check.py` on the branch: PASS (14 skills, leak check over every tracked file); the pin check ran against `../1prompt` (no "no clone" note). `git grep -nE '/home/[a-z]'` finds only the `/home/x/` test placeholders in `owner-token-guard.py`; product names appear only in existing public files (none describes how a product posts), none in this intent or plan. Internal names moved to a machine-local term list (review round 1).
3. not run: T8 waits. A session (APS-101) is working in `~/work/ambysto/coding-playbook` and its worktree `coding-playbook-aps101`; Risk 4 holds the archive until no session runs there. That session was told the private repo is frozen.
4. PASS. `gh api repos/ambysto/1prompt --jq .full_name` prints `0xdonniechu/1prompt`.
5. PASS for 1prompt: `~/work/0xdonniechu/1prompt`, origin `github.com/0xdonniechu/1prompt`, `user.name` 0xdonniechu, `gh api user` 0xdonniechu; `~/work/ambysto/ambysto-1prompt` does not exist. This clone: origin `0xdonniechu/coding-playbook`, author 0xdonniechu.
6. PASS. `install.py --global --settings` from this clone, then `install.py --check` exit 0; the old names count 0 in `~/.claude/CLAUDE.md`, `~/.local/bin/gh` and `loop-wake.py`; the global block names the new path 7 times; `pin.json` names `0xdonniechu/1prompt`. APS-100 (merged in the private copy after the snapshot) was missing from the first install for two minutes; it came in by PR #25 and was installed again, and the running APS-101 session was told.
7. PASS. Headless `claude -p` in a scratch git repo ran Bash, `dispatch.py --help` (usage printed) and `loop.py status` (no run, as expected); BYFA-skills clean, both symlinks unchanged, the installer printed `skipped` for both.
8. PASS. A tracked `leak-probe.txt` with a fake `ghp_` token: `check.py` FAIL naming the file and pattern; removed, PASS.
9. PASS for the repo files: CLAUDE.md Rules say a merge publishes the files and nothing else, and the merge rule; `~/work/ambysto/CLAUDE.md` names neither coding-playbook nor 1prompt.
10. PASS. `plane.py projects` lists `CPB Coding Playbook`; `.claude/branch-name.json` pattern `cpb-[0-9]+-…`.
11. PASS. `ambysto/ambysto-governance` is PRIVATE; `github-boundary.py --self-test` PASS; `--check` ran read-only (drift as before: rulesets applied only where GitHub allows); no boundary config here.
12. PASS for the repos this work owns: marketing-team PR #10 and what-to-build PR #123 merged; the aipub landing PR is open in its new owner's repo (it moved out of Ambysto, PR 74); the `ambysto-memory` PR #55 waits for the owner. Left as history: intents and reviews here, the private clone and its worktree, gitignored HANDOFF files, brand asset file names in `ambysto-assets`.
13. PASS. `README.md` section "Install" says how to install from this clone and names what came in from the private copy.
