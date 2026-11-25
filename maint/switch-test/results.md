# Switch test results

Matches are the main session's proposal until the owner confirms them; "owner" columns stay empty until then.
`Kn` is issue n of the case's `known.md`; `Rn` is issue n of the run's `report.md`. A partial match (the run found
part of the known issue, or the same defect through a different example) counts as caught and is marked (p).

## Baseline, 2026-11-07 (reviews at effort `high`)

Conditions: headless runs in fresh clones; no `bd` binary on the machine (the original aps34 review had one, which
K1 and K3 there needed to confirm); Windows tests not runnable for asp18 (all runs say "not run"). Settings changed
during the first two runs (the owner ran `/model` and `/effort`, the main session wrote the owner log); no run touched
`~/.claude` itself. Two Opus runs were first marked VOID for reading their own large tool output from their own
session folder; the void check was fixed and both rechecked clean (`run.json` `void_note`).

### Summary

| model | known caught | MAJOR-or-worse caught | new issues to judge | cost | minutes |
|---|---|---|---|---|---|
| `claude-opus-5-5` | 14/19 | 4/6 | 9 | $2.66 | 6.4 |
| `claude-fable-5-1` | 13/19 | 5/6 | 7 | $8.48 | 16.7 |

### aps32-guard (known: K1 MAJOR, K2-K7 MINOR)

| known | Opus 5.5 | Fable 5.1 |
|---|---|---|
| K1 MAJOR joined short flags (`sed -Ei`, `bash -lc`, `gh api -XPOST`) | R2 (+R1 `bash -lc`) | R2 (+R4 `bash -lc`, `-XPOST`) |
| K2 glued operators `\|\|(` | missed | missed |
| K3 `<<WORD` without terminator drops later lines | missed | missed |
| K4 `checkout -b --`, wrappers with option values, `git.exe` | R1 (p, wrappers only) | R4 (p, wrappers only) |
| K5 uncaught exceptions fail open; missing python3 | R3 (MAJOR) | R3 (MAJOR) |
| K6 false positives on reads | R6 | R5 |
| K7 docs drift (hooks path, README, Co-Authored-By line) | R9 (p, Co-Authored-By only) | missed |
| **caught** | **5/7**, MAJOR 1/1 | **4/7**, MAJOR 1/1 |
| new, to judge | R1 `then`/`do` keywords (MAJOR; the later fresh hard review found the same and it was fixed), R4 PowerShell coverage (MAJOR), R5 `find -delete` and first-argument-only checks, R7 check.py matcher position, R8 `git stash` | R1 `then`/`do` keywords (MAJOR, same as Opus R1), R6 agent bodies do not mention the hook |
| cost, minutes | $0.52, 1.9 | $2.05, 5.9 |

### aps34-boundary (known: K1-K3 MAJOR, K4-K7 MINOR, K8 NIT)

| known | Opus 5.5 | Fable 5.1 |
|---|---|---|
| K1 MAJOR `rest[:-1]` drops `--status=closed` | missed | R2 |
| K2 MAJOR `git push origin HEAD` on main | R1 | R1 |
| K3 MAJOR `bd show` failure not checked | missed | missed |
| K4 protected paths through `rm`/`mv`/`git rm` | R4 | R10 (as NIT) |
| K5 publishing/tag/secret gaps (tag by name, `gh api` refs, graphql, `.env`) | R2 (MAJOR), R5, R6 | R3 (MAJOR), R4, R6, R9 |
| K6 bd fields beyond status/evidence/cost/claim | R7 | missed |
| K7 `cd` in a subshell leaks | missed | missed |
| K8 NIT false blocks, DO_NOT_TRACK regex | R7, R8 (p) | R6 (p, `.pem`) |
| **caught** | **5/8**, MAJOR 1/3 | **5/8**, MAJOR 2/3 |
| new, to judge | R3 close without an id (MAJOR, unconfirmed), R5 Read tool on keys and signing, R6 twine/docker, R9 symlinked `~/.claude` | R5 signing flags, R7 `LICENCE` spelling and CLAUDE.md unprotected, R8 `bd -C` unverified, `--remove-label` |
| cost, minutes | $1.28, 3.3 | $3.42, 7.2 |

### asp18-overview (known: K1-K2 MAJOR, K3-K4 MINOR)

