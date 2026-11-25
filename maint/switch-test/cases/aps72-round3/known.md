# Known findings: aps72-round3

The original round-3 report, verbatim but for its paths (APS-91 layout, the machine's user name as `<user>`) (claude-fable-5-2). It PASSed; its three MINORs were fixed in a fourth round (ambysto/coding-playbook PR #71). Issue n of the report is `K{n}` in results.md.

---

**PASS** (APS-72 round 3, commit d8aa744)

All five round 2 issues are fixed and I found no BLOCKER or MAJOR. Three MINORs remain, all in shapes origin/main never read either.

**Round 2 issues**
1. **MAJOR (injected line in main's reading): fixed.**
   - Under `READING = ("main","all")`, 400,000 token-soup commands with heredocs, `$((` and backticks give identical `strip_heredocs`, `pieces` and blanked text on origin/main and here. `commands_read` is an ordered superset.
   - The dash case in `lost1.txt` is refused again.
2. **Quadratic scans: fixed.** 4,000 × `$('` in a body takes 0.02 s (was 36 s); 4,000 nested `$((` takes 0.9 s (was 89 s).
3. **Heredoc inside an injected substitution: fixed.** The quoted-inner case is allowed; the unquoted-inner one is refused.
4. **Newline test: added**; the mutant is killed.
5. **Docs: fixed.** "Linear" is gone; the 16-`$((` cap and the unclosed rule are stated.

**The unclosed rule**
- It holds against real shells. In 27,000 heredoc bodies with unclosed `$(`, `$((` and lone backticks, there was no case where bash or dash ran a git command the gate allowed.
- Spot checks: for a body with an unclosed `$( '`, a lone backtick or an unclosed `$((` before `$(git push origin main)`, bash runs no push and dash rejects the script.

**Issues**
1. **MINOR — the unclosed rule trusts the scanner** (`hooks/gates/session-gates.py:145`, `:154`).
   - Where the new scanner wrongly sees a substitution as unclosed, the rest of the body goes unread.
   - `cat <<EOF\n$(time case a in) $(git push origin main)\nEOF`: dash runs the push and the gate allows it.
   - Same on origin/main, but b2dc5db refused it. The doc states the rule, not this consequence.
2. **MINOR — the `ARITH_SCANS` cap leaves a gap, as documented.** Sixteen `$((1))` followed by `$((git push origin main); true)` is allowed and bash pushes; with fifteen it is refused.
3. **MINOR — tests.** 18 of 19 round 3 mutants killed. The survivor removes the `MAX_NEST` bound on the nested strip; a fault there would only skip a new reading.

**Other observations**
- Cost is still about 12× origin/main at 8 nesting levels (320 KB: 11.2 s against 1.0 s), now documented.
- 8 of the 27,000 bodies were refused where no shell runs anything. Every one has a body the shell rejects, and round 2 refused the same eight.

**Other checks**
- Invariant fuzz against origin/main, 350,000 commands (200,000 heredoc-focused): no refusal, target or recorded tree lost, no exception.
- Shell fuzz with git in substitutions (2,000 each, bash and dash): no old-deny/new-allow.
- 9,000 heredoc bodies from the round 2 grammar: no gap, no false refusal.

**Run**
- `python3 hooks/gates/session-gates.py --self-test`: PASS.
- `systemd-run --user --scope -q -p MemoryMax=4G python3 maint/check.py`: PASS, exit 0.
- `python3 maint/install.py --check`: exit 1, as expected before merge.

**Not run:** zsh; a live hook call; your transcript replay.

Tools are in `/tmp/claude-1000/-home-<user>-work-0xdonniechu/d07dfdaa-2116-4b20-8d25-7a68b50be988/scratchpad/rv11/` (`mainsame.py`, `hfr2.py`, `probeF.py`, `mutate6.py`, `hinv.py`, `perf4.py`).
