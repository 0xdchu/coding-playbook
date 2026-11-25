**FAIL**

1. **MAJOR** — `hooks/agent-guard.py:20,110` (tokenizer). Glued punctuation (`);`, `)|`, `&&(`, `)>`) is not an operator, and `then`/`do`/`else` are read as the command name. These exit 0:
   - build: `msg=$(cat m.txt); git commit -m "$msg"`
   - build: `(cd sub && make); git commit -m x`
   - build: `if make test; then git commit -am x; fi`
   - build: `for b in a b; do git push origin $b; done`
   - review: `for f in *.pyc; do rm "$f"; done`

2. **MAJOR** — `:65` heredoc regex matches `<<` inside quotes and here-strings, so every later line goes unchecked: `grep -rn "cout << endl" src⏎git commit -m x`, `grep -c foo <<< "abc"⏎git commit -m x`. `:216` accepts only an exact `-c`: `bash -lc 'git commit -m x'` passes.

3. **MINOR, realistic** — other build slips:
   - `:147` wrappers with a valued option: `xargs -n 1 git push`, `timeout -k 5 30 git push`, `sudo -u me git push`.
   - `:168,172`: `git checkout main --`, `git checkout -b topic --`, `git stash branch topic`, `git branch -v newbranch`.
   - `:191`: `gh api -XPOST repos/o/r/issues`.
   - `git \⏎ commit -m x`.

4. **MINOR, realistic** — `:44-48,230` reviewer writes that pass: `find . -name '*.pyc' -delete`, `find … -exec rm {} \;`, `sed -Ei`, `perl -0pi`, `make >& out.log`, `remove-item x`, `Add-Content`.

5. **MINOR, realistic** — `:202` relative paths resolve against the hook's cwd. From a cwd under `/tmp`, review `rm -rf src && echo x > README.md` exits 0. There the self-test gives 51/58 and `check.py` fails, so Verify depends on where the repo is checked out.

6. **MINOR, realistic** — `:246-258` fail-open: only `Blocked` is caught. Non-object JSON, a string `tool_input` or a non-string `command` exit 1, which does not block. Missing `python3` exits 127, also non-blocking and silent; README and CLAUDE.md "Open" do not say the guard is then off. A missing script exits 2 (closed).

7. **MINOR, realistic** — false blocks:
   - Reads: `git tag`, `git reflog -5`, `git config user.name`, `git fetch origin main`, `gh -R o/r pr view 5`, `gh api graphql -f query=…`.
   - Parsing: `# don't forget⏎make test`; `grep -rn '`git push`' README.md`.
   - Reviewer temp work the task allows: `echo x > "$TMPDIR/x"`, `cd /tmp/rv && touch a`, `chmod +x /tmp/rv/run.sh`, `sed -i … /tmp/rv/f`, `git init /tmp/rv/repo`.

8. **MINOR, realistic** — `scripts/check.py:94-97` are substring checks: `command: 'true # python3 "$HOME/…" review'` passes. The self-test has no case for issues 1–4.

9. **MINOR, realistic** — `README.md:29` still says "agents and skills into ~/.claude"; hooks are missing.

Installer change is sound: it backs up a differing file, never deletes, and `--check` reports the hook file.

**Run**
- `python3 scripts/check.py`: PASS, exit 0.
- `python3 hooks/agent-guard.py --self-test`: 58/58; 51/58 from a `/tmp` cwd.
- `python3 scripts/install.py --check`: exit 1; this machine differs, including the missing hook file.
- About 150 piped-JSON probes: results above.
- Fuzz of 200,000 commands: no uncaught exception.
- Mutation checks in temp copies: hook removed from `builder.md` fails `check.py`; `commit` dropped from the guard fails `check.py`; the neutered command of issue 8 passes.

**Not run**
- `install.py` without `--check`: forbidden here.
- The live agent run through `/agents` that CLAUDE.md Verify requires: needs an install and a new session, so whether the frontmatter hook fires is unverified.
- Windows and PowerShell: wrong OS.