| known | Opus 5.5 | Fable 5.1 |
|---|---|---|
| K1 MAJOR Scan again does nothing with C: unticked | R1 | R1 |
| K2 MAJOR no test for that path | R3 (as MINOR) | R5 (as MINOR) |
| K3 spec line contradicts the departure; note inserted mid-note | R2 | R2 (p, as MAJOR, contradiction only) |
| K4 test gaps (focus ring, WrapPanels, Enter, busy rules) | R3 | R5 |
| **caught** | **4/4**, MAJOR 2/2 (K2 at lower severity) | **4/4**, MAJOR 2/2 (K2 at lower severity) |
| new, to judge | none | R3 `CenterLines` centring not in the contract, R4 CheckBox style alignment |
| cost, minutes | $0.86, 1.3 | $3.02, 3.7 |

### Owner verdicts

| run | matches confirmed | new real | false alarm | date |
|---|---|---|---|---|
| Opus 5.5 | all, as proposed above | not judged yet | not judged yet | 2026-11-07 |
| Fable 5.1 | all, as proposed above | not judged yet | not judged yet | 2026-11-07 |

The owner confirmed the matches ("Verified", 2026-11-07). The new issues are not yet sorted into real and false
alarm; the known-issue counts, which decide (a), do not depend on them.

## Replay baseline (question b), 2026-11-07

