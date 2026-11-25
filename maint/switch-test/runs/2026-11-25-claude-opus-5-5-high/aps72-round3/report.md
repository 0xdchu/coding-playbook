**PASS**

I found no BLOCKER or MAJOR issue. Main's reading is still 4b83421's reading:
- **`strip_heredocs`:** under `READING` main it adds no `: …` line, so its output is byte-identical to before.
- **`split_substitutions`:** under main it now looks inside `$((` to collect bodies but writes the same text. The backtick end index is unchanged.
- **`pieces`:** the backtick branches run only under `new`.
- **Scanners:** `scan_end` and `scan_end_main` are unchanged.
- **Fast path:** backtick-only text used to be read once under `("new","all")`. Without `$(` or `${` that is the same as main's reading, which now runs first.

The one thing main's reading does differently is that it now also reads substitution bodies, which can only add refusals.

1. **MINOR (realistic)**, `gates/session-gates.py:240`: the substitutions from an unquoted heredoc body are placed on the next line, after anything else on the heredoc's own line. So a `cd` on that line moves them. Case: `cat <<EOF; cd /b` / `$(git checkout -b wip)` / `EOF`. Bash runs the substitution in the starting directory, but the gate checks `/b`. It checks the wrong repo's branch rule and tree, which can be a miss or a false refusal. `docs/internals.md` says these are checked "in the directory where the substitution runs", which is wrong here. This is not a loss against 4b83421, which dropped the body.

2. **MINOR (realistic, rare)**, `gates/session-gates.py:130-150`: `body_substitutions` scans the raw body, and the scanner does not know about heredocs. A heredoc nested inside a substitution in an unquoted heredoc body, whose own body contains a `'` or an unmatched `(`, looks unclosed and ends the list. Case: `cat <<EOF` / `$(cat <<X` / `it's` / `X` / `)` / `$(git checkout -b wip)` / `EOF`. Bash and dash both run the second substitution (I checked: it runs), but the gate allows the command.

3. **MINOR (realistic)**, `docs/internals.md:13`: one sentence is now garbled: "The new readings keep a backtick substitution in one piece; main's reading still splits inside it, redirections and leading shell keywords … are dropped". The backtick clause also repeats what the Limits section already says.

4. **MINOR (hypothetical: a test failure message only)**, `gates/session-gates.py:1274`: the `body_substitutions` failure message prints a different input from the one tested.

What I confirmed independently, not from your summary:
- **Unclosed substitution in a heredoc body:** in bash, the substitutions before it run, nothing after it does, and the command after the heredoc still runs. Dash stops the whole script with a syntax error. Main's reading still checks what comes after, so nothing is lost.
- **`$((cmd); …)` in a heredoc body:** bash treats it as broken arithmetic and runs nothing. Reading it only adds a refusal.

Commands run:
- `--self-test` on the new and old files: both PASS.
- Differential fuzz of `commands()` against 4b83421, 20,000 commands: no new errors, nothing slow. Two commands dropped words that only 4b83421's new-scanner readings produced, at `$((x); y)`.
- Verdict-level fuzz (branches, pushes, write trees) against 4b83421, 30,000 commands: 0 refusals lost, 0 errors.
- About 35 targeted cases: no refusal lost. The new refusals are real shell executions or the documented `${x:-…}` case.
- Mutations (body recursion, heredoc body runs, backtick fast path): all killed (22, 7 and 1 self-test failures).
- Timing with large inputs, under a memory cap: at most 1.2 s, for a 180 KB unquoted PR body. The hook timeout is 30 s.
- `scripts/check.py`: **exit 1**. It fails only in the `progress-diagram.py` self-test, because the installed `ambysto-graph` rejects its old IR format. This change does not touch that file, but check.py is not green on this machine.

Not run:
- `install.py --check`: this is a throwaway clone and `~/.claude` is not its install target.
- zsh checks: zsh is not installed.
- The real-transcript comparison: I don't have the corpus.
