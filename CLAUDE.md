# coding-playbook: which model does which job in Claude Code, and the skills and scripts that go with it

## Where things live
One row per job. `maint/check.py` fails when a file under `rules/`, `hooks/`, `tools/` or `maint/` is named here neither by its path nor by a folder above it: add a row when you add one.

| Job | Path |
|---|---|
| Write a builder's task contract (its own worktree, or the main checkout) | `tools/dispatch.py` |
| Check an intent (`clarify`), a plan against its branch (`converge`), a repo's map (`map`) | `tools/sdlc-check.py` |
| Start, hold, pass, fail, ask, stop or resume a one-prompt run | `tools/loop.py` |
| Move or comment on a Plane ticket | `tools/plane.py` |
| Draw a plan's progress diagram | `tools/progress-diagram.py` |
| Read the owner time log | `tools/hil-report.py` |
| Install into `~/.claude`, or check the install (`--check`) | `maint/install.py` |
| Verify this repo: frontmatter, pins, every self-test, this table | `maint/check.py` |
| The leak patterns `check.py` refuses in any tracked file | `maint/leak-patterns.json` |
| Switch a role's model | `maint/switch-model.py` |
| Test a candidate model before a switch (runner, cases, runs, release-day list) | `maint/switch-test/` |
| The cost report and its prices | `maint/cost-report.py`, `maint/model-prices.json` |
| The builder and reviewer guard and an autonomous run's settings, copied from 0xdonniechu/1prompt and pinned | `hooks/1prompt/` (installed in `~/.claude/hooks/1prompt/`) |
| The session gates: branch names, trees under review, lesson recall | `hooks/gates/` (`~/.claude/hooks/gates/`) |
| The owner-token guard | `hooks/owner-token-guard/` (`~/.claude/hooks/owner-token-guard/`) |
| The save-it hooks: brief at session start, save the tail before compaction | `hooks/saveit/` (`~/.claude/hooks/saveit/`) |
| The session graph hook | `hooks/graph/` (`~/.claude/hooks/graph/`) |
| The one-prompt Stop hook and the wake timer | `hooks/loop/` (`~/.claude/hooks/loop/`) |
| The global block and the settings defaults; its Codex and Gemini versions (`AGENTS.md`, `GEMINI.md`, kept here by hand) | `rules/global/` (into `~/.claude/CLAUDE.md` and `settings.json`) |
| The four subagents | `rules/agents/` (`~/.claude/agents/`) |
| The skills | `skills/<name>/` (`~/.claude/skills/`) |
| The design systems (CSS libraries the mockup skill reads) | `design-systems/` |
| This repo's map | `docs/map/` |
| How the scripts work inside, and their known gaps | `docs/internals.md` |
| Intents and plans | `intent/` |


## What it does
The four subagents (builder, reviewer, hard-reviewer, transcriber), the global instructions, fourteen skills (`starter-kit`, `handoff`, `sdlc`, `teardown`, `orca-worktree-setup`, `agent-team`, `create-skill`, `secrets`, `whats-next`, `system-map`, `mockup`, `static-mockup-visuals`, `graph` and `userflow`), the builder dispatch and sdlc check scripts, a one-command model switch and the switch test kit, the agent-guard hooks, the owner-token guard and the save-it hooks, the Plane and progress-diagram scripts, the one-prompt loop (`tools/loop.py` and its Stop hook), the session graph hook, the session gates, the owner time log report, the cost report, plus a check script and an installer. Standard library Python only. Every session on every machine follows these files, so a wrong rule rates HARD work as EASY or lets an unreviewed change through.

