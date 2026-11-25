**FAIL**

Each MAJOR is an ordinary, non-evasive shell form that the guard allows; all were confirmed by piping JSON into `hooks/agent-guard.py`.

1. **MAJOR** `hooks/agent-guard.py:20,110` — an operator glued to `)` is not split, because shlex merges `);` into one token that is not in `OPERATORS`. Allowed: `(cd sub && make test); git commit -am x`, `v=$(cat VERSION); git tag "v$v"`, `(make)&& git push`.
2. **MAJOR** `:137-156` — shell keywords are taken as the command name. Allowed: `if make test; then git commit -am x; fi`, `for b in a b; do git push origin $b; done`; in review, `for f in a b; do rm $f; done`.
3. **MAJOR** `:90` — newline becomes ` ; ` before lexing, so backslash continuations split one command in two. Allowed: `gh api repos/o/r/issues \⏎ -f title=x`, `gh api \⏎ -X POST …`, `git -C ../repo \⏎ push`. It also blocks `cp a.txt \⏎ /tmp/rv/` in review.
4. **MAJOR** `:216` — only a separate `-c` is recognised. Allowed: `bash -lc 'git commit -m x'`, `sh -ec 'git push'`.
5. **MINOR, realistic** `:56-66` — any `<< word` without a terminator drops every later line unchecked. Allowed: `grep "cout << value" src⏎git push`, `echo $((1 << n))⏎git commit`, `bash <<'EOF'⏎git commit⏎EOF`.
6. **MINOR, realistic** — further forms allowed:
   - Review writes: `sed -Ei`, `find -delete`, `curl -o`, `echo x >& out.txt`, `remove-item`, `Add-Content`.
   - Wrappers with option values: `xargs -n 1 git push`, `sudo -u me …`, `env -u FOO …`, `timeout -s KILL 30 …`.
   - git and gh: `gh api -XPOST`, `gh api … -ftitle=x`, `git.exe commit`, `git checkout -b topic --`, `git stash branch topic`, `git branch -v new`, `cat <(git push)`.
7. **MINOR, realistic** — false positives on normal work:
   - A comment line with an apostrophe (`# builder's output⏎python3 scripts/check.py`) blocks the whole command.
   - Reads: `git tag`, `git fetch` (not in the task's forbidden list), `git config user.name`, `git reflog -5`, `git branch --sort=…`, `git submodule update --init`, `git apply --check`, `gh --version`, `command -v gh`, `gh api graphql -f query=…`, ``grep '`git commit`' README.md``.
   - Review temp use: `cd /tmp/rv && echo x > out.txt`, and PowerShell `2>$null`.
8. **MINOR, realistic** — a missing `python3` fails open: the hook exits 127, which Claude Code treats as non-blocking (not run here). `check.py` self-tests with `sys.executable` and the docs invoke `python`, so both checks stay green with the guard off. `install.py:70` and "Open" do not say so; a missing script does fail closed (python exits 2).
9. **MINOR, hypothetical** `:246-258` — `main()` catches only `Blocked`; any other exception exits 1, which fails open. Confirmed with `[]`, `null`, a non-string `command`, a NUL in a redirect target and deep `eval`. Claude Code always sends an object with a string command, so these never arrive. The docstring (`:11`) claims unparsable commands are blocked.
10. **MINOR, realistic** — the self-test calls `check()` only, never `main()` (stdin, exit 2, stderr reason), and covers none of the forms in 1–5. `check.py:103-104` prints only stdout, so a crashing self-test fails with an empty message.
11. **MINOR, realistic** — commit `ea89167` lacks the Co-Authored-By trailer that CLAUDE.md Rules require (`8dd835a` has it).
12. **MINOR, realistic** — the README row says the hook "blocks commit, push, merge…" and "Open" names only interpreters, build scripts and MCP as gaps; issues 1–5 are undocumented.

The installer change is sound: it reuses `install_file`, backs up first, never deletes, and `--check` writes nothing and reports the hook file. The frontmatter hooks and `check.py`'s `GUARDED` checks match.

**Run**
- `python3 scripts/check.py`: PASS.
- `python3 hooks/agent-guard.py --self-test`: PASS 58/58.
- `python3 scripts/install.py --check`: exit 1, because this machine's installed copy differs from the clone (expected here).
- 88 entry-point probes: 51 differed from expectation.
- 13 odd-input probes: results in issue 9.

**Not run**
- `install.py` without `--check`: forbidden by the task.
- Agent run in a fresh session with the result recorded in the PR: no PR or remote in this clone.
- Windows / PowerShell: wrong OS.
- Mutation check: not done.
