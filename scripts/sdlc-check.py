#!/usr/bin/env python3
"""Checks the sdlc chain's artifacts (APS-51).

    python3 scripts/sdlc-check.py clarify <intent.md>
    python3 scripts/sdlc-check.py converge <plan.md> [--base <ref>] [--checks]
    python3 scripts/sdlc-check.py --self-test

`clarify` fails while the intent still has a `[NEEDS CLARIFICATION: …]` marker, or its `## Open questions` section
is missing or does not begin with `None`. Run it before the intent goes to `approved`, and again before the plan.
It also fails (APS-82):
  - when `## Coverage` lacks one of its six bullets (`- Who:`, `- Trigger:`, `- Main path:`, `- Branches and
    failures:`, `- Data and states:`, `- Limits:`), gives one twice, or leaves one empty (blank, a bare `N/A`, `TBD`
    or `?`, with or without a full stop, also as sub-bullets; `N/A: <reason>` is content);
  - when the intent has no `Flow:` line or more than one; when `Flow: not needed:` gives no reason or names a flow
    file; when a named `*.flow.json` is not `<intent stem>.<name>.flow.json` beside the intent (no slash or backslash;
    a file belongs to the longest intent stem it extends, so `x.trial.a.flow.json` is `x.trial.md`'s, not `x.md`'s),
    is a link, or is missing; when a flow file of the intent is not named;
  - for each named flow: when its `.flow.html` is missing; when the flow tool (`ambysto-graph` on PATH, else
    `~/.claude/skills/graph/scripts/graph.py`) fails `validate`; when `render` with no flags gives other bytes than
    the `.flow.html` (CRLF read as LF); when a call takes over 60 s. With no flow tool, it says the flows were not
    checked and does not fail for that.
`converge` also traces (APS-82): when the plan's intent has `## Coverage`, every top-level numbered Outcome item must be
named by a Proof item, as `(O1, O3)` on the item's line, and a Proof item must not name an Outcome item that does not
exist. An intent without `## Coverage` (written before this) is reported and passes.

`converge` compares a plan with its branch: the paths changed since the merge base with `--base` (default
`origin/main`, else `main`), the working tree and untracked files included. It also reports `floor:` notes when the
diff or an untracked file adds a linter or type-checker suppression (`noqa`, `type: ignore`, `@ts-ignore`,
`@ts-expect-error`, `eslint-disable`), adds a test skip, deletes a test file, or removes more `assert` lines than it
adds, so the reviewer sees every bar-lowering change. Each gap is one line:
  - a changed path that no task allows (agent-guard's own rule: inside `allow`, outside `forbid`), other than the
    plan and its intent;
  - a task, not marked `not needed`, whose `allow` matches no changed path;
  - a Proof item with no Result item, or a Result item that does not begin with PASS, FAIL or `not run: <reason>`.
A plan with no `## Tasks` section has nothing to compare: it is reported and passes, so older plans stay valid.
With `--checks`, and only once nothing else is missing, it also runs each distinct `check:` command of the tasks that
are needed, through the shell at the work tree's top, in the plan's order (`SDLC_CHECK_TIMEOUT` seconds each, default
900; `SDLC_CHECKS_TOTAL` seconds for all of them, default 1500); a non-zero exit, a timeout (the check's whole process
group is killed) or no time left is the gap `check failed: …`. The one-prompt loop's Stop hook judges with it, so
"done" means the checks passed just now, not that someone wrote PASS. A heavy check carries its own memory cap.

The formats are in the sdlc skill (`skills/sdlc/SKILL.md`). `dispatch.py --task` reads tasks with `parse_tasks`
here. Exit 0: pass; 1: a gap or a marker; 2: the file cannot be read as the format says (nothing is guessed).
It never edits a file; with `--checks` the plan's commands run as written. Standard library only.
"""
import importlib.util
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADING = re.compile(r"^### (T\d+) \((builder|main)(, parallel)?\) (\S.*)$")
TICKED = re.compile(r"`([^`]+)`")
RESULT = re.compile(r"^(PASS|FAIL|not run: \S)")
SUPPRESSION = re.compile(r"(?:#\s*(?:noqa|type:\s*ignore)\b|//\s*@ts-(?:ignore|expect-error)\b|(?:/\*|//)\s*eslint-disable\b)")
TEST_SKIP = re.compile(r"(?:@(?:unittest\.|pytest\.mark\.)?skip(?:If|Unless|if)?\b|\b(?:it|test|describe)\.skip\s*\(|\bpytest\.skip\s*\()")
ASSERT_LINE = re.compile(r"^\s*(?:assert\b|self\.assert\w+\s*\(|expect\s*\()")
TEST_FILE = re.compile(r"(?:^|/)(?:test_[^/]+\.py|[^/]+_test\.(?:py|go)|[^/]+\.(?:test|spec)\.[jt]sx?)$")
COVERAGE = ("Who", "Trigger", "Main path", "Branches and failures", "Data and states", "Limits")
EMPTY_ROW = {"", "n/a", "tbd", "?"}
FLOW_TIMEOUT = 60


class Malformed(Exception):
    pass


def sections(text):
    """`## ` heading line → its lines (up to the next `## `), in order; fenced code blocks are not headings."""
    out, name, fenced = [], None, False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            name = line[3:].strip()
            out.append((name, []))
        elif name is not None:
            out[-1][1].append(line)
    return out


def section(text, name):
    """The lines of `## <name>`, also when the heading goes on (`## Result (2026-11-10)`); None if absent."""
    found = [lines for title, lines in sections(text) if title == name or title.startswith(name + " ")]
    if len(found) > 1:
        raise Malformed(f"more than one `## {name}` section")
    return found[0] if found else None


def ticked_only(value, what):
    globs = TICKED.findall(value)
    if not globs or TICKED.sub("", value).strip():
        raise Malformed(f"{what}: write each glob in backticks, separated by spaces, and nothing else: {value!r}")
    return globs