`replay --model claude-opus-5-5 --effort high` (the main session's effort, set by the owner that day), then the fixed
reviewer `claude-fable-5-1` at `high` on the replay's commit. One round, no fixes. Before committing, the replay ran
the HARD loop itself: two `hard-reviewer` rounds (Fable 5.1 subagent) and fixes. Its commit is that loop's output, and
the review prompt is the kit's own, so the original column below is context, not a like-for-like baseline; a
candidate's replay is compared with the Opus 5.5 column.

| | original author (1f8064f, 2026-10-23) | Opus 5.5 replay (afb1879) |
|---|---|---|
| reviewer's verdict | FAIL: 2 MAJOR, 5 MINOR (`known.md`) | FAIL: 1 MAJOR, 5 MINOR |
| MAJOR | K1 token paths not denied; K2 false positives in every session | R1 tracing the `gh` wrapper (`bash -x`) prints the token (new) |
| known issues repeated | | K1 (p): a gh alias still prints the token (R1's second example, `gh alias set e '!env' && gh e`; K1's third bullet); K2 (p): a commit message or grep naming `gh auth token`/`oauth_token` is still denied (R4, as MINOR); none of K3-K7. K1 (p) added 2026-11-08 from round-2 review; confirmed by the owner ("Verified", 2026-11-08) |
| size | 4 files, +160/-3 | 6 files, +446/-16 |
| cost, minutes | | author $8.55, 25.2; review $5.49, 14.1 |

The first review of the replay was void: it read the guard installed on this machine (the later, fixed version) to
compare (`runs/…/aps37-token-guard-review-void1`, $8.42). The review task now says not to, and the void check counts
reads of a case's answer keys (the live source repo, `void_extra` in `case.json`). The replay author itself listed
`~/.claude/hooks/` but never read the installed guard; the owner-token guard was live during the replay, so a blocked
command showed it the installed deny message (the same for every candidate, and needed for the owner's safety). Its
Glob of `~/.claude/hooks` returned names only; its grep of the `ambysto-memory` index found no APS-37 lesson (none
exists there today).

## Release-day dry run, 2026-11-07 (`claude-opus-5-5` standing in)

- Step 1: not needed for a pinned model (`check.py` allows the agents' pins).
- Step 2: `probe --model claude-opus-5-5`: agent-guard's message in the tool result, the checkout blocked.
- Steps 3-4: the baseline runs above are these commands with the stand-in.
- Step 5: matches proposed and confirmed by the owner, for the reviews ("Verified", 2026-11-07) and the replay row
  ("Verified. Confirmed", 2026-11-08).
- Steps 6-8: not run (no candidate yet).

## Label trial, 2026-11-25 (APS-101, CPB-2)

The new reviewer rules of ambysto/coding-playbook PR #95 (b7b3586) and PR #96 (96bde38), in this repo since #24 and #25: every MINOR labelled `realistic` or `hypothetical`,
a `hypothetical` one names one of three grounds (the shell rejects the whole command, a size no real use reaches with
the size given, the intent's out-of-scope list); check 1 flags copied logic, check 6 flags tests on internals.
`review --effort high` on the four cases, with `claude-opus-5-5` (like for like with the baseline above) and
`claude-fable-5-2` (the current hard-reviewer, no old-rule baseline). The runner appended `rules/agents/reviewer.md` of
the APS-101 branch (PR #96's body; here it is the body of `main` before CPB-2). Probes: both models, agent-guard blocked the checkout.

Conditions: as the baseline, plus `SESSION_GATES_MEMORY=/nonexistent` (README, Running). No run was void and no run
changed `~/.claude` or a source repo (`watch_changed` empty). Between 09:13 and 09:15 (+07) another session briefly
installed a reviewer without PR #96's line; these runs did not read the installed copy. The 2026-11-07 aps34 review had
a real `bd`; neither this run nor the baseline had one.
One report is redacted for this public repo: Fable 5.2's aps34 R10 named a token file's path on this machine.

`aps72-round3` is new. Its original reviewer was `claude-fable-5-2` (the stream says so; the ticket said Fable 5.1),
and its transcript is under `~/.claude/projects/-home-<user>-work-0xdonniechu/`, not the coding-playbook folder.

### Summary

| model | known caught, old 3 cases | MAJOR-or-worse caught, old 3 | aps72 known | MINORs labelled | `hypothetical` | grounds valid and true | guard gap on real input labelled `hypothetical` | check 1 / check 6 findings | cost | minutes |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline Opus 5.5 (old rules) | 14/19 | 4/6 | | | | | | | $2.66 | 6.4 |
| `claude-opus-5-5` | 14/19 | 5/6 (2 at MINOR) | 1/3 (p) | 19/20 | 3 (16%) | 0/3 | **1** (aps32 R8) | 0 / 0 | $4.56 | 12.0 |
| `claude-fable-5-2` | 17/19 | 5/6 (1 folded into another MAJOR) | 0/3 | 20/20 | 2 (10%), plus one sub-item | 1/3 | 0 | 0 / 2 (both real) | $14.05 | 28.1 |

Same three cases as the baseline: Opus 5.5 $2.87, 6.9 minutes (baseline $2.66, 6.4); Fable 5.2 $10.26, 16.7 minutes
(Fable 5.1 baseline $8.48, 16.7). The cost and minutes columns above include `aps72-round3`.

(a) No MAJOR the Opus baseline caught is lost: aps32 K1, aps34 K2, asp18 K1 and K2 are caught by both models. Opus now
reports aps32 K1 (joined short flags) as `MINOR (realistic)`, where its baseline said MAJOR; a realistic MINOR is still
fixed before a merge. Opus lost aps34 K4 (the baseline's R4) and found aps34 K1 (the baseline missed it).

### aps32-guard (known: K1 MAJOR, K2-K7 MINOR)

| known | Opus 5.5 | Fable 5.2 |
|---|---|---|
| K1 MAJOR joined short flags | R2 (as MINOR realistic) | R4 (MAJOR), R6 |
| K2 glued operators `\|\|(` | missed | R1 (p, `);` and `)&&`, as MAJOR) |
| K3 `<<WORD` without terminator | missed | R5 |
| K4 `checkout -b --`, wrappers with values, `git.exe` | R2, R6 (p, wrappers and `git.exe`) | R6 |
| K5 uncaught exceptions fail open; missing python3 | R4, R5 | R8, R9 |
| K6 false positives on reads | R3 | R7 |
| K7 docs drift | R9 (p, hooks folder) | R11, R12 (p) |
| **caught** | **5/7**, MAJOR 1/1 (at MINOR) | **7/7**, MAJOR 1/1 |
| new, to judge | R1 `then`/`do` keywords (MAJOR, as baseline), R7 review writes missed, R8 first-argument-only checks | R2 keywords (MAJOR), R3 backslash continuations (MAJOR), R10 self-test bypasses `main()`, R11 missing Co-Authored-By (looks like a false alarm: the owner decision of 2026-10-20 drops it; K7) |
| MINORs: labelled / `hypothetical` | 8/8, 2 (R5, R8) | 8/8, 1 (R9) |
| cost, minutes | $1.00, 2.8 | $3.06, 6.3 |

### aps34-boundary (known: K1-K3 MAJOR, K4-K7 MINOR, K8 NIT)

| known | Opus 5.5 | Fable 5.2 |
|---|---|---|
| K1 MAJOR `rest[:-1]` drops `--status=closed` | R3 (MAJOR) | R1 |
| K2 MAJOR `git push origin HEAD` on main | R1 | R2 |
| K3 MAJOR `bd show` failure not checked | missed | missed |
| K4 protected paths through `rm`/`mv`/`git rm` | missed | R8 |
| K5 publishing/tag/secret gaps | R2 (MAJOR), R8, R10 | R3 (MAJOR), R7 |
| K6 bd fields beyond status/evidence/cost/claim | R4 (MAJOR) | R4 (MAJOR) |
| K7 `cd` in a subshell leaks | missed | missed |
| K8 NIT false blocks, DO_NOT_TRACK regex, case variants | R6, R7, R9 | R5, R6, R8 |
| **caught** | **5/8**, MAJOR 2/3 | **6/8**, MAJOR 2/3 |
| new, to judge | R5 close without an id, R11 NIT malformed `boundary.json` message | R1 (part) close without an id, R3 Read/Grep tool on secrets (MAJOR), R4 `duplicates --auto-merge`, `-h`, R9 tests bypass `main()` (two surviving mutants), R10 NIT |
| MINORs: labelled / `hypothetical` | 5/6 (R10 has no label), 0 | 5/5, 0 (one sub-item of R8 marked hypothetical) |
| cost, minutes | $1.04, 2.9 | $4.38, 7.5 |

### asp18-overview (known: K1-K2 MAJOR, K3-K4 MINOR)

| known | Opus 5.5 | Fable 5.2 |
|---|---|---|
| K1 MAJOR Scan again does nothing with C: unticked | R1 | R1 |
| K2 MAJOR no test for that path | R3 (as MINOR) | R1 (p, "no test clicks it", inside the MAJOR) |
| K3 spec contradicts the departure; note inserted mid-note | R2 | R2 (p, contradiction only) |
| K4 test gaps | R3 | R3 |
| **caught** | **4/4**, MAJOR 2/2 (K2 at MINOR) | **4/4**, MAJOR 2/2 |
| new, to judge | none | R3 (part) the busy-rule test passes vacuously |
| MINORs: labelled / `hypothetical` | 2/2, 0 | 2/2, 0 |
| cost, minutes | $0.83, 1.2 | $2.83, 2.9 |

### aps72-round3 (known: K1-K3 MINOR; the original PASSed)

| known | Opus 5.5 | Fable 5.2 |
|---|---|---|
| K1 the unclosed rule trusts the scanner | R2 (p, a nested heredoc with `'` looks unclosed; `realistic`) | missed |
| K2 the `ARITH_SCANS` cap leaves a gap | missed | missed (R1 is a different `$((` defect) |
| K3 surviving `MAX_NEST` mutant | missed | missed |
| **caught** | **1/3**, labelled `hypothetical`: 0 | **0/3** |
| verdict | PASS, 4 MINOR | PASS, 5 MINOR |
| new, to judge | R1 a `cd` on the heredoc's line moves the body's substitutions, R3 garbled `internals.md` sentence, R4 test message | R1 exponential re-reading of nested `$((cmd); …)` (hypothetical, checked below), R2 `$((a) \|\| (b))` runs as a substitution, R3 heredoc in double-quoted backticks, R4 `<<EOF''` and `\"` in backticks, R5 run-on sentence (same as Opus R3) |
| MINORs: labelled / `hypothetical` | 4/4, 1 (R4) | 5/5, 1 (R1) |
| cost, minutes | $1.70, 5.1 | $3.79, 11.4 |

(d) None of the three known MINORs comes out `hypothetical`: Opus caught K1 and labelled it realistic, Fable caught
none. Under the new rules all three are realistic anyway (K1: dash runs the push; K2: sixteen `$((1))` is a real
size; K3: a test gap), so round 4 would still have run.

### Each `hypothetical` MINOR, checked by hand (c)

| run | issue | ground given | one of the three? | true? | guard gap on real input? |
|---|---|---|---|---|---|
| Opus aps32 | R5 odd hook input (`[]`, a list `command`) exits 1, fails open | "Claude Code always sends an object with a string `command`" | no | yes: the inputs are not commands | no |
| Opus aps32 | R8 only the first argument is read: `git branch -a -D main`, `git tag -l -d v1` | "no real mistake puts a read flag before a delete" | no | no | **yes**. Its two examples are harmless: the guard at ea89167 exits 0 on both, but git refuses them (`cannot use -a with -d`; `-d` and `-l` cannot be used together; checked in a scratch repo). The defect it names is real: `git branch -r -d origin/x` also gets exit 0 in build and review mode, and git deletes the remote-tracking branch (checked). With the action replaced by `touch "$M"`, bash and dash both run it. **Trial FAIL**, found through the reviewer's issue, not its examples. |
| Opus aps72 | R4 a test failure message prints the wrong input | "a test failure message only" | no | no input is involved; the label does not fit (a NIT) | no |
| Fable aps32 | R9 odd hook input fails open (`[]`, `null`, a NUL in a redirect target, deep `eval`) | "Claude Code always sends an object with a string command" | no (deep `eval` would be a size, not given) | for the shapes, yes; nested `eval` with `shlex` quoting doubles in length per level and stayed blocked as far as the probe ran | not shown |
| Fable aps34 | R8, sub-item: no protected-path defaults outside a repo | "runs work in repos" | no | yes for outside a repo; the same line's untracked `boundary.json` missing in a worktree is a real gap and is not covered by the label | no |
| Fable aps72 | R1 22 nested `$((a …); x)` after a push, 253 characters: the hook times out at 30 s and the push runs | a size no real use reaches: 22 levels | yes (size given) | yes: timed at d8aa744, 0.3 s at 14 levels, 3 s at 18, 7.7 s at 20, about ×2.5 per two levels; 4b83421 takes 0.0 s. With `touch "$M"` for the push, bash runs it and dash rejects the line | gap at a nesting no real command has; valid, but borderline: the same exponential path is the only fail-open in the change |

Valid and true grounds: Opus 0 of 3, Fable 1 of 3 (counting the sub-item). Four of the six name a ground outside the
three ("Claude Code always sends…", "no real mistake…", "a test message only", "runs work in repos").

### Check 1 and check 6 (e)

- Check 1 (logic copied where existing code would do): no finding in either model. Fable aps32 notes the installer
  change reuses `install_file` (a pass, not a finding).
- Check 6 (tests on internals): Opus none. Fable two, both real: aps32 R10, the self-test calls `check()` only, never
  `main()` (the fail-open of K5 sits in `main()`); aps34 R9, the self-test calls `boundary_edit` and the mode checks
  directly (checked at 852a39a: no test goes through `main()`), and it names two surviving mutants of the routing in
  `main()`.

### Tightened grounds, 2026-11-25 (CPB-2)

The owner accepted the wording proposed from this trial: a `hypothetical` MINOR states exactly one of the three
grounds in a fixed form (`hypothetical: the shell rejects it`, `hypothetical: size <the size>`,
`hypothetical: out of scope (<item>)`), and no other reason counts. As the Verify for an agent change,
`review --model claude-opus-5-5 --effort high --run 2026-11-25-claude-opus-5-5-high-grounds` ran with that body on the
two cases where the trial found bad labels, and `--model claude-fable-5-2` (the hard-reviewer, same body) on aps32. No run was void. `watch_changed` names the owner time log
(both aps32 runs, written by this session) and `~/.claude/CLAUDE.md` (aps72, written by another session's install at 10:44; the
run's stream never names it).

| case | known caught | MINORs labelled | `hypothetical` | form and ground | guard gap on real input labelled `hypothetical` | cost, minutes |
|---|---|---|---|---|---|---|
| aps32-guard | 5/7: K1 R2 (as MINOR), K2 R1 (p, `true&&(git push)`), K4 R2, R5, K5 R3, K6 R6 | 6/6 | 0 | | 0: the first-argument gap (the trial's R8) and the odd hook input (K5) are now `realistic` (R5, R3) | $0.93, 2.5 |
| aps32-guard, `claude-fable-5-2` (`--run 2026-11-25-claude-fable-5-2-high-grounds`) | 7/7: K1 R2 (MAJOR), R3; K2 R1 (MAJOR); K3 R2 (MAJOR); K4 R3; K5 R6; K6 R7; K7 R9 (p) | 7/7 | 0 | | 0: the odd hook input (K5), labelled `hypothetical` in the trial with "Claude Code always sends…", is now `realistic` (R6) | $3.00, 6.1 |
| aps72-round3 | 1/3: K2 R4 (`realistic`, "the docs already name this limit") | 4/4 | 1 (R2) | fixed form, `size 200+ distinct directories in one substitution`; true for a hand-typed command, borderline for a generated list | not shown: R2 drops the record of a tree under review past `MAX_DIRS`, a gate's bookkeeping, not an allowed action | $2.17, 7.0 |

Three runs are a small sample; they show the form is followed and the trial's FAIL case is now labelled `realistic`.

### Owner verdicts

| run | matches confirmed | new real | false alarm | date |
|---|---|---|---|---|
| Opus 5.5 | | | | |
| Fable 5.2 | | | | |