## Verify
- `python3 maint/check.py`: agent frontmatter and pinned models, `hard-reviewer` body equal to `reviewer` body, `rules/global/CLAUDE.md` matches the pins, the starter-kit template's sections, skill frontmatter, `settings-defaults.json`, and the self-tests of `dispatch.py`, `sdlc-check.py`, `switch-model.py`, `hooks/saveit/saveit-hook.py`, `plane.py`, `progress-diagram.py`, `hooks/graph/graph-hook.py` (a fake `ambysto-graph` and `systemd-run` on a scratch repo: refresh, skip with no change, lock, failing or killed jobs keeping the old graph, the start lines), `tools/loop.py` and `hooks/loop/loop-stop.py` (the run file and the Stop hook on scratch repos and plans: gaps and failing checks block, reviewer verdicts recorded and required, done, two fails, three check rounds, idle, the time limit, the ticket comment, never trapping a session), `maint/cost-report.py` (scratch transcripts), the leak check over every tracked file (`maint/leak-patterns.json`), `hooks/loop/loop-wake.py --self-test` (a fake `claude`, `systemd-run`, `systemctl` and `plane.py` in a scratch HOME: a dead quiet run woken once and bound to the fork, every reason not to wake, each cap closing the run, the spend ledger, the timer install), plus `install.py --settings` registering the session hooks once each and a refusal writing nothing (scratch HOMEs).
- `HOME=$(mktemp -d) python3 maint/install.py --settings` then `--check` under the same `HOME`: installs and reports no drift (exit 0), without touching `~/.claude`. Without `--settings` the install skips the session hook entries in `settings.json`, and `--check` reports them as drift (exit 1).
- A change to an agent's behaviour: start a new session, run the agent once on a known diff, and record what it returned in the PR.
- A change to a skill's steps: run it once in a fresh agent on a scratch repo, given only the skill, and record where it had to guess.

## HARD: the main session does it directly, then hard-reviewer
Rated by undo cost (global "Task rating", owner decision 2026-11-11): HARD here is what no revert undoes (a guard that let something through, money spent, something published, a setting the installer spread to every machine) and any change of a rule (what the global block, a skill's steps or an agent's instructions tell a session to do or not do). Read an item's section in `docs/internals.md` before changing it.
- The model choice and switching: the "Current choice" line, any agent's `model:` or `effort:`, `maint/switch-model.py`.
- Task rating (EASY / MEDIUM / HARD), the review loop, who may commit or merge, the honesty rules.
- The reviewers' checklist and their PASS/FAIL rule.
- `tools/dispatch.py`: the task contract a builder works to, which `hooks/1prompt/agent-guard.py` enforces, and the task parser in `tools/sdlc-check.py` that `--task` reads it from (`converge` also prints `floor:` notes for added suppressions, skipped/deleted tests and removed assertions).
- `tools/loop.py` and `hooks/loop/loop-stop.py`: the one-prompt run, its evidence-based done and verdicts per task.
- `hooks/loop/loop-wake.py`: waking a dead run under spend caps.
- `hooks/gates/session-gates.py` and `.claude/branch-name.json`: the session gates (branch names, no push to `main`, trees a running subagent read, lesson recall); a gate that wrongly allows lets the slip through, one that wrongly refuses stalls every session.
- The installer's writes to `~/.claude` (backups, the marker block, which also takes over a block left by an earlier `coding-playbook` or `claudecode-guide` install, skill folders, `hooks/saveit`, `hooks/loop`, `hooks/graph` and `hooks/gates`, and with `--settings` the entries of `rules/global/settings-defaults.json` and the session hook entries in `settings.json` (PreToolUse, SessionStart, PreCompact, Stop, SubagentStop, SessionEnd; an entry already there is brought to this repo's timeout), each appended once beside any other hooks; it never sets the model and never deletes).

## MEDIUM: builder builds, reviewer reviews
- Builder and transcriber wording that changes what they do or when they stop; the template's sections; a skill's steps or stop points; `maint/check.py`; `tools/sdlc-check.py`.
- Shortening or rewording `rules/global/CLAUDE.md` or a skill without changing a rule: the reviewer compares the old and new text rule by rule; a rule found changed makes the change HARD.
- `hooks/graph/graph-hook.py` (the session graph): it must never block or break a session (exit 0, `|| true`) and writes only under `<git dir>/progress-diagram/`.
- `docs/internals.md`, `tools/plane.py`, `tools/progress-diagram.py`, `tools/hil-report.py`, `maint/cost-report.py`.

