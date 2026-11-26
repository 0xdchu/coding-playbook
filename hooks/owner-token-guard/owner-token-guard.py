#!/usr/bin/env python3
"""PreToolUse hook for every Claude Code session: an agent never takes the owner's GitHub token (APS-37).

Agents act as the bot account where the owner said so (ambysto-memory), and GitHub refuses the bot's merges.
That boundary holds only while no agent can read the owner's token, which sits in the system keyring and is
reachable by any process of this user. This hook closes the paths an agent would use through its tools:

  deny  a command that asks gh for a token or switches account (`gh auth token`, `auth status --show-token`,
        `auth switch`, `auth logout`, and the same words written as a list, e.g. `["gh", "auth", "token"]`),
        reads gh's hosts file, or reads the keyring (`secret-tool lookup`, the keyring folder, python `keyring`);
        a Read, Grep or Glob of gh's hosts file or the keyring folder
  allow one switch (owner decision 2026-11-26): back to the personal account, `gh auth switch --user 0xdonniechu`
        (the name gh still keeps in the keyring since the account was renamed to `0xdchu`; gh matches on that
        name, and the guard accepts both). The gh wrapper picks `ambysto` by folder, so no agent needs to switch
        to it. The WHOLE command must be exactly that: another account, no `--user` (gh asks interactively),
        anything before it (`cd x &&`, `sudo`, a variable, a line continuation) or after it (a second command, a
        redirection, a suffix, a substitution) and the exception does not apply, the deny patterns judge the
        command as before. The switch changes machine-wide state, so it also undoes a switch the owner made on
        purpose; run it from outside ~/work/ambysto, where the wrapper sets GH_TOKEN for gh
  ask   a command that sets AMBYSTO_OWNER (the owner's own merge in ambysto-memory): Claude Code asks the owner
        to confirm each time; a run with nobody at the keyboard cannot confirm, so it is refused there

It reads the hook JSON on stdin and prints a decision; anything else is let through. It catches mistakes and
casual use, not every way a determined process could reach the keyring: a script file that does it, words split
or encoded (`au''th`, `$a token`, base64 with `eval`), or `cd` into gh's folder before reading a file are not
seen, nor `git credential-store get` (it reads `~/.git-credentials`, not the keyring); nor is AMBYSTO_OWNER set without the literal word (`export $(cat f)`). Matching is anchored to `gh`, git's
credential commands and the keyring, so prose such as a commit message about "auth tokens" is not refused. The scripts that legitimately need the owner's token (the gh wrapper, the git credential helper) run
outside the agent's tools and are not seen here.

  python3 owner-token-guard.py --self-test
"""
import json
import re
import sys

