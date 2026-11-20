---
name: sdlc
description: The artifact chain intent, plan, build, verify, ship for any piece of work big enough to need it in a repo. Use when you start a new feature or a large refactor, or say "write the intent", "follow the plan", "/sdlc". Not for a one-line fix, a quick diagnosis, or a one-off ops task.
---

# /sdlc

Each phase ends with an artifact committed to the repo. A later session (or another agent) only needs to read that file, not the chat history.

You are both the one who sets the requirements and the one who builds, so every approval gate comes down to one rule: **you approve the artifact before the next phase runs.**

The chain lives in the repo's `intent/` folder:

```
intent/
  2026-09-01-dark-mode.md        # WHY + WHAT (intent, approved)
  2026-09-01-dark-mode.plan.md   # HOW (plan, complete on its own)
```

Spec first, code after; verify layer by layer instead of reading every line.

---

## Phase 1: Intent (why + what)

When you describe a feature or a problem, the agent asks a few sharp questions (3 to 6) until the scope is clear: technical constraints, the systems affected, what is **not** done. Attach your best guess (the default or recommendation from the codebase) to each question so the owner can confirm in one word. Write each answer into the intent where it applies (an Outcome item, a Coverage bullet, a constraint); a point still unanswered is a marker (below). Then it writes `intent/<yyyy-mm-dd>-<slug>.md`:

```markdown
---
status: draft   # draft → approved → planned → building → verified → shipped (PR #n)
---
# <Title>
## Problem
What hurts now, in your words.
## Outcome
1. What exists when this is done; each numbered item a success criterion (measurable).
## Constraints
Tech, budget, policy (lean, no new dependency, …).
## Coverage
- Who: the people, roles and systems involved.
- Trigger: what starts each use.
- Main path: the steps when all goes well.
- Branches and failures: wrong input, denied or expired, an outside service down, nothing found, a repeat or a race.
- Data and states: what is stored or changes state.
- Limits: size, time, cost, quotas.

Flow: <each `<yyyy-mm-dd>-<slug>.<name>.flow.json` in backticks, or `not needed: <reason>`>
## Out of scope
What this work deliberately does NOT do.
## Open questions
None.
```

**Write WHAT, never HOW.** Function names, file layouts and algorithms belong in the plan. Every line should change a decision or a test; cut the rest.

**Coverage.** Each of the six bullets has text, or `N/A: <reason>`. A bare `N/A`, `TBD` or `?` counts as empty; an open point is a marker (below). Sub-bullets go indented under their bullet.

**Flow.** Draw the work as a flow when it has a branch point (a place where it takes one of several paths with different outcomes: yes or no, success or failure) or three or more parties that act on each other (people, roles, your own systems, outside services). A forgotten path shows up as a validation error: a decision with one exit, a node nothing reaches, a step with no declared link.
- A path through steps and decisions (a user flow) is a `workflow`: draw one when the work branches. Who calls whom, in order (a processing flow), is a `sequence`: draw one when three or more parties act on each other. When both hold, draw both, one file each.
- Name each `<yyyy-mm-dd>-<slug>.<name>.flow.json`, beside the intent, and name every one on the intent's single `Flow:` line.
- Draw from the intent alone, with the flow tool your global instructions name, or the `graph` skill: no `sources`, no `--repo-root`, and in a `sequence` people and outside services as `external` participants. Render each one with only `-o <…>.flow.html` (no theme or other option) beside it, with the same tool `clarify` will use, and commit both.
- Say, when handing it over, that the flow was not checked against code.
- Otherwise write `Flow: not needed: <reason>`.

Mark every open point where it stands in the text as `[NEEDS CLARIFICATION: <question>]`, and list it under `## Open questions`. That section begins with `None` when nothing is open. Run

```
python3 <coding-playbook>/scripts/sdlc-check.py clarify intent/<yyyy-mm-dd>-<slug>.md
```

(`scripts/sdlc-check.py` in the coding-playbook repo) before the intent goes to `approved`, and again before the plan is written. It fails while any marker remains, `## Open questions` does not begin with `None`, a Coverage bullet is missing or empty, the `Flow:` line is missing or wrong, or a flow fails validation or its `.flow.html` is not a fresh render. With no flow tool installed it says the flows were not checked; say so too.

**Fresh reader.** Before you ask the owner to approve, run one fresh agent, with none of this chat, on the model your builder agent uses, read-only. Give it this prompt, with the paths filled in:

```text
You are a fresh reader of a spec. Read ONLY these files and nothing else (no other file, no search, no web):
- <intent path>
- <each flow .json path>

Imagine you must plan, build and test this work from these files alone. Return three numbered lists, at most 300 words in all:
A. Guesses: each point you would have to guess to build or test it (quote the line, say what is unclear, give the two readings).
B. Cuts: each line that changes no decision and no test, so it could be removed.
C. HOW: each implementation detail that belongs in a plan rather than in this intent.
Write "none" for an empty list. Do not invent problems to fill a list; do not suggest new scope.
```

