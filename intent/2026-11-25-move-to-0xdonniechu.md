---
status: approved   # draft → approved → planned → building → verified → shipped (PR #n)
---
# Move coding-playbook and 1prompt to 0xdonniechu (APS-97)

## Problem
The playbook every session on this machine follows lives in the Ambysto account (`ambysto/coding-playbook`, private, 363 commits) and is copied through a filter into a public repo `0xdonniechu/coding-playbook` (130 commits). Its builder guard comes from another Ambysto repo (`ambysto/1prompt`), its tickets are in Ambysto's Plane project APS, and it sets GitHub rules for 11 Ambysto repos. The owner wants the playbook rooted in 0xdonniechu, public, and separate from Ambysto (owner, 2026-11-25).

Owner decisions (2026-11-25):
- One public repo, `0xdonniechu/coding-playbook`, is the source of truth; no private copy, no filtered sync.
- History: one snapshot commit of the current tree on top of the public repo's history. The 363 private commits stay private in `ambysto/coding-playbook`, archived read-only.
- `ambysto/1prompt` (public, the agent-guard source) moves to 0xdonniechu as a whole repo.
- Tickets go to a new Plane project; APS keeps its old tickets as history.
- The old private clone stays read-only for the switch-test kit (amended during the build, 2026-11-25).
- No more merges to `ambysto/coding-playbook` from now on (freeze, 2026-11-25).
- The Ambysto GitHub rules config moves to a new private repo `ambysto/ambysto-governance`.
- 1prompt follows the playbook's merge rule after the move.
- Once public: the main session merges a playbook change itself after `check.py` and review; a change of a rule or a model still needs the owner's approval, as today.

## Outcome
1. After one snapshot commit, the tree of `0xdonniechu/coding-playbook` main is: every file of `ambysto/coding-playbook` main (machine paths `/home/<user>` rewritten to `~`), plus every file only the public repo has today (`skills/graph`, `skills/mockup`, `skills/userflow`, `skills/static-mockup-visuals`, `design-systems/`, the AGENTS and GEMINI copies). For the three files both have: `CLAUDE.md` is the private one with Outcome 8's changes; `README.md` is the public one, extended to name what came in; `.claude/branch-name.json` uses the new Plane key. The leak check (Outcome 7) finds nothing in this tree.
2. As the last step, `ambysto/coding-playbook` is archived (read-only, private). Its local clone `~/work/ambysto/coding-playbook` stays, on `main`, only for the switch-test kit, whose cases are diffs in its history (owner, 2026-11-25); nothing else on this machine reads it, and nothing writes it.
3. `0xdonniechu/1prompt` exists with its full history (a GitHub transfer); `gh api repos/ambysto/1prompt --jq .full_name` prints `0xdonniechu/1prompt`.
4. The local clones are `~/work/0xdonniechu/coding-playbook` (the existing public clone) and `~/work/0xdonniechu/1prompt` (was `~/work/ambysto/ambysto-1prompt`), both committing as 0xdonniechu; once Outcome 5 passes, the old 1prompt clone is gone from `~/work/ambysto/` (moved), and the old playbook clone stays only as Outcome 2 says.
5. Every path on this machine that named `~/work/ambysto/coding-playbook` or `~/work/ambysto/ambysto-1prompt` names the new folder: the global block, hooks, the wake timer, the `gh` wrapper, the 1prompt pin. `python maint/install.py --check` exits 0 from the new clone.
6. A session started after the move runs a Bash call, a builder dispatch with a contract, and `loop.py status` without an error.
7. `check.py`, the gate every playbook merge runs, fails when a tracked file matches a leak pattern: the patterns in `maint/public-sync.json` today (secret shapes, internal names) plus `/home/<user>` paths. The filtered sync (`sync-public.py`, `public-sync.json`) is gone. No GitHub CI is added.
8. The playbook repo's `CLAUDE.md` says what a merge to main publishes and the merge rule above. `~/work/ambysto/CLAUDE.md` and the `gh` wrapper no longer name coding-playbook or 1prompt; the bot rule stays for `ambysto-memory` only.
9. A new Plane project exists for the playbook and 1prompt; `plane.py projects` lists it; the playbook's branch-name rule uses its key.
10. The GitHub rules for the 11 Ambysto repos (repo list, rulesets, CODEOWNERS) are set from a new private repo `ambysto/ambysto-governance` (owner, 2026-11-25); the public playbook no longer names those repos.
11. Other repos that name the old paths today (the repos listed in the ticket, `ambysto-memory` among them) name the new ones: 0xdonniechu repos by this work, Ambysto repos by one PR each, `ambysto-memory` by a PR the owner merges. Check: a search of `~/work` for `ambysto/coding-playbook` and `ambysto-1prompt` finds only history (intent files, changelogs).