def parse_tasks(text):
    """The plan's tasks as dicts (id, who, parallel, title, allow, forbid, checks, not_needed), or None without a
    `## Tasks` section. A line the format does not know is refused, never skipped."""
    lines = section(text, "Tasks")
    if lines is None:
        return None
    tasks, task = [], None
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("###"):
            m = HEADING.match(line)
            if not m:
                raise Malformed(f"task heading not in the form `### T<n> (builder|main[, parallel]) <title>`: {line!r}")
            task = {"id": m[1], "who": m[2], "parallel": bool(m[3]), "title": m[4].strip(), "allow": [],
                    "forbid": [], "checks": [], "not_needed": None}
            tasks.append(task)
            continue
        if task is None:
            continue  # prose before the first task
        m = re.match(r"^- (allow|forbid|check|not needed): (.*\S)\s*$", line)
        if not m:
            raise Malformed(f"{task['id']}: a line the format does not know: {line!r}")
        key, value = m[1], m[2]
        if key in ("allow", "forbid"):
            task[key] += ticked_only(value, f"{task['id']} {key}")
        elif key == "check":
            c = re.fullmatch(r"`(.+)`", value)
            if not c or not c[1].strip() or re.search(r"`\s+`", c[1]):
                raise Malformed(f"{task['id']}: one command per `check`, in backticks: {value!r}")
            task["checks"].append(c[1])
        else:
            task["not_needed"] = value
    ids = [t["id"] for t in tasks]
    for t in tasks:
        if ids.count(t["id"]) > 1:
            raise Malformed(f"task id {t['id']} is used twice")
        if not t["allow"]:
            raise Malformed(f"{t['id']} has no `allow`")
        if not t["checks"]:
            raise Malformed(f"{t['id']} has no `check`")
    if not tasks:
        raise Malformed("the `## Tasks` section has no task")
    return tasks


def numbered(lines, what):
    items = {}
    for m in (re.match(r"^(\d+)\. (.*)$", l) for l in lines or []):
        if m and int(m[1]) in items:
            raise Malformed(f"`## {what}` item {m[1]} is numbered twice")
        if m:
            items[int(m[1])] = m[2]
    return items


def clarify(text):
    """Markers outside code (a backticked span or a fenced block names the marker, it does not use it)."""
    gaps, fenced = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and "[NEEDS CLARIFICATION" in re.sub(r"`[^`]*`", "", line):
            gaps.append(f"line {n}: {line.strip()}")
    lines = section(text, "Open questions")
    if lines is None:
        gaps.append("no `## Open questions` section")
    else:
        first = next((l.strip() for l in lines if l.strip()), "")
        if not re.match(r"None\b", first):
            gaps.append(f"`## Open questions` does not begin with `None`: {first[:80]!r}")
        elif any(re.match(r"\s*(?:[-*]|\d+\.) ", l) for l in lines):
            gaps.append("`## Open questions` begins with `None` but lists questions under it")
    return gaps


def coverage(text):
    """Gaps in `## Coverage`: each of the six labels once, as `- <Label>: <text>`, with text or `N/A: <reason>`."""
    lines = section(text, "Coverage")
    if lines is None:
        return ["no `## Coverage` section"]
    rows, gaps, current, fenced = {}, [], None, False
    for line in lines:
        if line.startswith("```"):
            fenced, current = not fenced, None
            continue
        m = None if fenced else re.match(r"^- ([^:`]+):(.*)$", line)
        if m:
            current = m[1].strip()
            if current in rows:
                gaps.append(f"`## Coverage` gives `{current}` twice")
            rows[current] = [m[2]]
        elif current and not fenced and line[:1] in (" ", "\t"):
            rows[current].append(line)
        elif line.strip():
            current = None
    for label in COVERAGE:
        if label not in rows:
            gaps.append(f"`## Coverage` has no `- {label}:` bullet")
        elif empty_row(rows[label]):
            gaps.append(f"`## Coverage` `{label}` is empty (write it, or `N/A: <reason>`)")
    return gaps


