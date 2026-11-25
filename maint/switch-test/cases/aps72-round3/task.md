Review a HARD change: a PreToolUse hook that runs in every session and guards branch names and pushes to `main`.

Repo: {repo}. Ticket APS-72, three commits on top of 4b83421 (main when the change was made). Review `git diff {range}`. Do not check out or edit anything in that repo. Read with `git show`/`git diff`, and copy files to your own temp dir to run them.

The owner asked for this fix ("continue 72"). The task: `echo $(git push origin main)` passed every gate, because the words inside `$( )` and backticks were blanked and never read as commands. Requirements:
- the commands inside substitutions are checked by every gate (branch names, no_push, trees under review);
- no refusal that 4b83421 makes is lost, per the APS-71 design and the memory lesson `keep-old-parser-as-a-reading`;
- no new false refusals on realistic commands.

What changed:
- `split_substitutions` returns the bodies;
- `commands_read` reads each body recursively (`MAX_NEST` = 8) in the cwd the substitution runs in;
- the new readings keep a backtick substitution in one piece (unquoted and in double quotes), and main's reading still splits inside it;
- the `commands()` fast path now also takes the readings path when backticks are present.

My checks:
- self-test PASS, `check.py` PASS;
- 13/13 mutations of the new code killed;
- 14,591 real transcript commands give identical verdicts and trees to main;
- fuzz with git inside substitutions against bash and dash: no old-deny/new-allow. The new refusals I saw were `${x:-$(git …)}` with `x` set (the shell skips the push; documented), `$((cmd))` aborts, and the stub's missing `cat`.

Note: dash rejects `$((cmd); …)` as a syntax error. The gate still reads it as a command, which only adds a refusal there.

Check especially that main's reading is 4b83421's reading (strip_heredocs and split_substitutions under READING main), and whether the change added anything new. One rule to check: an unclosed substitution in a heredoc body ends the body's list, since bash runs nothing after it and dash runs none of the body.

Return PASS or FAIL with numbered issues, at most 500 words.