# One shell command segment (up to ; & | or a new line), so words of two different commands never combine.
SEG = r"(?:[^;&|\n\\]|\\\n|\\.)*"  # a backslash-continued line stays one segment
GH = r"(?:^|[\s;&|(`'\"/])gh(?:\.real)?\b"
TOKEN_COMMANDS = [
    (re.compile(GH + SEG + r"\bauth\b" + SEG + r"\btoken\b", re.I), "asks gh for a token"),
    (re.compile(GH + SEG + r"\bauth\b" + SEG + r"(?:--show-token|\s-t\b|\s-[a-z]*t[a-z]*\b)", re.I),
     "asks gh to show a token"),
    (re.compile(GH + SEG + r"\bauth\b" + SEG + r"\b(?:switch|logout|refresh)\b", re.I),
     "switches, refreshes or signs out a gh account"),
    (re.compile(r"[\"']gh[\"']" + r"[^\]\n]*[\"']auth[\"'][^\]\n]*[\"'](?:token|switch|logout)[\"']", re.I),
     "asks gh for a token"),
    (re.compile(GH + SEG + r"\b(?:alias\s+(?:set|import)|extension\s+(?:install|create|upgrade))\b", re.I),
     "adds a gh alias or extension, which runs with the owner's token"),
    (re.compile(r"\bgit\b" + SEG + r"\bcredential\s+(?:fill|get)\b", re.I), "asks git for a stored credential"),
    (re.compile(r"git-credential-[\w.-]+(?:\s|$)" + SEG + r"\bget\b|\bcredential-ambysto\b", re.I),
     "runs a git credential helper"),
    (re.compile(r"\bGIT_TRACE_REDACT\s*=|\bGIT_TRACE_CURL\b|\bGIT_CURL_VERBOSE\b"), "turns on git's credential traces"),
    (re.compile(r"\.config/gh/(?:[\w.*-]*\.ya?ml|\*)", re.I), "reads gh's config files"),
    (re.compile(r"\bsecret-tool\s+(?:lookup|search)\b", re.I), "reads the system keyring"),
    (re.compile(r"\.local/share/keyrings\b", re.I), "reads the keyring folder"),
    (re.compile(r"\b(?:import\s+keyring|from\s+keyring\s+import|import\s+secretstorage)\b|\bkeyring\.get_password\b"
                r"|(?:^|[\s;&|])keyring\s+get\b", re.I), "reads the keyring"),
]
# The one switch an agent may run: back to the personal account. The WHOLE command must be this and nothing else:
# nothing before it (no `cd x &&`, no `sudo`, no variable), nothing after it (no second command, no redirection),
# at most one trailing newline. It is matched with fullmatch, so there is no splicing: a command that is not exactly
# this shape is judged by the deny patterns below as if this exception did not exist. (An earlier draft cut the
# shape out of a longer command and checked the rest; `&>file` is a redirection, not a separator, and slipped a
# second account name through.) `0xdonniechu` is the name gh keeps in the keyring since the rename to `0xdchu`,
# and the name gh matches on, so it is the form to use; both are accepted here.
PERSONAL = r"(?:0xdonniechu|0xdchu)"
SWITCH_PERSONAL = re.compile(
    r"[ \t]*gh[ \t]+auth[ \t]+switch(?:[ \t]+(?:-h|--hostname)[ =]github\.com)?"
    r"[ \t]+(?:-u|--user)(?:[ \t]+|=)" + PERSONAL + r"[ \t]*\n?")
OWNER = re.compile(r"\bAMBYSTO_OWNER\b")
PATH_FIELDS = ("file_path", "path", "pattern")
SECRET_PATHS = re.compile(r"\.config/gh(?:/|$)|\.local/share/keyrings", re.I)


def decide(event):
    """Return (decision, reason) or None to let the call through."""
    tool = event.get("tool_name", "")
    params = event.get("tool_input") or {}
    if tool == "Bash":
        command = str(params.get("command", ""))
        if SWITCH_PERSONAL.fullmatch(command):
            return None
        for pattern, what in TOKEN_COMMANDS:
            if pattern.search(command):
                return "deny", ("owner-token-guard: this command %s. Agents never take the owner's GitHub token, and "
                                "switch accounts only back to the personal one, as the whole command and nothing "
                                "else: `gh auth switch --user 0xdonniechu` (the name gh keeps in the keyring) "
                                "(APS-37); in ambysto-memory they act as the bot. Anything else: if the owner "
                                "asked for it, they run it themselves." % what)
        if OWNER.search(command):
            return "ask", ("owner-token-guard: this command acts as the owner (AMBYSTO_OWNER). Confirm only if you "
                           "asked for exactly this, e.g. merging a reviewed ambysto-memory PR.")
        return None
    if tool in ("Read", "Grep", "Glob"):
        for field in PATH_FIELDS:
            if SECRET_PATHS.search(str(params.get(field, ""))):
                return "deny", ("owner-token-guard: this reads where the owner's GitHub token is kept. Agents never "
                                "take it (APS-37).")
    return None


def output(decision, reason):
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                              "permissionDecisionReason": reason}})


