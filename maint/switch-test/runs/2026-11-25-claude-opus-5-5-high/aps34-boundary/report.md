**FAIL**

The change only reaches autonomous runs: `boundary` is wired only from `hooks/autonomous-settings.json`, not from `agents/`, `global/`, `skills/` or `templates/` (checked by grep). `install.py` copies the JSON, and `check.py` checks its shape. But ordinary, non-evasive commands still get past four items on the human-only list. I probed a scratch copy of the script against a `/tmp` repo.

1. **MAJOR**, `hooks/agent-guard.py` `boundary_git` (`if len(names) <= 1`): the guard checks the current branch only for a bare `git push`. On `main`, `git push -u origin HEAD`, `git push origin HEAD` and `git push origin @` are all allowed, and each pushes to main. `git push -u origin HEAD` is the most common push form an agent uses. `HEAD` and `@` should be treated as the current branch.

2. **MAJOR**, `check_boundary` publish check (`first in PUBLISH[name]`): it looks only at the first argument. These all pass: `pnpm -r publish`, `npm -w pkg publish`, `npm --workspace pkg publish`, `npx npm publish`, `python3 -m twine upload dist/*`, `docker buildx build --push`, `docker image push`. A publish can't be undone, and the docs don't list these gaps.

3. **MAJOR**, `boundary_bd` (`enumerate(rest[:-1] + [""])`): the status scan drops the last argument. So `bd update tr-1 --status=closed` closes the bead without the gate/owner check. Mutation check: fixing this line still passes the self-test, so no test covers it.

4. **MAJOR**, `BD_UPDATE_OK`: it allows `-p/--priority`, `--add-label`, `--defer` and `--due`, and `bd label add` is allowed too. The intent lets an agent change only status, evidence, cost and the claim, and makes a bead optional when it has priority 4 or the label `optional`. So `bd update tr-1 -p 4` or `--add-label optional` drops a bead from "done" without the owner. That is a scope change.

5. MINOR, realistic: `bd close` and `bd update -s closed` with no id skip the `bd show` check, because the id list is empty. If bd 1.3.1 defaults to the last-touched bead, this lets a gate be closed. It should block when no id is given.

6. MINOR, realistic: the DO_NOT_TRACK regex matches anywhere in the command. `DO_NOT_TRACK=1 bd ready && bd ready` and `echo DO_NOT_TRACK=1; bd ready` pass, yet the second `bd` sends metrics. The check should be per segment.

7. MINOR, realistic: the protected patterns are matched from the repo root and are case-sensitive. `LICENCE`, `license.md` and `pkg/LICENSE` are all editable. The README claims "licences" without that limit.

8. MINOR, realistic: `SECRET_PATH` doesn't cover `.env`, so `cat .env` and `echo k > .env` pass. The Read tool isn't checked either: reading `~/.ssh/id_ed25519` with Read is allowed, while `cat` of the same file is blocked.

9. MINOR, realistic, false block: `git log -- .claude/settings.json` and `git diff .claude/agents/x.md` are blocked, because `git` isn't in `READERS`.

10. MINOR, cheap to close: `bd duplicates`/`find-duplicates` are on the read list, though they may have merge flags (not verified, no bd). `gh api` with PATCH on `/git/refs/heads/main`, POST to `/git/refs` with a tag ref, or PUT to `/contents` with `branch=main` all pass. MCP tools aren't mentioned in the new docs paragraph.

11. NIT: a malformed `.claude/boundary.json` (a list, or `"protected"` as a string) blocks every write in that repo with a generic "could not check" message. That fails closed, which is good, but the message doesn't name the file.

**Commands run**
- `python3 scripts/check.py`: PASS, exit 0.
- `python3 hooks/agent-guard.py --self-test`: PASS (132 command cases, the work-tree watch, 77 boundary cases).
- Mutation 1, removing the gate/owner-label check in close: 4 self-test failures (caught).
- Mutation 2, removing the main/master refspec match: 2 failures (caught).
- Mutation 3, fixing the off-by-one in issue 3: still PASS, so that path has no test.
- Probe script: about 60 commands and edits, with the results above.

**Not run**
- Real `bd` 1.3.1 flags: no beads binary on this machine. So I could not confirm that `bd -C <dir> show <id> --json` exists (the self-test's fake `bd` assumes it does), the no-id close behaviour in issue 5, or the merge flags in issue 10.
- `install.py --check`: it compares against this machine's `~/.claude`, which isn't the change under review.
- A live `claude --settings` run.
