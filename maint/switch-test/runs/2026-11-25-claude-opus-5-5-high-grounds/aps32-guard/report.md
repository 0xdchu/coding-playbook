**FAIL**

This fails on one MAJOR issue, the gap in parsing shell keywords, plus several MINOR gaps. The guard catches simple `git` and `gh` commands well. Quoting, `git -C`, `-c`, `--git-dir`, `env`, `command`, `xargs`, subshells, `$(...)`, `eval` and `&&`/`;` chains are all blocked.

1. **MAJOR**, `hooks/agent-guard.py:137` (`command_words`): shell keywords are not treated as the start of a command. The guard reads `if`, `then`, `do`, `else`, `while` or `until` as the command name. These all exit 0:
   - `if git commit -m x; then echo ok; fi`
   - `for i in 1; do git commit -m x; done`
   - `while true; do git push; break; done`

   Loops and conditionals are normal agent shell, so a reviewer's `for f in a b; do rm $f; done` also gets through. Joined punctuation has the same gap: `x=1;(git push)` and `true&&(git push)`. So does a line break after `git` (`git \` newline `push`). None of these are in the self-test.
2. **MINOR** (realistic), `:216` and `:144-150`: shell flags given together and wrapper flags that take a value are skipped wrongly. These pass: `bash -lc "git push"`, `sh -xc …`, `echo git push | bash`, `sudo -u bob git push`, `nice -n 5 git push`, `timeout -s KILL 30 git push` and `env -u X git push`.
3. **MINOR** (realistic), `:239-259`, fail-open:
   - Any exception the guard does not catch exits 1. Claude Code treats that as a non-blocking error, so the command runs. Examples: a NUL character in a redirect target (`ValueError`), or `tool_input` that is not a dict (`AttributeError`).
   - A missing `python3` exits 127, which also lets the command through. This is likely on Windows.
   - The docstring claims "When it cannot parse a command it blocks it". README and CLAUDE.md don't say a missing `python3` turns the guard off.
   - A missing script does exit 2, so that case blocks.
4. **MINOR** (realistic), commands that still let a reviewer write files:
   - `make >& build.log`: line 119 reads `>&` as a file-descriptor copy, but here it writes the file.
   - In-place edits with other flag forms: `sed -Ei`, `perl -0pi`, `awk -i inplace`.
   - PowerShell names in lower case or as aliases: `set-content`, `sc`, `del`.
   - Options that write somewhere else: `cp -t src /tmp/a`, `curl -o src/a.py`, `git diff --output=src/x`.
5. **MINOR** (realistic), branch and tag writes the builder can still make:
   - `git checkout -b topic -- x` passes because it contains `--` (`:172`).
   - `git branch --list -D x` and `git tag -l v1 -d v1` pass because only the first argument is checked (`:168`).
   - `gh api -XPOST …` and `gh api … -XDELETE` pass (`:191`).
6. **MINOR** (realistic), false positives that block normal reviewer work. The agent sees the reason and can adapt, but each costs it a retry:
   - Redirects to `"$tmp"` or `"$TMPDIR/x"` are blocked, because variables are not expanded.
   - After `cd /tmp/rv`, a redirect to a relative path is blocked.
   - `git worktree add /tmp/w` is blocked, though the task allows a temp dir.
   - `gh -R o/r pr view 3` is blocked, because the flag's value is read as the subcommand. This one hits the builder too.
7. **MINOR** (realistic), `scripts/install.py:67-72`: agents are installed before the hook. If the run fails in between, every Bash call of a guarded agent is blocked (`python3` exits 2 on a missing file). That fails closed, but installing hooks first is safer. Otherwise the installer still never deletes, backs up before overwriting, and `--check` reports the hook.

**Commands run**
- `python3 scripts/check.py`: PASS, exit 0.
- `python3 hooks/agent-guard.py --self-test`: PASS, 58/58.
- `python3 scripts/install.py --check`: exit 1. It correctly reports `agents/*.md` and `hooks/claudecode-guide/agent-guard.py` as differing, because they are not installed on this machine yet.
- About 130 commands piped into the guard as JSON in both modes, plus bad input, a missing script and a missing interpreter.

**Not run**
- `install.py` without `--check`: forbidden by the task.
- A real `/agents` session running the guarded agents on a known diff: that needs a fresh interactive session, as CLAUDE.md's Verify asks.
- Windows: no machine.
- Mutation check: the self-test has no cases for keywords, joined flags or `>&`. It would stay green while issues 1, 2 and 4 are present.

Pre-existing, outside this diff: `agents/hard-reviewer.md` and `README.md` still say Fable 5.1, but the global CLAUDE.md records the switch to Fable 5.2.