def self_test():
    deny = [
        "gh auth token", "/usr/bin/gh auth token --user ambysto", "GH_TOKEN=$(gh auth token) gh pr merge 3",
        "env -u GH_TOKEN /usr/bin/gh auth token --user ambysto | head -c 4",
        "python3 -c 'import subprocess; subprocess.run([\"gh\", \"auth\", \"token\"])'",
        "gh auth status --show-token", "gh auth status -t", "gh auth switch --user ambysto", "gh auth logout",
        "cat ~/.config/gh/hosts.yml", "grep oauth /home/x/.config/gh/hosts.yaml",
        "secret-tool lookup service gh:github.com", "ls ~/.local/share/keyrings/",
        "python3 -c 'import keyring; print(keyring.get_password(\"gh:github.com\", \"ambysto\"))'",
        "gh auth --user ambysto token", "gh auth --hostname github.com status -t", "gh auth -t status",
        "printf 'protocol=https\\nhost=github.com\\n' | git credential fill", "git -C x credential get",
        "~/work/ambysto/git-credential-ambysto.sh get", "gh alias set --shell e 'echo $GH_TOKEN'",
        "gh extension install someone/gh-x", "GIT_TRACE_REDACT=0 GIT_CURL_VERBOSE=1 git ls-remote https://github.com/x/y",
        "cat ~/.config/gh/*.yml", "python3 -c 'from keyring import get_password'", "gh auth refresh -s repo",
        "gh auth \\\n  token", "gh \\\n auth status \\\n --show-token",
        # near misses of the one allowed switch
        "gh auth switch -u ambysto", "gh auth switch", "gh auth switch -u 0xdchu2", "gh auth switch -u 0xdchu-x",
        "gh auth switch -u 0xdchu; gh auth token", "gh auth switch -u 0xdchu && gh auth switch -u ambysto",
        "gh auth switch -u 0xdchu $(gh auth token)", "gh auth switch -u 0xdchu -u ambysto",
        "gh auth switch -u ambysto -u 0xdchu", "gh auth switch --user 0xdchu --hostname evil.example",
        "FOO=1 gh auth switch -u 0xdchu", "/usr/bin/gh auth switch -u 0xdchu", "sudo gh auth switch -u 0xdchu",
        "gh auth switch -u 0xdchu\n gh auth token", "gh auth switch -u 0xdchu # then ambysto",
        "gh auth switch -u '0xdchu'", "gh auth switch --user 0xdchu | gh auth logout",
        "echo ok && gh auth switch -u ambysto", "gh auth switch -u 0xDCHU2", "gh auth switch -u 0xdchu\\\n -u ambysto",
        "gh auth logout -u 0xdchu", "gh auth refresh -u 0xdchu", "bash -c 'gh auth switch -u ambysto'",
        # the one allowed switch must be the whole command: nothing around it, in any shell spelling
        "cd ~/work/x && gh auth switch -u 0xdonniechu", "gh auth switch -u 0xdonniechu; gh api user --jq .login",
        "gh auth switch -u 0xdonniechu && true", "gh auth switch -u 0xdonniechu | cat",
        "gh auth switch -u 0xdonniechu 2>&1", "gh auth switch -u 0xdonniechu &", "gh auth switch -u 0xdonniechu\ntrue",
        "\ngh auth switch -u 0xdonniechu", "x=1; gh auth switch -u 0xdonniechu",
        # `&>` and `&>>` are redirections: the words after them still belong to the same command
        "gh auth switch -u 0xdonniechu &>/dev/null -u ambysto", "gh auth switch -u 0xdonniechu &>>/dev/null --user ambysto",
        "gh auth switch -u 0xdonniechu &> /dev/null -h evil.example", "gh auth switch -u 0xdonniechu >&/dev/null -u ambysto",
        # a prefix that hides the wrapper, a line continuation, a redirection or an escaped separator before it
        "sudo \\\ngh auth switch -u 0xdonniechu", "GH_CONFIG_DIR=/tmp/x \\\ngh auth switch -u 0xdonniechu",
        "env -u GH_TOKEN \\\ngh auth switch -u 0xdonniechu", "/usr/bin/gh >&gh auth switch -u 0xdonniechu",
        "/usr/bin/gh >|gh auth switch -u 0xdonniechu", "echo \\;gh auth switch -u 0xdonniechu",
        "echo -u ambysto | xargs /usr/bin/gh >&gh auth switch -u 0xdonniechu",
        "gh auth switch -u 0xdonniechu\r", "gh auth switch -u 0xdonniechu\x0b-u ambysto", "gh auth switch -u 0xdonniechu\\",
    ]
    ask = ["AMBYSTO_OWNER=1 gh pr merge 23 --merge --admin", "export AMBYSTO_OWNER=1; gh pr merge 23",
           "env AMBYSTO_OWNER=1 gh api user"]
    allow = ["gh pr list", "gh api user --jq .login", "gh auth status", "git push origin main",
             "python3 maint/check.py", "grep -n token maint/check.py", "echo authentication tokens are kept",
             "cat ~/.config/ambysto-bot/token.md", "ls ~/.config/gh/", "gh pr create --title 'Auth flow' --body x",
             "git commit -m 'Fix auth token refresh'", "git log --grep 'auth token'", "grep -rn 'auth-token' src/",
             "echo 'see docs/auth/token.md'", "cat docs/auth.token.md", "gh pr view 3 --json title",
             "git credential-cache exit", "gh auth status && git status -t",
             # the one switch agents may run: back to the personal account, as the whole command
             "gh auth switch -u 0xdonniechu", "gh auth switch --user 0xdonniechu", "gh auth switch --user=0xdonniechu",
             "gh auth switch -u 0xdchu", "gh auth switch --user 0xdchu", "gh auth switch --user=0xdchu",
             "gh auth switch --hostname github.com --user 0xdonniechu", "gh auth switch --hostname=github.com --user=0xdchu",
             "gh auth switch -h github.com -u 0xdonniechu", "gh auth switch -h=github.com -u 0xdonniechu",
             "gh auth switch -u 0xdonniechu\n", "  gh auth switch \t --user \t 0xdonniechu  "]
    bad = []
    for command in deny:
        if (decide({"tool_name": "Bash", "tool_input": {"command": command}}) or ("allow",))[0] != "deny":
            bad.append("not denied: %s" % command)
    for command in ask:
        if (decide({"tool_name": "Bash", "tool_input": {"command": command}}) or ("allow",))[0] != "ask":
            bad.append("not asked: %s" % command)
    for command in allow:
        if decide({"tool_name": "Bash", "tool_input": {"command": command}}) is not None:
            bad.append("blocked: %s" % command)
    for tool, params in (("Read", {"file_path": "/home/x/.config/gh/hosts.yml"}),
                         ("Grep", {"pattern": "oauth", "path": "/home/x/.config/gh/hosts.yml"}),
                         ("Glob", {"pattern": "/home/x/.local/share/keyrings/*"}),
                         ("Grep", {"pattern": "oauth", "path": "/home/x/.config/gh"})):
        if (decide({"tool_name": tool, "tool_input": params}) or ("allow",))[0] != "deny":
            bad.append("not denied: %s %s" % (tool, params))
    if decide({"tool_name": "Read", "tool_input": {"file_path": "/home/x/work/README.md"}}) is not None:
        bad.append("blocked an ordinary Read")
    if decide({"tool_name": "Edit", "tool_input": {"file_path": "/home/x/.config/gh/hosts.yml"}}) is not None:
        pass  # Edit/Write are not this hook's concern; the permission system covers writes
    for line in bad:
        print("- " + line)
    print("%s: owner-token-guard, %d failures" % ("FAIL" if bad else "PASS", len(bad)))
    return 1 if bad else 0


def main():
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        # Not a hook event: refuse rather than let an unknown call through.
        print("owner-token-guard: unreadable hook input; refusing", file=sys.stderr)
        return 2
    verdict = decide(event if isinstance(event, dict) else {})
    if verdict:
        print(output(*verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
