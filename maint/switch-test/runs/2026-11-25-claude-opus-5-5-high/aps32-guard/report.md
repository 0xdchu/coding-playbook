**FAIL**

1. **MAJOR**, `hooks/agent-guard.py:110-131` and `:137-156`. The guard never skips shell keywords (`if`, `then`, `else`, `elif`, `do`, `while`, `until`). The first word after one of them is taken as the command, so the git command after it is never checked. All of these exit 0, in both modes: `if ! git diff --quiet; then git commit -am wip; fi`, `for b in a b; do git branch -D $b; done`, `until git push; do sleep 1; done`, and in review mode `if true; then rm -rf src; fi`. These are everyday shell forms, so this is the kind of mistake the guard exists to catch. The self-test has no compound-command case, so its 58/58 gives false confidence.

2. **MINOR (realistic)**, `:216` and `:191-194`. Combined flags get through: `bash -lc 'git push'`, `bash -xc …`, `gh api -XPOST …`, `gh api … -Ftitle=x` and `sed -Ei …` (review mode). Wrapper options that take a value also get through: `nice -n 5 git push`, `timeout -s KILL 30 git push`, `xargs -n 1 git push`, `sudo -u bob git push`.

3. **MINOR (realistic)**: false positives that block normal read work.
   - Build mode blocks `git tag` (a list) and `git config user.email` / `git config --global --get x` (reads).
   - `gh -R o/r pr view 3` is blocked because `o/r` is read as the subcommand.
   - Read-only `gh api graphql -f query='query{…}'` is blocked.
   - Review mode blocks `echo x > "$TMPDIR/a"` and `tmp=$(mktemp) && … > "$tmp"`: the target is checked before variables expand, which breaks the usual mktemp pattern.
   - PowerShell `> $env:TEMP\a.txt` is blocked.

4. **MINOR (realistic)**: the guard fails open when `python3` is missing. A missing interpreter exits 127; the Windows Store stub exits 9009. Claude Code treats both as non-blocking errors, so the agent's Bash runs unguarded. The `install.py:70` comment ("without them … all blocked") holds only when the script is missing (python3 exits 2). CLAUDE.md "Open" and the README say "Needs python3" but not that the guard is silently off without it.

5. **MINOR (hypothetical: Claude Code always sends an object with a string `command`, and fuzzing `check()` with 400k random strings raised nothing)**, `:247-255`. Input of an unexpected shape (`[]`, `null`, a `tool_input` that is a string, a `command` that is a list) raises a traceback and exits 1, which lets the command run. That contradicts the docstring ("When it cannot parse a command it blocks it"). Wrapping `main` so it exits 2 on any exception closes it.

6. **MINOR (realistic)**: PowerShell checks are case-sensitive and know no aliases. `remove-item src`, `ri src`, `Add-Content README.md x` and `git.exe commit` all exit 0. CLAUDE.md "Open" says Windows is untested, but not that these get through.

7. **MINOR (realistic)**: review-mode file writes the guard misses: `git diff --output=src/x`, `git format-patch`, `git update-index`, `find -delete`, `curl -o`, `wget -O`, `tar x`, and `$(…)` inside an unquoted heredoc (its body is dropped before substitutions are found). CLAUDE.md "Open" names only interpreters and build scripts as gaps, so the docs understate this.

8. **MINOR (hypothetical: no real mistake puts a read flag before a delete)**, `:168`. Only the first argument is compared against the read list, so `git branch -a -D main` and `git tag -l -d v1` exit 0.

9. **MINOR (realistic, docs)**, `CLAUDE.md:18`. The HARD line on "the installer's writes to `~/.claude`" doesn't list the new `hooks/claudecode-guide` folder. The installer change itself is correct: it backs up a differing file, never deletes, and `--check` reports the hook.

**Commands run**
- `python3 scripts/check.py`: PASS, exit 0.
- `python3 hooks/agent-guard.py --self-test`: PASS, 58/58.
- `python3 scripts/install.py --check`: exit 1. It lists the hook and the agents as `differs`, which is right for this machine, and wrote nothing.
- About 200 JSON probes through the guard in build and review modes, Bash and PowerShell, plus odd inputs and missing python3 or script.
- A fuzz of `check()` with 200k random strings in each mode: no exceptions.

**Not run**
- The project's Verify step for an agent change (new session, `/agents`, run the agent on a known diff): it needs an interactive session and the hook installed. So I couldn't confirm that Claude Code runs this frontmatter hook and passes the exit-2 reason back to the agent.
- `install.py` without `--check`: forbidden.
- Anything on Windows or real PowerShell: none on this machine.