def empty_row(lines):
    """True when a Coverage bullet says nothing: each of its lines (sub-bullets too) blank, `N/A`, `TBD` or `?`, with
    or without a full stop; `N/A: <reason>` is content."""
    items = [re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", l).strip() for l in lines]
    items = [re.sub(r"^N/A\s*:", "", i, flags=re.I).strip().rstrip(".").strip().lower() for i in items]
    return all(i in EMPTY_ROW for i in items)


def intent_stems(folder):
    """The stems of the intents in a folder (`x.md`, not `x.plan.md`), longest first."""
    try:
        names = [q.name[:-3] for q in folder.iterdir() if q.name.endswith(".md") and not q.name.endswith(".plan.md")]
    except OSError:
        names = []
    return sorted(names, key=len, reverse=True)


def flow_owner(name, stems):
    """The intent stem a `<stem>.<name>.flow.json|html` file belongs to: the longest stem it extends, or None."""
    return next((st for st in stems if name.startswith(st + ".") and re.fullmatch(
        re.escape(st) + r"\.[^/\\.][^/\\]*\.flow\.(?:json|html)", name)), None)


def flow_line(path, text):
    """(named flow files, gaps) from the intent's one `Flow:` line, checked against the flow files beside it."""
    found, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("Flow: "):
            found.append(line[len("Flow: "):].strip())
    if not found:
        return [], ["no `Flow:` line (name the flow files, or write `Flow: not needed: <reason>`)"]
    if len(found) > 1:
        return [], [f"{len(found)} `Flow:` lines; write one"]
    value, stem, gaps = found[0], path.name[:-3] if path.name.endswith(".md") else path.stem, []
    stems = intent_stems(path.parent)
    stems = stems if stem in stems else sorted(stems + [stem], key=len, reverse=True)
    listed = [n for n in TICKED.findall(value) if n.endswith(".flow.json")]
    if value.startswith("not needed"):
        named = []
        if not re.match(r"not needed:\s*\S", value):
            gaps.append("`Flow: not needed` gives no reason")
        for n in listed:
            gaps.append(f"`Flow: not needed` names `{n}`: name the flows without `not needed`, or delete the file")
    else:
        named = list(dict.fromkeys(listed))  # a name given twice is checked once
        if not named:
            gaps.append("the `Flow:` line names no `*.flow.json` file and does not say `not needed: <reason>`")
        for n in list(named):
            if flow_owner(n, stems) != stem:  # also refuses a slash or backslash: a name never leaves the folder
                gaps.append(f"flow `{n}`: name it `{stem}.<name>.flow.json`, beside the intent")
                named.remove(n)
            elif (path.parent / n).is_symlink() or (path.parent / (n[: -len(".json")] + ".html")).is_symlink():
                gaps.append(f"flow `{n}` or its `.flow.html` is a link; commit the file itself")
                named.remove(n)
            elif not (path.parent / n).is_file():
                gaps.append(f"flow `{n}` is named but missing")
                named.remove(n)
    for q in sorted(path.parent.iterdir()):
        if q.name.endswith(".flow.json") and flow_owner(q.name, stems) == stem and \
                (value.startswith("not needed") or q.name not in listed):
            gaps.append(f"flow `{q.name}` is not named on the `Flow:` line")
    return named, gaps


def flow_tool():
    """The flow tool as a command list: `ambysto-graph` on PATH, else the installed `graph` skill; None without one."""
    exe = shutil.which("ambysto-graph")
    if exe:
        return [exe]
    script = Path.home() / ".claude" / "skills" / "graph" / "scripts" / "graph.py"
    return [sys.executable, str(script)] if script.is_file() else None


def check_flows(folder, named, tool, timeout=FLOW_TIMEOUT):
    """(notes, gaps): each named flow validates, and its `.flow.html` equals a fresh render with no flags."""
    notes, gaps = [], []
    for name in named:
        html = folder / (name[: -len(".json")] + ".html")
        if not html.is_file():
            gaps.append(f"flow `{name}`: `{html.name}` is missing")
        if tool is None:
            continue
        shown = " ".join(shlex.quote(Path(tool[0]).name if len(tool) == 1 else t) for t in tool)
        again = f"render it again: `{shown} render {name} -o {html.name}`"
        try:
            v = subprocess.run([*tool, "validate", str(folder / name)], capture_output=True, text=True, timeout=timeout)
            if v.returncode != 0:
                said = " | ".join(l.strip() for l in (v.stdout + v.stderr).splitlines() if l.strip())[:300]
                gaps.append(f"flow `{name}`: validate failed (exit {v.returncode}): {said}")
                continue
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "fresh.html"
                r = subprocess.run([*tool, "render", str(folder / name), "-o", str(out)], capture_output=True, text=True,
                                   timeout=timeout)
                if r.returncode != 0 or not out.is_file():
                    said = " | ".join(l.strip() for l in (r.stdout + r.stderr).splitlines() if l.strip())[:300]
                    gaps.append(f"flow `{name}`: render failed (exit {r.returncode}): {said}")
                elif html.is_file() and html.read_bytes().replace(b"\r\n", b"\n") != out.read_bytes().replace(b"\r\n", b"\n"):
                    gaps.append(f"flow `{name}`: `{html.name}` is not a fresh render of it; {again}")
                elif html.is_file():
                    notes.append(f"flow `{name}`: valid, and `{html.name}` is its fresh render")
        except subprocess.TimeoutExpired:
            gaps.append(f"flow `{name}`: the flow tool took over {timeout} s")
    if named and tool is None:
        notes.append("flows not checked: no flow tool installed (`ambysto-graph`, or the `graph` skill)")
    return notes, gaps


def clarify_intent(path, tool=None, timeout=FLOW_TIMEOUT):
    """(notes, gaps) for an intent file: the open points, `## Coverage`, the `Flow:` line and its flows."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    named, flow_gaps = flow_line(path.resolve(), text)
    notes, checked = check_flows(path.resolve().parent, named, tool, timeout)
    return notes, clarify(text) + coverage(text) + flow_gaps + checked


def trace(plan_path, proof):
    """(notes, gaps): with an intent that has `## Coverage`, every top-level Outcome item is named by a Proof item."""
    if not plan_path.name.endswith(".plan.md"):
        return [f"{plan_path.name}: no intent beside it; Outcome items not traced"], []
    intent = plan_path.with_name(plan_path.name[: -len(".plan.md")] + ".md")
    if not intent.is_file():
        return [f"{intent.name}: no such intent; Outcome items not traced"], []
    text = intent.read_text(encoding="utf-8")
    if section(text, "Coverage") is None:
        return [f"{intent.name}: no `## Coverage` (written before it); Outcome items not traced"], []
    outcome = numbered(section(text, "Outcome"), "Outcome")
    if not outcome:
        return [], [f"{intent.name} has `## Coverage` but no numbered `## Outcome` items"]
    named = {}
    for n in sorted(proof):
        for group in re.findall(r"\((O\d+(?:\s*,\s*O\d+)*)\)", proof[n]):
            for o in re.findall(r"O(\d+)", group):
                named.setdefault(int(o), n)
    gaps = [f"outcome {o} is named by no Proof item (write `(O{o})` on the Proof items that prove it)"
            for o in sorted(set(outcome) - set(named))]
    gaps += [f"proof {named[o]} names O{o}, which {intent.name} has no Outcome item for" for o in sorted(set(named) - set(outcome))]
    return [], gaps


def guard():
    spec = importlib.util.spec_from_file_location("agent_guard", ROOT / "hooks" / "agent-guard.py")
    module = importlib.util.module_from_spec(spec)
    dont = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = dont
    return module


def git(top, *args):
    out = subprocess.run(["git", "-C", str(top), *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise Malformed(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


def changed_paths(top, base):
    if base is None:
        refs = [r for r in ("origin/main", "main")
                if subprocess.run(["git", "-C", str(top), "rev-parse", "-q", "--verify", r + "^{commit}"],
                                  capture_output=True).returncode == 0]
        if not refs:
            raise Malformed("no origin/main or main to compare with; pass --base")
        base = refs[0]
    mb = git(top, "merge-base", base, "HEAD").strip()
    paths = set(git(top, "-c", "core.quotePath=false", "diff", "--name-only", "--no-renames", mb).splitlines())
    paths |= set(git(top, "-c", "core.quotePath=false", "ls-files", "--others", "--exclude-standard").splitlines())
    return base, sorted(p for p in paths if p)


def floor_notes(top, base, paths, own):
    """Floor notes for the reviewer: added suppressions, added test skips, deleted test files, and net removed assertions."""
    notes, added_asserts, removed_asserts = [], {}, {}
    mb = git(top, "merge-base", base, "HEAD").strip()
    untracked = sorted(p for p in set(git(top, "-c", "core.quotePath=false", "ls-files", "--others", "--exclude-standard").splitlines()) if p)
    for p in paths:
        if p in own:
            continue
        if TEST_FILE.search(p) and not (top / p).exists():
            notes.append(f"floor: {p}: test file deleted")
    diff = git(top, "-c", "core.quotePath=false", "diff", "--no-renames", "--unified=0", mb)
    cur = None
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            cur = raw[6:]
        elif raw.startswith("+++ /dev/null"):
            pass
        elif raw.startswith("--- a/"):
            cur = raw[6:]
        elif cur and cur not in own and not cur.endswith(".md"):
            if raw.startswith("+") and not raw.startswith("+++"):
                line = raw[1:]
                if "floor:" not in line:
                    m = SUPPRESSION.search(line)
                    if m:
                        notes.append(f"floor: {cur}: added suppression `{m[0].strip()}`")
                    m = TEST_SKIP.search(line)
                    if m:
                        notes.append(f"floor: {cur}: added test skip `{m[0].strip()}`")
                if ASSERT_LINE.search(line):
                    added_asserts[cur] = added_asserts.get(cur, 0) + 1
            elif raw.startswith("-") and not raw.startswith("---"):
                if ASSERT_LINE.search(raw[1:]):
                    removed_asserts[cur] = removed_asserts.get(cur, 0) + 1
    for p in untracked:
        if p in own or p.endswith(".md") or not (top / p).is_file():
            continue
        for line in (top / p).read_text(encoding="utf-8", errors="replace").splitlines():
            if "floor:" in line:
                continue
            m = SUPPRESSION.search(line)
            if m:
                notes.append(f"floor: {p}: added suppression `{m[0].strip()}`")
            m = TEST_SKIP.search(line)
            if m:
                notes.append(f"floor: {p}: added test skip `{m[0].strip()}`")
            if ASSERT_LINE.search(line):
                added_asserts[p] = added_asserts.get(p, 0) + 1
    for p in sorted(removed_asserts):
        rem, add = removed_asserts[p], added_asserts.get(p, 0)
        if rem > add:
            notes.append(f"floor: {p}: removed {rem - add} assertion(s) ({rem} removed, {add} added)")
    return notes


def run_checks(tasks, top):
    """(notes, gaps) from running each distinct check of the live tasks once, in the plan's order."""
    def seconds(name, default):
        try:
            return max(1, int(os.environ.get(name, default)))
        except ValueError:
            return default

    limit, total = seconds("SDLC_CHECK_TIMEOUT", 900), seconds("SDLC_CHECKS_TOTAL", 1500)
    started = time.monotonic()
    notes, gaps, seen = [], [], {}
    for t in tasks:
        if t["not_needed"]:
            continue
        for cmd in t["checks"]:
            if cmd in seen:
                continue
            seen[cmd] = t["id"]
            left = int(total - (time.monotonic() - started))
            if left < 1:
                gaps.append(f"check failed: {t['id']} `{cmd}` not run: the checks' total time ({total} s) is used up")
                continue
            mine = min(limit, left)
            # its own process group, so a timeout kills what the command started too, not only the shell
            proc = subprocess.Popen(cmd, shell=True, cwd=top, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                output = proc.communicate(timeout=mine)[0]
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    proc.kill()
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:  # something left the group and holds the output: do not wait for it
                    pass
                gaps.append(f"check failed: {t['id']} `{cmd}` took over {mine} s")
                continue
            if proc.returncode != 0:
                tail = " ".join(output.split())[-300:]
                gaps.append(f"check failed: {t['id']} `{cmd}` (exit {proc.returncode}): {tail}")
            else:
                notes.append(f"check passed: {t['id']} `{cmd}`")
    return notes, gaps


def converge(plan_path, base=None, checks=False):
    """(notes, gaps) for a plan file in a git work tree."""
    plan_path = Path(plan_path).resolve()
    text = plan_path.read_text(encoding="utf-8")
    tasks = parse_tasks(text)
    if tasks is None:
        return [f"{plan_path.name}: no `## Tasks` section; nothing to compare"], []
    top = Path(git(plan_path.parent, "rev-parse", "--show-toplevel").strip()).resolve()
    base, paths = changed_paths(top, base)
    own = {plan_path.relative_to(top).as_posix()}
    if plan_path.name.endswith(".plan.md"):
        own.add(plan_path.relative_to(top).as_posix()[: -len(".plan.md")] + ".md")
    stem = plan_path.name[: -len(".plan.md")] if plan_path.name.endswith(".plan.md") else None
    folder, stems = plan_path.parent.relative_to(top).as_posix(), intent_stems(plan_path.parent)
    stems = stems if stem is None or stem in stems else sorted(stems + [stem], key=len, reverse=True)
    flow_of_intent = lambda q: stem is not None and q.rpartition("/")[0] == ("" if folder == "." else folder) and \
        flow_owner(q.rpartition("/")[2], stems) == stem
    in_contract = guard().in_contract
    live = [t for t in tasks if not t["not_needed"]]
    contracts = {t["id"]: {"allow": t["allow"], "forbid": t["forbid"]} for t in live}
    notes, gaps = [f"{len(paths)} changed path(s) since the merge base with {base}"], []
    for p in paths:
        if p in own or flow_of_intent(p):
            continue
        if not any(in_contract(p, c) for c in contracts.values()):
            gaps.append(f"outside every task: {p}")
    for t in tasks:
        if t["not_needed"]:
            notes.append(f"{t['id']} not needed: {t['not_needed']}")
        elif not any(in_contract(p, contracts[t["id"]]) for p in paths):
            gaps.append(f"{t['id']} ({t['title']}) changed none of its files")
    notes += floor_notes(top, base, paths, own)
    proof = numbered(section(text, "Proof"), "Proof")
    result = numbered(section(text, "Result"), "Result")
    if not proof:
        gaps.append("no numbered `## Proof` items")
    for n in sorted(proof):
        if n not in result:
            gaps.append(f"proof {n} has no result")
        elif not RESULT.match(result[n]):
            gaps.append(f"result {n} does not begin with PASS, FAIL or `not run: <reason>`: {result[n][:60]!r}")
        elif result[n].startswith("FAIL"):
            notes.append(f"proof {n} recorded FAIL")
    for n in sorted(set(result) - set(proof)):
        gaps.append(f"result {n} has no proof item")
    more_notes, more_gaps = trace(plan_path, proof)
    notes += more_notes
    gaps += more_gaps
    if checks and not gaps:  # only once nothing else is missing: the checks are the last, and the slow, step
        more_notes, gaps = run_checks(tasks, top)
        notes += more_notes
    return notes, gaps


def self_test():
    failures = []

    def expect(name, got, want):
        if got != want:
            failures.append(f"{name}: got {got!r}, want {want!r}")

    def refused(name, fn):
        try:
            fn()
            failures.append(f"{name}: not refused")
        except Malformed:
            pass

    expect("clarify clean", clarify("# I\n\n## Open questions\n\nNone.\n"), [])
    expect("clarify marker", len(clarify("Do [NEEDS CLARIFICATION: which?]\n## Open questions\nNone.\n")), 1)
    expect("clarify open", len(clarify("## Open questions\n\n1. Which account?\n")), 1)
    expect("clarify missing", clarify("# I\n"), ["no `## Open questions` section"])
    expect("clarify None then a list", len(clarify("## Open questions\nNone, but:\n- which account?\n")), 1)
    expect("clarify Nonetheless", len(clarify("## Open questions\nNonetheless, one thing.\n")), 1)
    expect("clarify None with a reason", clarify("## Open questions\nNone. Decided by the owner on 2026-11-10.\n"), [])
    expect("clarify fenced heading", len(clarify("```\n## Open questions\nNone\n```\n")), 1)
    expect("clarify named in code", clarify("Mark it as `[NEEDS CLARIFICATION: q]`.\n```\n[NEEDS CLARIFICATION: x]\n```\n"
                                            "## Open questions\nNone.\n"), [])

    task = "### T1 (builder, parallel) Build a\n- allow: `src/**` `README.md`\n- forbid: `src/x.py`\n- check: `make test`\n"
    expect("parse", parse_tasks(f"## Tasks\n\n{task}\n## Steps\n"),
           [{"id": "T1", "who": "builder", "parallel": True, "title": "Build a", "allow": ["src/**", "README.md"],
             "forbid": ["src/x.py"], "checks": ["make test"], "not_needed": None}])
    expect("no tasks", parse_tasks("## Steps\n1. x\n"), None)
    expect("check keeps inner text", parse_tasks("## Tasks\n### T2 (main) M\n- allow: `a`\n- check: `sh -c 'x | y'`\n")[0]["checks"],
           ["sh -c 'x | y'"])
    refused("unknown bullet", lambda: parse_tasks(f"## Tasks\n{task}- files: `x`\n"))
    refused("bad heading", lambda: parse_tasks("## Tasks\n### Task one\n- allow: `a`\n- check: `x`\n"))
    refused("untick glob", lambda: parse_tasks("## Tasks\n### T1 (main) M\n- allow: src/**\n- check: `x`\n"))
    refused("text beside globs", lambda: parse_tasks("## Tasks\n### T1 (main) M\n- allow: `a` and `b`\n- check: `x`\n"))
    refused("no allow", lambda: parse_tasks("## Tasks\n### T1 (main) M\n- check: `x`\n"))
    refused("no check", lambda: parse_tasks("## Tasks\n### T1 (main) M\n- allow: `a`\n"))
    refused("duplicate id", lambda: parse_tasks(f"## Tasks\n{task}{task}"))
    refused("empty section", lambda: parse_tasks("## Tasks\nprose only\n"))
    refused("two sections", lambda: parse_tasks(f"## Tasks\n{task}## Tasks\n{task}"))
    refused("two commands in one check", lambda: parse_tasks("## Tasks\n### T1 (main) M\n- allow: `a`\n- check: `make test` `make lint`\n"))
    expect("Tasks heading that goes on", parse_tasks(f"## Tasks (dispatch)\n{task}")[0]["id"], "T1")
    refused("a proof number twice", lambda: numbered(["1. a", "1. b"], "Proof"))

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        fake = d / "fake-flow-tool.py"
        fake.write_text("import sys, time\n"
                        "text = open(sys.argv[2]).read()\n"
                        "if 'SLOW' in text: time.sleep(5)\n"
                        "if sys.argv[1] == 'validate':\n"
                        "    if 'BAD' in text: print('error decision-one-branch nodes[1]: one exit'); sys.exit(1)\n"
                        "    print('ok'); sys.exit(0)\n"
                        "if 'NORENDER' in text: print('render: layout error'); sys.exit(2)\n"
                        "open(sys.argv[4], 'w').write('HTML ' + text)\n")
        tool = [sys.executable, str(fake)]
        cov = ("## Coverage\n- Who: me\n- Trigger: a click\n- Main path: a, b\n- Branches and failures:\n  - none found: a note\n"
               "- Data and states: N/A: no data\n- Limits: 1 s\n")
        head = "# I\n## Outcome\n1. x\n" + cov + "## Open questions\nNone.\n"
        intent = d / "2026-01-01-x.md"

        def run_clarify(flow, files=None, timeout=FLOW_TIMEOUT, tool=tool, text=None):
            for f in d.glob("2026-01-01-x.*"):
                f.unlink()
            for name, body in (files or {}).items():
                (d / name).write_text(body)
            intent.write_text((head if text is None else text) + flow)
            return clarify_intent(intent, tool, timeout)

        expect("intent clean, no flow needed", run_clarify("Flow: not needed: one linear step\n"), ([], []))
        expect("coverage missing", run_clarify("Flow: not needed: x\n", text="## Open questions\nNone.\n")[1],
               ["no `## Coverage` section"])
        expect("coverage label missing", run_clarify("Flow: not needed: x\n", text=head.replace("- Limits: 1 s\n", ""))[1],
               ["`## Coverage` has no `- Limits:` bullet"])
        expect("coverage label twice", run_clarify("Flow: not needed: x\n", text=head.replace("- Limits: 1 s\n", "- Limits: 1 s\n- Who: you\n"))[1],
               ["`## Coverage` gives `Who` twice"])
        for empty in ("", " N/A", " TBD", " ?", " N/A:", " n/a: tbd"):
            expect(f"coverage empty {empty!r}", run_clarify("Flow: not needed: x\n", text=head.replace("- Trigger: a click", "- Trigger:" + empty))[1],
                   ["`## Coverage` `Trigger` is empty (write it, or `N/A: <reason>`)"])
        for empty in (" N/A.", " TBD.", "\n  - TBD", "\n  - ?\n  - N/A"):
            expect(f"coverage empty {empty!r}", run_clarify("Flow: not needed: x\n", text=head.replace("- Limits: 1 s", "- Limits:" + empty))[1],
                   ["`## Coverage` `Limits` is empty (write it, or `N/A: <reason>`)"])
        expect("coverage: a sub-bullet is content", run_clarify("Flow: not needed: x\n", text=head.replace("- Limits: 1 s", "- Limits:\n  - 1 s"))[1], [])
        expect("coverage: a bullet in a fence does not count",
               run_clarify("Flow: not needed: x\n", text=head.replace("- Limits: 1 s\n", "```\n- Limits: 1 s\n```\n"))[1],
               ["`## Coverage` has no `- Limits:` bullet"])
        expect("coverage: an unindented line ends a bullet",
               run_clarify("Flow: not needed: x\n", text=head.replace("- Limits: 1 s\n", "- Limits:\nsome prose\n"))[1],
               ["`## Coverage` `Limits` is empty (write it, or `N/A: <reason>`)"])
        expect("an approved intent without Coverage fails too", run_clarify("Flow: not needed: x\n",
               text="---\nstatus: shipped (PR #1)\n---\n## Open questions\nNone.\n")[1], ["no `## Coverage` section"])
        expect("no Flow line", run_clarify("")[1], ["no `Flow:` line (name the flow files, or write `Flow: not needed: <reason>`)"])
        expect("two Flow lines", run_clarify("Flow: not needed: a\nFlow: not needed: b\n")[1], ["2 `Flow:` lines; write one"])
        expect("Flow in a fence is not the line", run_clarify("```\nFlow: not needed: a\n```\n")[1][0][:15], "no `Flow:` line")
        expect("not needed without a reason", run_clarify("Flow: not needed\n")[1], ["`Flow: not needed` gives no reason"])
        expect("no flow named", run_clarify("Flow: see below\n")[1],
               ["the `Flow:` line names no `*.flow.json` file and does not say `not needed: <reason>`"])
        expect("a name outside the folder", run_clarify("Flow: `../2026-01-01-x.a.flow.json`\n")[1][0],
               "flow `../2026-01-01-x.a.flow.json`: name it `2026-01-01-x.<name>.flow.json`, beside the intent")
        expect("a name with a slash under the stem", run_clarify("Flow: `2026-01-01-x.sub/a.flow.json`\n")[1],
               ["flow `2026-01-01-x.sub/a.flow.json`: name it `2026-01-01-x.<name>.flow.json`, beside the intent"])
        expect("a name with a backslash", run_clarify("Flow: `2026-01-01-x.sub\\a.flow.json`\n")[1],
               ["flow `2026-01-01-x.sub\\a.flow.json`: name it `2026-01-01-x.<name>.flow.json`, beside the intent"])
        for bad in ("2026-01-01-x..flow.json", "2026-01-01-x..a.flow.json", "2026-01-01-xyz.a.flow.json", "2026-01-01-y.long.a.flow.json"):
            expect(f"a name not `<stem>.<name>`: {bad}", run_clarify(f"Flow: `{bad}`\n", {bad: "{}"})[1],
                   [f"flow `{bad}`: name it `2026-01-01-x.<name>.flow.json`, beside the intent"])
        expect("not needed that names a flow", run_clarify("Flow: not needed: `2026-01-01-x.a.flow.json` is a sketch\n",
                                                           {"2026-01-01-x.a.flow.json": "BAD"})[1],
               ["`Flow: not needed` names `2026-01-01-x.a.flow.json`: name the flows without `not needed`, or delete the file",
                "flow `2026-01-01-x.a.flow.json` is not named on the `Flow:` line"])
        expect("another intent's name", run_clarify("Flow: `other.a.flow.json`\n")[1][0][:26], "flow `other.a.flow.json`: ")
        expect("a named flow missing", run_clarify("Flow: `2026-01-01-x.a.flow.json`\n")[1],
               ["flow `2026-01-01-x.a.flow.json` is named but missing"])
        good = {"2026-01-01-x.a.flow.json": "{}", "2026-01-01-x.a.flow.html": "HTML {}"}
        notes, gaps = run_clarify("Flow: `2026-01-01-x.a.flow.json` (a user flow)\n", good)
        expect("a flow checked", (notes, gaps), (["flow `2026-01-01-x.a.flow.json`: valid, and `2026-01-01-x.a.flow.html` is its fresh render"], []))
        expect("a flow not named", run_clarify("Flow: not needed: x\n", good)[1],
               ["flow `2026-01-01-x.a.flow.json` is not named on the `Flow:` line"])
        expect("a validate error", run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {**good, "2026-01-01-x.a.flow.json": "BAD"})[1],
               ["flow `2026-01-01-x.a.flow.json`: validate failed (exit 1): error decision-one-branch nodes[1]: one exit"])
        expect("the HTML missing", run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {"2026-01-01-x.a.flow.json": "{}"})[1],
               ["flow `2026-01-01-x.a.flow.json`: `2026-01-01-x.a.flow.html` is missing"])
        stale = run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {**good, "2026-01-01-x.a.flow.html": "HTML old"})[1]
        expect("the HTML stale", [g.split(";")[0] for g in stale],
               ["flow `2026-01-01-x.a.flow.json`: `2026-01-01-x.a.flow.html` is not a fresh render of it"])
        expect("a render failure", run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {**good, "2026-01-01-x.a.flow.json": "NORENDER"})[1],
               ["flow `2026-01-01-x.a.flow.json`: render failed (exit 2): render: layout error"])
        expect("CRLF in the checked-out HTML is not stale",
               run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {"2026-01-01-x.a.flow.json": "{\n}", "2026-01-01-x.a.flow.html": "HTML {\r\n}"})[1], [])
        run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {"2026-01-01-x.real.json": "{}", "2026-01-01-x.a.flow.html": "HTML {}"})
        (d / "2026-01-01-x.a.flow.json").symlink_to(d / "2026-01-01-x.real.json")
        expect("a flow that is a link", clarify_intent(intent, tool, FLOW_TIMEOUT)[1],
               ["flow `2026-01-01-x.a.flow.json` or its `.flow.html` is a link; commit the file itself"])
        run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {"2026-01-01-x.a.flow.json": "{}", "2026-01-01-x.real.html": "HTML {}"})
        (d / "2026-01-01-x.a.flow.html").symlink_to(d / "2026-01-01-x.real.html")
        expect("a flow whose HTML is a link", clarify_intent(intent, tool, FLOW_TIMEOUT)[1],
               ["flow `2026-01-01-x.a.flow.json` or its `.flow.html` is a link; commit the file itself"])
        run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {**good, "2026-01-01-x.real.html": "x"})
        (d / "2026-01-01-x.a.html").symlink_to(d / "2026-01-01-x.real.html")
        expect("an unrelated .html link is not the flow's", clarify_intent(intent, tool, FLOW_TIMEOUT)[1], [])
        expect("a flow named twice is checked once",
               run_clarify("Flow: `2026-01-01-x.a.flow.json` and again `2026-01-01-x.a.flow.json`\n", good),
               (["flow `2026-01-01-x.a.flow.json`: valid, and `2026-01-01-x.a.flow.html` is its fresh render"], []))
        expect("a plan file is not an intent that owns flows",
               run_clarify("Flow: `2026-01-01-x.plan.a.flow.json`\n", {"2026-01-01-x.plan.md": "p\n",
                           "2026-01-01-x.plan.a.flow.json": "{}", "2026-01-01-x.plan.a.flow.html": "HTML {}"})[1], [])
        run_clarify("Flow: not needed: x\n", {"2026-01-01-x.trial.b.flow.json": "{}", "2026-01-01-x.trial.b.flow.html": "HTML {}"})
        longer = d / "2026-01-01-x.trial.md"
        longer.write_text(head + "Flow: `2026-01-01-x.trial.b.flow.json`\n")
        expect("a longer intent's flows belong to it, not to the shorter one", clarify_intent(intent, tool, FLOW_TIMEOUT), ([], []))
        expect("and the longer intent names them", clarify_intent(longer, tool, FLOW_TIMEOUT)[1], [])
        longer.unlink()
        expect("a slow tool", run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", {**good, "2026-01-01-x.a.flow.json": "SLOW"}, timeout=1)[1],
               ["flow `2026-01-01-x.a.flow.json`: the flow tool took over 1 s"])
        expect("no tool: a note, never a check", run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", good, tool=None),
               (["flows not checked: no flow tool installed (`ambysto-graph`, or the `graph` skill)"], []))
        saved = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE", "PATH")}
        os.environ.update(HOME=tmp, USERPROFILE=tmp, PATH=tmp)
        try:
            expect("no tool found on an empty PATH and HOME", flow_tool(), None)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        run_clarify("Flow: not needed: one step\n")
        out = subprocess.run([sys.executable, __file__, "clarify", str(intent)], capture_output=True, text=True)
        expect("cli clarify", (out.returncode, out.stdout.splitlines()[-1][:13]), (0, "PASS: clarify"))
        # the CLI finds the flow tool: `ambysto-graph` on PATH first, else the graph skill under HOME, else none
        run_clarify("Flow: `2026-01-01-x.a.flow.json`\n", good)
        empty, bin_dir, home = d / "empty", d / "bin", d / "home"
        empty.mkdir()
        bin_dir.mkdir()
        exe = bin_dir / ("ambysto-graph.bat" if os.name == "nt" else "ambysto-graph")
        exe.write_text(f'@"{sys.executable}" "{fake}" %*\n' if os.name == "nt" else f'#!/bin/sh\nexec "{sys.executable}" "{fake}" "$@"\n')
        exe.chmod(0o755)
        skill = home / ".claude" / "skills" / "graph" / "scripts"
        skill.mkdir(parents=True)
        shutil.copy(fake, skill / "graph.py")
        for case, path_dir, home_dir, want in (("ambysto-graph on PATH", bin_dir, empty, "flow `2026-01-01-x.a.flow.json`: valid"),
                                               ("the graph skill under HOME", empty, home, "flow `2026-01-01-x.a.flow.json`: valid"),
                                               ("neither", empty, empty, "flows not checked: no flow tool installed")):
            env = {**os.environ, "PATH": str(path_dir), "HOME": str(home_dir), "USERPROFILE": str(home_dir)}
            out = subprocess.run([sys.executable, __file__, "clarify", str(intent)], capture_output=True, text=True, env=env)
            expect(f"cli clarify finds the flow tool: {case}", (out.returncode, out.stdout.splitlines()[0][:len(want)]), (0, want))

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        run = lambda *a: subprocess.run(["git", "-C", tmp, *a], check=True, capture_output=True)
        run("init", "-q", "-b", "main")
        run("config", "user.email", "t@example.com")
        run("config", "user.name", "t")
        (repo / "intent").mkdir()
        (repo / "README.md").write_text("r\n")
        run("add", ".")
        run("commit", "-qm", "base")
        run("checkout", "-qb", "work")
        plan = repo / "intent" / "x.plan.md"
        tasks = ("## Tasks\n### T1 (builder) A\n- allow: `src/**`\n- forbid: `src/secret.py`\n- check: `t`\n"
                 "### T2 (main) B\n- allow: `docs/*.md`\n- check: `t`\n")
        proof = "## Proof\n1. tests\n2. build\n"
        plan.write_text(tasks + proof + "## Result\n1. PASS 3 tests\n2. not run: no build here\n")
        (repo / "intent" / "x.md").write_text("i\n")
        (repo / "src" / "deep").mkdir(parents=True)
        (repo / "src" / "deep" / "a.py").write_text("a\n")
        (repo / "docs").mkdir()
        (repo / "docs" / "n.md").write_text("n\n")
        run("add", ".")
        run("commit", "-qm", "work")
        notes, gaps = converge(plan)
        expect("converge clean", gaps, [])
        # tracing: an intent with `## Coverage` has every top-level Outcome item named by a Proof item
        intent_x = repo / "intent" / "x.md"
        intent_x.write_text("## Outcome\n1. one\n   1. a sub-item is not an Outcome item\n2. two\n## Coverage\n- Who: me\n")
        plan.write_text(tasks + "## Proof\n1. tests (O1)\n2. build (O2, O1)\n## Result\n1. PASS\n2. PASS\n")
        expect("trace clean", converge(plan)[1], [])
        plan.write_text(tasks + "## Proof\n1. tests (O1)\n2. build\n## Result\n1. PASS\n2. PASS\n")
        expect("trace an untraced outcome", converge(plan)[1],
               ["outcome 2 is named by no Proof item (write `(O2)` on the Proof items that prove it)"])
        plan.write_text(tasks + "## Proof\n1. tests (O1, O3)\n2. build (O2)\n## Result\n1. PASS\n2. PASS\n")
        expect("trace an unknown outcome", converge(plan)[1], ["proof 1 names O3, which x.md has no Outcome item for"])
        intent_x.write_text("## Outcome\nprose only\n## Coverage\n- Who: me\n")
        expect("trace an intent without numbered outcomes", converge(plan)[1],
               ["x.md has `## Coverage` but no numbered `## Outcome` items"])
        intent_x.write_text("i\n")
        plan.write_text(tasks + proof + "## Result\n1. PASS 3 tests\n2. not run: no build here\n")
        (repo / "intent" / "x.user.flow.json").write_text("{}\n")
        (repo / "intent" / "x.user.flow.html").write_text("h\n")
        (repo / "intent" / "y.user.flow.json").write_text("{}\n")
        (repo / "docs" / "x.user.flow.json").write_text("{}\n")
        (repo / "intent" / "x.trial.md").write_text("i\n")
        (repo / "intent" / "x.trial.b.flow.json").write_text("{}\n")
        expect("the intent's flows count as the plan's own, another intent's do not", sorted(converge(plan)[1]),
               ["outside every task: docs/x.user.flow.json", "outside every task: intent/x.trial.b.flow.json", "outside every task: intent/x.trial.md",
                "outside every task: intent/y.user.flow.json"])
        for f in ("x.user.flow.json", "x.user.flow.html", "y.user.flow.json", "x.trial.md", "x.trial.b.flow.json"):
            (repo / "intent" / f).unlink()
        (repo / "docs" / "x.user.flow.json").unlink()
        (repo / "src" / "secret.py").write_text("s\n")  # untracked, inside allow but forbidden
        (repo / "README.md").write_text("changed\n")    # uncommitted, outside every task
        expect("converge outside", sorted(converge(plan)[1]),
               ["outside every task: README.md", "outside every task: src/secret.py"])
        run("checkout", "-q", "--", "README.md")
        (repo / "src" / "secret.py").unlink()
        plan.write_text(tasks + "### T3 (main) C\n- allow: `web/**`\n- check: `t`\n" + proof + "## Result\n1. PASS\n")
        expect("converge untouched task and missing result", sorted(converge(plan)[1]),
               ["T3 (C) changed none of its files", "proof 2 has no result"])
        plan.write_text(tasks + "### T3 (main) C\n- allow: `web/**`\n- check: `t`\n- not needed: merged into T2\n"
                        + proof + "## Result (2026-11-10)\n1. FAIL 1 test\n2. done\n3. PASS\n")
        notes, gaps = converge(plan)
        expect("converge result words", sorted(gaps),
               ["result 2 does not begin with PASS, FAIL or `not run: <reason>`: 'done'", "result 3 has no proof item"])
        expect("converge notes", [n for n in notes if not n[0].isdigit()],
               ["T3 not needed: merged into T2", "proof 1 recorded FAIL",
                "x.md: no `## Coverage` (written before it); Outcome items not traced"])
        # --checks: the commands run only when nothing else is missing, once per distinct command, at the top
        ran = repo / "ran.log"
        ok = f"echo x >> {ran.name}"
        checked = (f"## Tasks\n### T1 (builder) A\n- allow: `src/**`\n- forbid: `src/secret.py`\n- check: `{ok}`\n"
                   f"### T2 (main) B\n- allow: `docs/*.md` `ran.log`\n- check: `{ok}`\n- check: `%s`\n")
        done = proof + "## Result\n1. PASS\n2. PASS\n"
        plan.write_text(checked % "true" + done)
        expect("no --checks runs nothing", (converge(plan)[1], ran.exists()), ([], False))
        notes, gaps = converge(plan, checks=True)
        expect("checks pass, each distinct command once", (gaps, ran.read_text(), sum(n.startswith("check passed") for n in notes)),
               ([], "x\n", 2))
        plan.write_text(checked % "echo broken; exit 3" + done)
        expect("a failing check is a gap", converge(plan, checks=True)[1], ["check failed: T2 `echo broken; exit 3` (exit 3): broken"])
        os.environ["SDLC_CHECK_TIMEOUT"] = "1"
        plan.write_text(checked % "sleep 5" + done)
        expect("a check over its time is a gap", converge(plan, checks=True)[1], ["check failed: T2 `sleep 5` took over 1 s"])
        left = repo / "left.log"
        plan.write_text(checked % f"(sleep 3; echo late > {left.name}) & sleep 5" + done)
        converge(plan, checks=True)
        time.sleep(3.5)
        expect("a timeout kills what the check started, not only the shell", left.exists(), False)
        del os.environ["SDLC_CHECK_TIMEOUT"]
        os.environ["SDLC_CHECKS_TOTAL"] = "2"
        plan.write_text(checked % "true" + f"### T3 (main) C\n- allow: `ran.log`\n- check: `sleep 2; true`\n### T4 (main) D\n- allow: `ran.log`\n- check: `echo never`\n" + done)
        gaps = converge(plan, checks=True)[1]
        expect("the checks share one total time", [g.split("`")[2].strip()[:22] for g in gaps], ["took over 1 s", "not run: the checks' t"])
        del os.environ["SDLC_CHECKS_TOTAL"]
        before = ran.read_text()
        plan.write_text(checked % "true" + proof + "## Result\n1. PASS\n")
        expect("another gap: the checks do not run", (converge(plan, checks=True)[1], ran.read_text()), (["proof 2 has no result"], before))
        plan.write_text(checked % "true" + f"### T3 (main) C\n- allow: `web/**`\n- check: `echo y >> {ran.name}`\n"
                        "- not needed: dropped\n" + done)
        ran.unlink()
        converge(plan, checks=True)
        expect("a task that is not needed runs no check", ran.read_text(), "x\n")
        ran.unlink()
        cli = lambda *a: subprocess.run([sys.executable, __file__, *a], capture_output=True, text=True, cwd=tmp)
        out = cli("converge", str(plan), "--checks", "--base", "main")
        expect("cli --checks with --base in either order", (out.returncode, out.stdout.splitlines()[-1][:14], ran.exists()), (0, "PASS: converge", True))
        expect("cli unknown option", cli("converge", str(plan), "--check").returncode, 2)
        expect("cli --base without a value", cli("converge", str(plan), "--base").returncode, 2)
        ran.unlink()
        old = repo / "intent" / "old.plan.md"
        old.write_text("## Steps\n1. x\n## Proof\n1. y\n")
        expect("converge old plan", converge(old)[1], [])
        old.unlink()
        # floor notes: added suppressions, added test skips, deleted test files, and net removed assertions
        run("checkout", "-q", "--", ".")
        run("checkout", "-qb", "floor-base", "main")
        (repo / "intent").mkdir(exist_ok=True)
        (repo / "src").mkdir(exist_ok=True)
        (repo / "src" / "test_mod.py").write_text("def test_one():\n    assert 1 == 1\n    assert 2 == 2\n")
        (repo / "src" / "test_gone.py").write_text("def test_two():\n    assert True\n")
        run("add", ".")
        run("commit", "-qm", "tests")
        run("checkout", "-qb", "floor-work")
        (repo / "src" / "test_gone.py").unlink()
        (repo / "src" / "test_mod.py").write_text("@pytest.mark." + "skip\ndef test_one():\n    x = 1  # " + "noqa\n")
        (repo / "src" / "untracked.ts").write_text("// @ts-" + "ignore\nit." + "skip('later', () => {})\n")
        plan.write_text("## Tasks\n### T1 (builder) A\n- allow: `src/**`\n- check: `true`\n## Proof\n1. ok\n## Result\n1. PASS\n")
        f_notes, f_gaps = converge(plan, base="floor-base")
        expect("floor notes do not create gaps", f_gaps, [])
        expect("floor notes catch deleted test, suppression, skip, and removed assertions",
               sorted(n for n in f_notes if n.startswith("floor: ")),
               ["floor: src/test_gone.py: removed 1 assertion(s) (1 removed, 0 added)",
                "floor: src/test_gone.py: test file deleted",
                "floor: src/test_mod.py: added suppression `# " + "noqa`",
                "floor: src/test_mod.py: added test skip `@pytest.mark." + "skip`",
                "floor: src/test_mod.py: removed 2 assertion(s) (2 removed, 0 added)",
                "floor: src/untracked.ts: added suppression `// @ts-" + "ignore`",
                "floor: src/untracked.ts: added test skip `it." + "skip(`"])
        (repo / "src" / "untracked.ts").unlink()
        (repo / "src" / "test_gone.py").write_text("def test_two():\n    assert True\n")
        (repo / "src" / "test_mod.py").write_text("def test_one():\n    assert 1 == 1\n    assert 2 == 2\n    assert 3 == 3\n")
        expect("floor notes silent when assertions increase and test restored",
               [n for n in converge(plan, base="floor-base")[0] if n.startswith("floor: ")], [])

    if failures:
        print("FAIL: sdlc-check self-test\n  " + "\n  ".join(failures))
        return 1
    print("PASS: sdlc-check self-test (clarify with Coverage and flows, the task parser and its refusals, converge with tracing and --checks on a scratch repo)")
    return 0


def main(argv):
    if argv == ["--self-test"]:
        return self_test()
    if len(argv) == 2 and argv[0] == "clarify":
        cmd = "clarify"
    elif argv[:1] == ["converge"] and len(argv) >= 2 and not argv[1].startswith("--"):
        cmd, base, checks, rest = "converge", None, False, argv[2:]
        while rest:
            if rest[0] == "--checks" and not checks:
                checks, rest = True, rest[1:]
            elif rest[0] == "--base" and base is None and len(rest) >= 2:
                base, rest = rest[1], rest[2:]
            else:
                print(__doc__.strip(), file=sys.stderr)
                return 2
    else:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        if cmd == "clarify":
            notes, gaps = clarify_intent(argv[1], flow_tool())
        else:
            notes, gaps = converge(argv[1], base, checks)
    except (Malformed, OSError, UnicodeDecodeError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    for line in notes:
        print(line)
    for line in gaps:
        print(f"gap: {line}")
    print(f"{'FAIL' if gaps else 'PASS'}: {cmd} {argv[1]}, {len(gaps)} gap(s)")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
