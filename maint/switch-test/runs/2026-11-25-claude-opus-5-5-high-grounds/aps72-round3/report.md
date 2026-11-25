**PASS**

I found no BLOCKER or MAJOR. Main's top-level reading is the same as 4b83421's, and no git command that 4b83421 found is lost. The four MINORs below are all gaps or wording, not lost refusals, except issue 2, which only applies past the 200-directory recording cap.

1. **MINOR realistic**, `gates/session-gates.py:137`: `body_substitutions` steps over `\` plus the next character. A heredoc body line ending in `$\` followed by a line `(git push origin main)` is joined by both bash and dash into `$(git push …)`, and the push runs. The gate finds nothing (checked with a stub `git`). The same happens in double quotes, `echo "$\<newline>(git push origin main)"`, because `pieces` turns `\<newline>` into a space; 4b83421 had that gap too.

2. **MINOR hypothetical: size 200+ distinct directories in one substitution**, `gates/session-gates.py:677`: the commands inside a substitution are now listed before the outer command, and main's reading does this too. In `touched()`, a subagent's `git -C /r status $(ls <200+ directories>)` fills `MAX_DIRS` with the inner directories first, so `/r` is no longer recorded. 4b83421 recorded it, because `-C /r` came before the inner words. The comment at :125 ("never drops one of them") no longer holds. Listing the inner commands after the outer one would restore the old order.

3. **MINOR realistic**, `docs/internals.md:63`: replacing "Commands inside a substitution are not checked" left a broken sentence: "…main's reading still splits inside a backtick substitution… The new readings keep a backtick substitution in one piece; main's reading still splits inside it, redirections and leading shell keywords … are dropped". The backtick point is stated twice, and the clause about redirections and keywords is now attached to the wrong sentence.

4. **MINOR realistic (the docs already name this limit)**, `gates/session-gates.py:127`: after 16 `$((` in one command or heredoc body, a `$((git push origin main); true)` passes. Bash runs it (dash does not). The cost of fixing it is the trade-off already chosen, so this only needs listing as a known gap.

**What checks out:**
- **Main's reading:** `strip_heredocs`, `pieces` and `split_substitutions` give 4b83421's text under `READING` main; the only addition is the commands inside substitutions.
- **Backticks:** the `commands()` fast path change keeps main's split inside backticks.
- **Your heredoc rule:** confirmed. With `$(echo a) $( '` or an unclosed backtick in a body, neither bash nor dash runs the later `$(…)`, and the gate matches.
- **New refusals are real:** README code fences in an unquoted heredoc, `` `git checkout -b wip` `` in notes, and `x=$(git branch aps-1 …)`. Both shells actually run these commands, so the refusals are correct, not false ones.
- **Directories:** a `cd` inside a substitution does not move the outer command.

**Commands run:**
- `session-gates.py --self-test` on d8aa744: PASS.
- `scripts/check.py`: **exit 1**, because the `scripts/progress-diagram.py --self-test` failed (`ambysto-graph render … Validation INVALID`). That file is not in this diff, so it looks like this machine's setup, but your "check.py PASS" did not reproduce here.
- Differential fuzz, about 250k generated commands: 0 old-only git calls, 0 changes to main's top-level reading, 0 exceptions, 0 over 0.5 s. Some commands that only 4b83421's new readings found are gone, but none of them was a git call.
- Bash and dash stub probes: 30 cases.
- Timing on inputs up to 130 KB (deep nesting, thousands of backticks and heredocs): at most 0.18 s.

**Not run:**
- An end-to-end gate test in a scratch git repo: my hooks block `git init`.
- zsh: not installed.
- pyflakes: not installed.