## EASY: transcriber or builder, no review
- README wording, typos, examples that do not change a rule, intent and plan status lines that record work done.

## Rules
- Models are pinned to full model IDs (`claude-opus-5-5`), never aliases. A model change edits every agent file, the "Current choice" line and the README in one PR (`maint/switch-model.py` does it in one command).
- The body of `hard-reviewer.md` is the body of `reviewer.md`: edit `reviewer.md`, then copy its body; `check.py` fails otherwise.
- Universal only: no project's paths, commands or names in `rules/agents/`, `rules/global/` or `skills/`. Three exceptions: `rules/global/CLAUDE.md` names this repo's own folder (`~/work/0xdonniechu/coding-playbook`) where it points at `dispatch.py`, `hil-report.py`, `tools/loop.py`, `progress-diagram.py`, `plane.py` and the switch-test kit; its Tools section names the owner's local tools (`ambysto-saveit`, `ambysto-graph`, Plane) because every session needs to know them (owner instruction 2026-11-10: load the existing tools, one step at a time); it tells a session to skip a tool that is not installed; and "The loop" names `ambysto-memory` as the repo where GitHub keeps merges with the owner.
- Nothing secret: no keys, tokens, hosts or ids.
- Public, and the only copy (owner decision 2026-11-25, APS-97): this repo is the source of truth; the internal `ambysto/coding-playbook` is archived and nothing is synced. A push of any branch already publishes its files (anyone can read a public branch), and a merge to `main` publishes them as the repo's content and nothing else (no site, no package, no deploy): run `check.py` before every push. `check.py` refuses a tracked or new file that matches `maint/leak-patterns.json` or a term in the machine-local `~/.config/coding-playbook/leak-terms.txt`; a pattern catches shapes, not every secret, so the review still reads the whole diff for keys, hosts, ids, e-mails and the owner's private business. The Codex and Gemini files (`AGENTS.md`, `GEMINI.md`, `rules/global/AGENTS.md`, `rules/global/GEMINI.md`, `skills/starter-kit/project-AGENTS.md`, `skills/starter-kit/project-GEMINI.md`) are kept by hand beside their Claude versions and stay universal like `rules/global/CLAUDE.md`.
- The builder's task contract is enforced by `hooks/1prompt/agent-guard.py`. The main session still reruns the contract's checks and runs `sdlc-check.py converge` before review.
- `hooks/1prompt/agent-guard.py` and `hooks/1prompt/autonomous-settings.json` are copied from `0xdonniechu/1prompt` at the commit `hooks/1prompt/pin.json` names: change them there, copy them here, update the pin.
- Git: English only; the `0xdonniechu` account (check with `gh api user --jq .login` before the first PR of a session; do not switch accounts); branches `cpb-N-slug` (Plane project CPB), never a push to `main`; only the main session commits, pushes, opens and merges PRs: this repo is public, so a merge publishes to its readers; it merges on its own (owner decision 2026-11-25, APS-97) once the whole Verify passed on the branch and the review passed (a change of model, rating or review rule needs the owner's approval first), then deletes the branch and its worktree (owner decision 2026-11-11).

## Read when
- Changing a hook or script in the HARD list: its section in `docs/internals.md` first (how it works inside, its limits).
- Changing the switch script: `maint/switch-model.py --self-test` runs it on a scratch copy of this repo.
- Adding a skill: add its name to `SKILLS` in `maint/check.py`, or to `MORE_SKILLS` with its self-test script and trigger prompts.

## Session state
`HANDOFF.md` (gitignored) holds only where the current goal stands. Plans, decisions and dead ends go in files, not in the chat.

## Open
- The switch-test cases and replays are diffs from `ambysto/coding-playbook` (archived, private since APS-97); their runner needs its clone at `~/work/ambysto/coding-playbook`, kept read-only on `main` for that alone (owner decision 2026-11-25). Keep that clone, or the kit cannot replay them.
- `intent/` and `docs/` are the history of these files as they were made in `coding-playbook`.