Each item ends as a question to the owner, a clearer line, or a cut (HOW moves to the plan). Run `clarify` again, and once more the reader after a large change. Record the lists and what became of each item in the intent's PR body; an intent always goes up as its own PR.

You edit it → `status: approved`, commit. **Do not write the plan before the intent is approved.**

For a new product: the intent must state how it earns money (who pays, and for what).

---

## Phase 2: Plan (how)

Feed only the intent file into plan mode. For large or architectural work, split the product review from the technical review before settling. Ask: "what could break?" Output `intent/<yyyy-mm-dd>-<slug>.plan.md`, the intent's own name with `.plan` before `.md` (converge finds the intent by that name):

- **Files**: every file that will be touched, in the order of work.
- **Risks**: what could break, and the check that would catch it.
- **Tasks**: one entry per builder dispatch, or per step the main session does itself.
- **Proof**: the commands or evidence that show it is done (test, build, screenshot, curl). "Done" is defined here, before any code is typed. An item names the intent's Outcome items it proves, as `(O1, O3)` on its line, and an item that proves none on its own (a whole-suite run) names none; every Outcome item is named at least once.
- **Result**: an empty heading for now, filled in Phase 4.

The plan starts with its own status line, `status: draft # draft → planned → building → verified`.

`## Tasks` has one `###` heading per task, then bullets:

