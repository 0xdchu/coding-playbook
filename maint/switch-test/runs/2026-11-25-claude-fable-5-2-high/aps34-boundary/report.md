**FAIL** — 4 MAJOR. All issues are in `hooks/agent-guard.py` and were reproduced on a scratch copy.

1. **MAJOR, `:527`, `:532` — gate/owner close check skipped by `=` flags.** These are allowed for a gate or a `human` bead: `bd close --reason=done tr-gate`, `bd update tr-gate --status=closed`, `bd update --status=closed tr-gate`. The id after a `--flag=value` word is dropped, and a trailing `--status=closed` is never read. A close with no id (`xargs bd close`) is also unchecked.
2. **MAJOR, `:430` — push to main.** On `main`, `git push origin HEAD`, `git push -u origin HEAD` and `git push origin @` are allowed; the branch is read only when no refspec is given.
3. **MAJOR, `:724` — secret files through the Read tool.** `Read ~/.ssh/id_ed25519` and `Grep` on `~/.ssh` exit 0 while `cat` is blocked. `SECRET_PATH` (`:340`) also lacks `.env`, `*.key` and `~/.aws/credentials`. README claims "keys and secret files"; the Open note lists only write gaps.
4. **MAJOR, `:350`, `:358` — bd allowlist slips (checked against v1.3.1 source).**
   - `bd duplicates --auto-merge` and `bd orphans --fix` close or merge unnamed beads with no gate check.
   - `bd update -p 4`, `--add-label optional` and `bd tag <id> optional` make a bead optional, so it no longer blocks "done".
   - `bd create --deps blocks:<id>` changes an existing bead's deps.
   - `-h` anywhere allows any subcommand.
   - Title, acceptance, design, type and parent flags are all blocked.
5. **MINOR realistic, `:488` — `DO_NOT_TRACK=1` matched anywhere in the text.** `DO_NOT_TRACK=1 bd ready && bd update x --claim` and `bd ready # DO_NOT_TRACK=1` pass.
6. **MINOR realistic — false blocks of ordinary work.**
   - `bd update x --append-notes '- ran pytest'` (`:520`) and `bd close x -m done`.
   - Commit or PR text naming `.npmrc`, `id_rsa` or `.claude/settings.json`.
   - `cat .npmrc`, `curl --cacert ca.pem`, `pytest tests/secrets/…`.
   - `cd "$(git rev-parse --show-toplevel)" && git push`.
7. **MINOR realistic, `:376`, `:384` — plain publish, sign and tag forms pass.** `python3 -m twine upload`, `npx vsce publish`, `npx vercel --prod`, `docker buildx build --push`, `gpg -ab`, `git push origin v1.0.0`, `git push origin tag v1`, `gh api … /git/refs -f ref=refs/tags/v1`. Cheap to close: treat `npx` and `python -m` as wrappers, scan field values.
8. **MINOR realistic, `:348`, `:575` — protected paths.**
   - `LICENCE`, `license` and `pkg/LICENSE` are unprotected.
   - A `boundary.json` with `"docs/api/"` or a `Protected` key silently protects nothing.
   - `pushd docs/spec && echo x > a.md` passes.
   - `rm`, `mv` and `git rm` of a protected file pass; the Open note names only `sed -i` and `cp`.
   - An untracked `boundary.json` is absent in a worktree, and there are no defaults outside a repo (hypothetical: runs work in repos).
   - Symlinks, `..` and invalid JSON are handled and fail closed.
9. **MINOR realistic, `:961` — tests bypass `main()`.** Two mutations survive: Edit/Write never routed to `boundary_edit`, and boundary Bash commands checked as `build`.
10. **NIT.** The module docstring, CLAUDE.md Verify and the HARD list do not mention `boundary` or the JSON; `check.py` does not check the hook `type`; a machine path (`<a local token file, redacted>`) sits in a test case.

Not affected: build and review modes are unchanged, only the settings file wires `boundary`, `install.py` installs the JSON, and ordinary commit, feature-branch push, PR, comment and `bd ready/show/create/update --claim/close` work.

**Commands run**
- `python3 scripts/check.py`: PASS, exit 0.
- `python3 hooks/agent-guard.py --self-test`: PASS, 132 + 77 cases.
- Mutations of the guard: 14 of 16 killed (survivors in issue 9). `check.py` mutations: 5 of 6 killed (hook `type` survives).
- `python3 scripts/install.py --check`: exit 1; this machine's install differs from this snapshot, so it says nothing about the change.

**Not run**
- Real `bd`: no binary on PATH. Flags were read from the public v1.3.1 source and the close check was run against a stand-in `bd show`.
- A live `claude --settings` session.