## Constraints
- No session on this machine may be left with a missing hook: a missing hook blocks every Bash call (playbook `CLAUDE.md`). Install the new copy before the old folder goes.
- Two identities never mixed: nothing under `~/work/0xdonniechu/` commits as Ambysto; nothing uses `gh auth switch`.
- No private business detail of the owner's products reaches the public repo (owner, 2026-11-08).
- Transfer to a user account waits for that account to accept; only the owner can accept (lesson `transfer-repo-to-a-user-account`).
- Standard library Python only, as today.

## Coverage
- Who: the owner (accepts the 1prompt transfer, approves this intent); the main session (moves, edits, merges); the `ambysto` GitHub account (starts the 1prompt transfer, archives the old repo); the `0xdonniechu` account (owns both repos after); Plane; every Claude Code session on this machine through the installed copy in `~/.claude`; other repos that cite the old paths.
- Trigger: a one-off move, started after this intent is approved.
- Main path: no open PR or unmerged branch in the old repo is lost → snapshot into the public repo → new clone installed and checked → 1prompt transferred, accepted, re-cloned, its pin updated → Ambysto ties removed (rules list, `CLAUDE.md` lines, `gh` wrapper entries) → new Plane project → old repo archived → old paths updated elsewhere.
- Branches and failures:
  - The leak check finds a hit in the snapshot: stop; nothing is pushed until the owner decides.
  - The owner has not accepted the 1prompt transfer: the playbook part goes on; the 1prompt paths stay old until acceptance.
  - `install.py --check` differs after the switch: fix before any old folder is removed.
  - A one-prompt run is open (`loop.py status`) or another session is working in either clone: stop and ask; do not move folders under a running loop.
  - Unmerged branches in the old repo (`aps-89`, `aps-90`, `aps-92`, `aps-96` today): listed for the owner; any with work not on main is carried over or dropped by the owner's word.
- Business rules: nothing secret, no machine path and no private business detail is published; each repo has one source of truth; no old folder is deleted before the new copy passes `install.py --check`; GitHub keeps the archived repo, nothing is deleted on GitHub.
- Data and states: repo ownership and visibility on GitHub; local folders; the installed copy in `~/.claude` (global block, hooks, `settings.json` entries, skills, systemd user units); Plane projects; the 1prompt pin.
- Security and privacy: everything in the playbook becomes public, including owner decisions and ticket ids already in the tree; the leak check guards every later commit; agent-guard and the owner-token guard keep working through the switch; 1prompt follows the playbook's merge rule after the move (owner, 2026-11-25): a change to agent-guard is HARD, so the hard-reviewer reviews it and the main session merges after a PASS; a change of what it allows or refuses still needs the owner's approval as a rule change
- UI states: N/A: no screen; command-line checks print their own results (`check.py`, `install.py --check`, `sdlc-check.py`).
- Limits: no session is without hooks at any time; the switch itself in one session, with no other agent running.

Flow: not needed: one straight sequence with stop points, written in Main path and Branches above.

## Out of scope
- Changing what any rule, guard or skill says, beyond paths, identity and the merge rule above.
- Moving other Ambysto repos, `ambysto-memory`, or `ambysto-graph` / `ambysto-saveit` tools.
- Rewriting history of either repo.
- Other machines: they run `install.py` from the new clone the next time they are used; this work lists the steps.

## Open questions
None.