```markdown
## Tasks

### T1 (builder, parallel) <title>
- allow: `src/feature/**` `tests/feature/**`
- forbid: `src/core/**`
- check: `make test`
- check: `make lint`

### T2 (main) <title>
- allow: `src/core/auth.py`
- check: `make test`
```

- Heading: `### T<n> (builder|main[, parallel]) <title>`. `builder` is dispatched to a builder; `main` is done by the main session. `parallel` means it may run beside another task, so it gets its own worktree.
- `- allow:` and `- forbid:` are globs in backticks, relative to the repo. `- check:` is one command in backticks per bullet, at least one per task.
- `- not needed: <reason>` marks a task dropped during the build.
- The plan, its intent and the intent's `*.flow.json` and `*.flow.html` need no `allow`: converge counts them as part of the plan.

A builder task is dispatched with `dispatch.py new <repo> <branch> --task <plan> <id>` (or `dispatch.py contract <tree> --task <plan> <id>`), so the contract comes from the accepted plan and not from flags typed by hand.

`## Proof` is a numbered list. `## Result` has one numbered item per Proof item, each beginning with `PASS`, `FAIL` or `not run: <reason>`, then the numbers (counts, commit, output):

```markdown
## Proof

1. `make test` passes. (O1, O2)
2. `curl localhost:8080/health` returns 200. (O3)

## Result

1. PASS, 42 tests, 0 failed.
2. not run: the server needs credentials.
```

You accept the plan → `status: planned`, commit. The plan is the handoff contract: the implementing agent reads only the plan, not the chat.

---

## Phase 3: Build

The repo's normal rules apply (one logical unit at a time; a worktree if tasks run in parallel). In addition:

- If the work departs from the plan → **update plan.md in the same commit**. The diff must match the plan.
- When coding starts → `status: building`.

---

## Phase 4: Verify

Run exactly the **Proof** items in the plan, and fill `## Result`: one numbered item per Proof item, beginning `PASS`, `FAIL` or `not run: <reason>`. Then run

```
python3 <coding-playbook>/scripts/sdlc-check.py converge intent/<yyyy-mm-dd>-<slug>.plan.md
```

It lists each gap between the plan and the branch's diff: a changed path no task allows, a task never touched (and not marked `not needed`), a Proof item with no Result, plus `floor:` notes for any added linter/type suppression, skipped or deleted test, or net removed assertion. When the intent has `## Coverage`, it also fails when an Outcome item is named by no Proof item, or a Proof item names an Outcome item that does not exist. In a repo with a map (`docs/map/`, the system-map skill), when the branch changes anything besides the plan and its intent, it also runs `sdlc-check.py map` and each item is a `map:` gap: update the map on the same branch, so the task that changes code also allows `docs/map/**`. It fails while any gap remains. A plan without `## Tasks`, or an intent without `## Coverage`, is reported and passes, so older plans stay valid.

The author does **not** approve their own work: it passes an independent review (`code-reviewer` or another review agent) with the intent and the plan as the contract. Give the reviewer converge's output together with the diff. Proof green → `status: verified`.

A mistake that happens a second time in any repo → write it down at once in that repo's `CLAUDE.md` or `lessons.md`.

---

## Phase 5: Ship

Merge following the repo's flow (feature branch → PR → main; or uat → main if the repo is set up that way). After the merge: `status: shipped (PR #n)` in the intent. The chain is closed, and git history is the audit trail.

---

## Phase 6: Maintain (the loop)

Health checks, cron jobs and alert emails can flag issues by themselves. Convention: an issue that is worth doing and bigger than a one-line fix starts with a new intent file in the repo that owns it. A small, bounded fix → a PR straight away, skipping the chain.

---

## One-prompt run (the chain without the owner between steps)

When the owner gives a goal and asks for it to be carried to done, the chain runs as one run:
- Write the intent and the plan as above, with `## Tasks` and `## Proof`. Run `clarify`; gather every point only
  the owner can settle into one question, asked once at the start. The prompt then counts as the approval of that
  intent and plan (record it in the status lines).
- Start the run on the plan with the loop tool the global instructions name. From then on, each time the session
  would stop, a Stop hook runs `converge` and hands back what is left (a task untouched, a proof item without a
  result, a FAIL result, a `check:` command that fails when the hook runs it) as the next work. Do the next item; do
  not stop to report progress.
- A review verdict comes from the reviewer agent. Its prompt for the run's own plan has, anywhere, a line of its own
  that reads `loop task: T<n>`, or for two tasks `loop tasks: T1, T2`. A hook records what the reviewer returned for
  each task named, and the tool's `pass` is refused without that task's reviewer PASS on record. A review of other
  work gets no such line: its verdict counts for nothing and neither holds nor passes the run. A FAIL of two tasks is
  one FAIL for each: record it with the tool's `fail` once per task. Record every reviewer FAIL with the tool's `fail`. The second FAIL of one task, or the third
  round of failing checks, ends the run: stop and report with the numbered issues. A question only the owner can
  answer ends it too (the tool's `ask`). Name the ticket in the plan (`Plane <KEY-N>`): a run that closes needing the
  owner comments there.
- Fill `## Result` as proof runs: PASS with numbers, FAIL, or `not run: <reason>`. When `converge` finds nothing
  left and the checks pass, the run closes as done; end with the usual summary.

## Evals: regression for the process

An `evals/` folder per repo: one file per case, with a **Task** (a real prompt) and an **Expect** (a result that can be checked). Every production incident and every "the agent got it wrong" adds a permanent case.

Run the evals **before merging** a change to `CLAUDE.md`, a skill or a hook. If the config lowers the pass rate, do not merge. Five cases are better than none.

---

## Conventions used for real

- **Rate the difficulty before handing out work.** Rate four things: ambiguity, decisions that depend on each other, how easy it is to check, and the cost if it is wrong, judged by what undoing it takes (a revert fixes it: low; a revert leaves work or decisions to redo: high; nothing undoes it, such as user data lost or migrated, auth or another security boundary weakened, money moved, something published or sent: HARD outright), never by how sure the model is. None high is **EASY**: give it to an agent to do, no review. One high is **MEDIUM**: an agent builds, then another agent reviews. Two or more high is **HARD**: the main session does it itself. Each repo's `CLAUDE.md` gives its own examples for the three levels.
- **One ticket, one branch; one phase, one PR.** The intent is one PR; wait for approval before writing the plan. No push straight to `main`; merge as the global instructions say (on its own once Verify and review passed; ask first when the merge publishes or deploys).
- **A ticket lives in two places** (the tracker and a GitHub issue), each linking to the other. The issue title carries the ticket code, for example `[AGD-2]`. When a ticket moves to another project, close the old one and leave a comment pointing to the new place.
- **The ticket follows the chain, at the moment each step happens.** No ticket yet when the intent PR opens: create it (Todo; the command prints its code) and link the PR. The GitHub issue, once it exists: link it on the ticket. `building` (the first dispatch): In Progress. Each PR opened (intent, plan, build): link it on the ticket. `shipped`: Done, with a comment naming the PR; the PR body says `Closes #<issue>` so the GitHub issue closes with it. Work dropped: Cancelled (or the project's state for it), with a comment saying why. Blocked on the owner: a comment saying what waits, no state change. Only the main session moves tickets.
- **The progress diagram follows the chain.** When a task's files change, a proof gets a result or the status line moves, redraw the plan's progress diagram (tasks started or not, proof items PASS, FAIL, not run) with the tool the global instructions name, and give the owner its path. It is drawn into the git folder and never committed. No such tool installed: skip this step and say so once.
- **One product, one repo.** A shared library is depended on by semver tag, never by branch.
- **A product that comes out of a teardown:** the intent points to `docs/spec/SPEC.md` as the WHAT, and does not rewrite the spec. When behaviour is missing from the spec, ask whoever owns the spec; do not decide alone.
- **Before pushing, check the GitHub account** with `gh api user --jq .login`. Do not change the active account; use `GH_TOKEN=$(gh auth token -u <account>)`.
- **Proof must be evidence that was run** (a command, a test count, a screenshot), not a claim. The reviewer judges the proof against the intent and the plan.

---

## When NOT to use

A one-line fix, a diagnosis, a one-off ops task: the chain is overhead. When in doubt: if it deserves a feature branch, it deserves an intent file.
