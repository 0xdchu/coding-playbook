**PASS** — no BLOCKER or MAJOR; five MINORs, three of them realistic.

Main's reading is 4b83421's reading. Under `READING main`, `strip_heredocs`, `pieces`, `split_substitutions()[0]` and `commands_read` (body reading off) were identical on 250k fuzzed inputs. Old `commands()` was a subset of new on 400k, with no new exceptions. The unclosed-substitution rule matches bash 5.3 (earlier ones run, later ones don't, the command after the heredoc runs) and dash (syntax error, nothing runs).

1. **MINOR, hypothetical** — `gates/session-gates.py:565-575`, `:675-677`. Main's reading appends a `$((cmd); …)` body and also reads on inside it, so nested ones are re-read exponentially. `git push origin HEAD:main; echo ` + 22 nested `$((a …); x)` (253 chars): 4b83421 denies in 0.0 s, d8aa744 exceeds the 30 s hook timeout, so the push goes through. 20 levels takes 15.5 s. No real command nests this 22 deep. The "linear `$((` scans" claim does not hold for this close.

2. **MINOR, realistic** — `:569`, `:146`. A `$((` that ends in `))` is taken as arithmetic, but bash runs `$((a) || (b))` as a substitution (checked: the subshell ran). `echo $((git push origin HEAD:main) || (true))` and `x=$((git checkout -b wip) && (echo ok))` are allowed. Not a regression, but it is a gap in requirement 1 and is not in the documented limits.

3. **MINOR, realistic** — `:174-187`, `:262`. A heredoc inside a double-quoted backtick substitution is never stripped, because only `$(` un-quotes there. Its body lines are now read as commands. `git commit -m "`cat <<'EOF'⏎Subject⏎⏎git checkout -b wip is refused now⏎EOF⏎`"` is denied; 4b83421 allows it, and so does the `$(` form.

4. **MINOR, realistic (rare)** — `:216`, `:591`.
   - `cat <<EOF''` is taken as an unquoted delimiter, so `$(git checkout -b wip)` in its body is denied; bash and dash do not expand it.
   - `\"` inside double-quoted backticks is not unescaped: `"`git push origin \"main\"`"` reads the ref as `"main"` and misses it, and `"`echo \"x; git checkout -b wip\"`"` is refused.

5. **MINOR, realistic** — `docs/internals.md:65` has a run-on left by the edit ("…still splits inside it, redirections and leading shell keywords… are dropped"). The module docstring (`:26-32`) does not say that substitution bodies are checked.

Scope is the gate and its doc section only. No suppressions; no threshold changed (`MAX_NEST` and `ARITH_SCANS` are new and documented).

**Run**
- `session-gates.py --self-test`: PASS.
- `scripts/check.py`: **exit 1** here. The only failure is the `scripts/progress-diagram.py` self-test, a file the diff does not touch (the installed `ambysto-graph` rejects the old flow IR). Your "`check.py` PASS" is not reproduced on this machine.
- `install.py --check`: exit 1; the installed copy differs from this older clone, which is unrelated to the diff.
- Mutations: 10/10 killed by the self-test (body recursion, both backtick guards, heredoc guard, fast path, unclosed break, `$((` under main, quoted delimiter, cwd, re-strip).
- Timing: 29 KB of 8-deep nesting 0.33 s, 160 KB flat 0.45 s; only item 1 blows up.
- Hook entry point (`pre-tool`) on the cases above, old against new.

**Not run**
- no_push with a local `main` branch: needs a scratch repo, which my hooks forbid; I used `HEAD:main` in the clone instead.
- zsh: not installed.
- The 14,591-transcript comparison: no corpus here.
- The agent and skill Verify lines: not applicable.
