#!/usr/bin/env python3
"""Flow diagrams: validate an IR file, render it as one standalone HTML page, import a call trace.

    graph.py validate <ir.json> [--repo-root DIR] [--json]
    graph.py render <ir.json> -o <out.html> [--repo-root DIR] [--theme dark|light]
    graph.py from-trace <trace.json> -o <ir.json>
    graph.py --self-test

Exit 0: valid, or the file was written. Exit 1: the diagram has errors (render then writes nothing). Exit 2: usage
error, or a trace that cannot be converted. The repo root is only ever read; render writes only the `-o` file, through
a temp file in the same folder and an atomic replace.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import graph_geometry as geo  # noqa: E402
import graph_sequence  # noqa: E402
import graph_svg  # noqa: E402
import graph_trace  # noqa: E402
import graph_validate as val  # noqa: E402
import graph_workflow  # noqa: E402

TESTS = HERE.parent / "tests"
VIEWER = HERE / "graph_viewer.html"


def _line(d):
    return f"{d['severity']} {d['rule']} {d['path'] or '(root)'}: {d['message']}"


def _json_in_script(obj):
    """JSON safe inside a <script> element: every '<' (so '</script>' and '<!--' cannot occur) is escaped."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True).replace("<", "\\u003c")


def build_page(d, layout, theme):
    """The standalone HTML page for a validated diagram and its layout."""
    items, _ = graph_svg.walkthrough(layout, d)
    data = {"title": d.title, "subtitle": d.subtitle or "", "kind": d.kind, "items": items}
    fields = {"THEME": theme, "TITLE": graph_svg.esc(d.title), "SUBTITLE": graph_svg.esc(d.subtitle or ""),
              "SVG": graph_svg.to_svg(layout, d), "DATA": _json_in_script(data)}
    template = VIEWER.read_text(encoding="utf-8")
    return re.sub(r"\{\{(THEME|TITLE|SUBTITLE|SVG|DATA)\}\}", lambda m: fields[m.group(1)], template)


def make_layout(d, strict):
    if d.kind == "sequence":
        return graph_sequence.layout(d, strict_sources=strict)
    return graph_workflow.layout(d)


def write_atomic(path, text):
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".graph-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(text.encode("utf-8"))
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _usage(msg):
    print(f"graph.py: {msg}", file=sys.stderr)
    return 2


def _root(args):
    if args.repo_root is None:
        return None, 0
    if not os.path.isdir(args.repo_root):
        return None, _usage(f"--repo-root {args.repo_root!r} is not a folder")
    return args.repo_root, 0


def cmd_validate(args):
    root, bad = _root(args)
    if bad:
        return bad
    _, diags = val.load(args.ir, root)
    errors = [x for x in diags if x["severity"] == "error"]
    if args.json:
        print(json.dumps({"ok": not errors, "errors": len(errors),
                          "warnings": sum(x["severity"] == "warning" for x in diags), "diagnostics": diags},
                         indent=2, sort_keys=True))
    else:
        for x in diags:
            print(_line(x))
        if not diags:
            print("ok: no errors, no warnings")
    return 1 if errors else 0


def cmd_render(args):
    if not args.output.endswith(".html"):
        return _usage("-o must end in .html")
    if not os.path.isdir(os.path.dirname(os.path.abspath(args.output))):
        return _usage(f"the folder of {args.output!r} does not exist")
    root, bad = _root(args)
    if bad:
        return bad
    d, diags = val.load(args.ir, root)
    errors = [x for x in diags if x["severity"] == "error"]
    for x in diags:
        print(_line(x), file=sys.stdout if x["severity"] == "error" else sys.stderr)
    if errors or d is None:
        return 1
    layout = make_layout(d, strict=root is not None)
    geom = geo.check(layout)
    gerr = [x for x in geom if x["severity"] == "error"]
    if gerr:
        for x in gerr:
            print(_line(x))
        return 1
    page = build_page(d, layout, args.theme or d.theme)
    write_atomic(args.output, page)
    crossings = next((x["message"] for x in geom if x["rule"] == "crossings"), "")
    print(f"wrote {args.output} ({crossings})")
    return 0


def cmd_from_trace(args):
    if not args.output.endswith(".json"):
        return _usage("-o must end in .json")
    if not os.path.isdir(os.path.dirname(os.path.abspath(args.output))):
        return _usage(f"the folder of {args.output!r} does not exist")
    try:
        trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
        data = graph_trace.convert(trace)
    except (OSError, ValueError) as e:      # graph_trace.TraceError is a ValueError
        return _usage(f"cannot convert {args.trace}: {e}")
    write_atomic(args.output, json.dumps(data, indent=2) + "\n")
    print(f"wrote {args.output} ({len(data['steps'])} step(s))")
    return 0


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"graph.py: {message}", file=sys.stderr)
        raise SystemExit(2)


def parser():
    p = _Parser(prog="graph.py", description="Flow diagrams: validate, render, import a trace.")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    v = sub.add_parser("validate", help="check an IR file")
    v.add_argument("ir")
    v.add_argument("--repo-root")
    v.add_argument("--json", action="store_true")
    rd = sub.add_parser("render", help="write one standalone HTML page")
    rd.add_argument("ir")
    rd.add_argument("-o", "--output", required=True)
    rd.add_argument("--repo-root")
    rd.add_argument("--theme", choices=("dark", "light"))
    t = sub.add_parser("from-trace", help="convert a call trace to an IR file")
    t.add_argument("trace")
    t.add_argument("-o", "--output", required=True)
    return p


def main(argv):
    if argv == ["--self-test"]:
        found = self_test()
        print("FAIL\n" + "\n".join(found) if found else "PASS: graph self-test")
        return 1 if found else 0
    args = parser().parse_args(argv)
    return {"validate": cmd_validate, "render": cmd_render, "from-trace": cmd_from_trace}[args.cmd](args)


# ---------------------------------------------------------------------------------------------------------------------
# self-test

FORBIDDEN = [("http://", re.compile(r"http://", re.I)), ("https://", re.compile(r"https://", re.I)),
             ("<link", re.compile(r"<link", re.I)), ("src= other than data:", re.compile(r"src\s*=(?!\s*[\"']?data:)", re.I)),
             ("url( other than #/data:", re.compile(r"url\((?!\s*[\"']?(#|data:))", re.I))]


def forbidden(text):
    return [name for name, rx in FORBIDDEN if rx.search(text)]


def tree_checksum(root):
    h = hashlib.sha256()
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + files):
            p = os.path.join(base, name)
            h.update(os.path.relpath(p, root).encode() + b"\0")
            if os.path.islink(p):
                h.update(b"L" + os.readlink(p).encode())
            elif os.path.isfile(p):
                h.update(Path(p).read_bytes())
    return h.hexdigest()


def run(argv):
    """(exit code, stdout, stderr) of main(argv) in this process."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 2
    return code, out.getvalue(), err.getvalue()


def _panel_data(html_text):
    m = re.search(r'<script type="application/json" id="flow-data">(.*?)</script>', html_text, re.S)
    return json.loads(m.group(1)) if m else None


def _trace_repo(tmp):
    root = tmp / "trace-repo"
    (root / "src").mkdir(parents=True)
    for name in ("api", "orders", "db"):
        (root / "src" / f"{name}.py").write_text("".join(f"# {name} line {i}\n" for i in range(1, 13)))
    return root


def _fixtures():
    groups = [("valid", TESTS / "valid"), ("sequence", TESTS / "sequence"), ("workflow", TESTS / "workflow")]
    return [(f"{g}/{f.name}", f) for g, folder in groups for f in sorted(folder.glob("*.json"))]


def self_test():
    problems = []
    tmp = Path(tempfile.mkdtemp(prefix="graph-cli-"))
    try:
        root = val.scratch_repo(tmp)
        before = tree_checksum(root)
        out = tmp / "out"
        out.mkdir()
        fixtures = _fixtures()
        if len(fixtures) < 10:
            problems.append(f"only {len(fixtures)} fixtures found under {TESTS}")
        expected_files = set()
        for tag, f in fixtures:
            args = [str(f), "-o"]
            extra = ["--repo-root", str(root)] if f.name.startswith("source-") else []
            a, b = out / f"{f.parent.name}-{f.stem}-a.html", out / f"{f.parent.name}-{f.stem}-b.html"
            expected_files |= {a.name, b.name}
            ca, oa, ea = run(["render", args[0], "-o", str(a)] + extra)
            cb, _, _ = run(["render", args[0], "-o", str(b)] + extra)
            if ca != 0 or cb != 0 or not a.exists() or not b.exists():
                problems.append(f"{tag}: render failed ({ca}/{cb}): {oa.strip()} {ea.strip()}")
                continue
            if a.read_bytes() != b.read_bytes():
                problems.append(f"{tag}: two renders differ")
            text = a.read_text(encoding="utf-8")
            hits = forbidden(text)
            if hits:
                problems.append(f"{tag}: output contains {hits}")
            if "<svg" not in text or "data-k=" not in text or "data-ref=" not in text:
                problems.append(f"{tag}: output lacks the svg, data-k or data-ref")
            data = _panel_data(text)
            if data is None or not data["items"]:
                problems.append(f"{tag}: no panel data")
            elif {it["k"] for it in data["items"]} != set(range(len(data["items"]))):
                problems.append(f"{tag}: walkthrough indexes are not 0..n-1")
        extra_files = sorted(p.name for p in out.iterdir() if p.name not in expected_files)
        if extra_files:
            problems.append(f"render left other files in the output folder: {extra_files}")

        # theme, and the page of a diagram with a repo root has the cited snippets in its panel data
        light = out / "light.html"
        c, _, _ = run(["render", str(TESTS / "valid" / "source-cited.json"), "-o", str(light), "--repo-root", str(root),
                       "--theme", "light"])
        text = light.read_text(encoding="utf-8") if light.exists() else ""
        if c != 0 or 'data-theme="light"' not in text.split("<body", 1)[0]:
            problems.append("--theme light did not set the page theme")
        data = _panel_data(text) or {"items": []}
        snippets = [s["snippet"] for it in data["items"] for s in it["sources"]]
        if "line 3\nline 4\nline 5" not in snippets:
            problems.append(f"panel data lacks the cited snippet: {snippets}")
        plain = out / "plain.html"
        run(["render", str(TESTS / "valid" / "source-cited.json"), "-o", str(plain)])
        data = _panel_data(plain.read_text(encoding="utf-8")) or {"items": []}
        if any(s["snippet"] is not None for it in data["items"] for s in it["sources"]):
            problems.append("a snippet is shown without a repo root")

        # invalid fixtures: exit 1 and nothing written
        for f in sorted((TESTS / "invalid").glob("*.json")):
            rule = f.stem.split("--")[0]
            extra = ["--repo-root", str(root)] if rule.startswith("source-") or rule == "edge-without-source" else []
            target = out / f"invalid-{f.stem}.html"
            code, text_out, text_err = run(["render", str(f), "-o", str(target)] + extra)
            if code != 1 or target.exists() or rule not in text_out + text_err:
                problems.append(f"invalid/{f.name}: exit {code}, file written {target.exists()}, "
                                f"rule shown {rule in text_out + text_err}")
        probe = subprocess.run([sys.executable, str(Path(__file__).resolve()), "render", str(TESTS / "invalid" / "unknown-field.json"),
                                "-o", str(out / "sub.html")], capture_output=True, text=True)
        if probe.returncode != 1 or (out / "sub.html").exists() or "unknown-field" not in probe.stdout:
            problems.append(f"subprocess render of an invalid fixture: exit {probe.returncode}")

        # render refuses geometry errors, through the same code path (a hand-built layout stands in for the layout)
        bad = json.loads((TESTS / "cli" / "bad-layout.json").read_text())
        target = out / "geometry.html"
        saved = graph_sequence.layout
        graph_sequence.layout = lambda d, strict_sources=False: bad
        try:
            code, text_out, _ = run(["render", str(TESTS / "valid" / "sequence-basic.json"), "-o", str(target)])
        finally:
            graph_sequence.layout = saved
        if code != 1 or target.exists() or "route-through-node" not in text_out:
            problems.append(f"geometry error not refused: exit {code}, written {target.exists()}, output {text_out.strip()!r}")

        # usage errors
        for argv, why in ((["render", str(TESTS / "valid" / "sequence-basic.json"), "-o", str(out / "x.txt")], "-o not .html"),
                          (["render", str(TESTS / "valid" / "sequence-basic.json")], "no -o"),
                          (["bogus"], "unknown command"), ([], "no command"),
                          (["render", str(TESTS / "valid" / "sequence-basic.json"), "-o", str(out / "x.html"), "--theme", "pink"], "bad theme"),
                          (["validate", str(TESTS / "valid" / "sequence-basic.json"), "--repo-root", str(tmp / "nope")], "bad root"),
                          (["from-trace", str(TESTS / "cli" / "trace.json"), "-o", str(out / "x.txt")], "trace -o not .json")):
            code, _, _ = run(argv)
            if code != 2:
                problems.append(f"usage error ({why}) exited {code}, not 2")
        if (out / "x.txt").exists() or (out / "x.html").exists():
            problems.append("a usage error wrote a file")

        # validate: human lines and JSON
        code, text_out, _ = run(["validate", str(TESTS / "invalid" / "unknown-field.json")])
        if code != 1 or not re.search(r"^error unknown-field \S+: ", text_out, re.M):
            problems.append(f"validate human output wrong: exit {code}: {text_out!r}")
        code, text_out, _ = run(["validate", str(TESTS / "invalid" / "unknown-field.json"), "--json"])
        try:
            parsed = json.loads(text_out)
            if code != 1 or parsed["ok"] or not parsed["diagnostics"] or parsed["diagnostics"][0]["rule"] != "unknown-field":
                problems.append("validate --json content wrong")
        except ValueError:
            problems.append("validate --json output does not parse")
        code, text_out, _ = run(["validate", str(TESTS / "valid" / "sequence-basic.json"), "--json"])
        if code != 0 or not json.loads(text_out)["ok"]:
            problems.append("validate --json on a valid fixture failed")

        # markup in text is escaped, everywhere
        evil = json.loads((TESTS / "valid" / "sequence-basic.json").read_text())
        evil["title"] = "T</script><img src=x onerror=alert(1)>"
        evil["participants"][0]["label"] = "B<b>&\"'"
        evil["steps"][0]["note"] = "</script><script>alert(1)</script>"
        evil_path, evil_out = tmp / "evil.json", out / "evil.html"
        evil_path.write_text(json.dumps(evil))
        code, _, _ = run(["render", str(evil_path), "-o", str(evil_out)])
        text = evil_out.read_text(encoding="utf-8") if evil_out.exists() else ""
        if code != 0 or "<img" in text or "<b>" in text or text.count("</script>") != 2 or text.count("<script") != 2:
            problems.append("markup in diagram text was not escaped")
        elif _panel_data(text)["title"] != evil["title"]:
            problems.append("title did not survive the JSON block")

        # trace import
        troot = _trace_repo(tmp)
        tbefore = tree_checksum(troot)
        ir_out, page = out / "trace-ir.json", out / "trace.html"
        code, so, se = run(["from-trace", str(TESTS / "cli" / "trace.json"), "-o", str(ir_out)])
        if code != 0 or not ir_out.exists():
            problems.append(f"from-trace failed: {code} {so} {se}")
        else:
            ir_data = json.loads(ir_out.read_text())
            if [p["label"] for p in ir_data["participants"]] != ["api.py", "orders.py", "db.py"]:
                problems.append(f"trace participants wrong: {ir_data['participants']}")
            if [s["label"] for s in ir_data["steps"]] != ["place_order", "save"] or len(ir_data["edges"]) != 2:
                problems.append("trace steps or edges wrong")
            code, so, _ = run(["validate", str(ir_out), "--repo-root", str(troot)])
            if code != 0 or not so.startswith("ok:"):
                problems.append(f"trace IR does not validate cleanly with a repo root: {so}")
            code, so, se = run(["render", str(ir_out), "-o", str(page), "--repo-root", str(troot)])
            text = page.read_text(encoding="utf-8") if page.exists() else ""
            if code != 0:
                problems.append(f"trace render failed: {so} {se}")
            elif not re.search(r'class="route unproven"[^>]*data-ref="steps\[1\]"', text) \
                    or re.search(r'class="route unproven"[^>]*data-ref="steps\[0\]"', text):
                problems.append("only the heuristic hop should be drawn unproven")
            else:
                items = _panel_data(text)["items"]
                if not (items[1]["unproven"] and not items[0]["unproven"]):
                    problems.append("panel does not mark the heuristic hop unproven")
                if not any(s["snippet"] for s in items[0]["sources"]):
                    problems.append("trace call site has no snippet with a repo root")
        if tree_checksum(troot) != tbefore:
            problems.append("the trace repo root changed")
        for bad_trace, why in (({"paths": []}, "empty paths"), ({}, "no paths"), ({"paths": [{"steps": []}]}, "no steps"),
                               ({"paths": [{"steps": [{"from_file": "a.py"}]}]}, "missing fields")):
            tp, tout = tmp / "bad-trace.json", out / "bad-trace-ir.json"
            tp.write_text(json.dumps(bad_trace))
            code, _, se = run(["from-trace", str(tp), "-o", str(tout)])
            if code != 2 or tout.exists() or not se.strip():
                problems.append(f"from-trace on {why}: exit {code}, written {tout.exists()}")

        # nothing was written under the scratch repo root, and nothing else is left behind
        if tree_checksum(root) != before:
            problems.append("the repo root changed during validate and render")
        leftovers = [p.name for p in out.iterdir() if p.name.startswith(".graph-")]
        if leftovers:
            problems.append(f"temp files left behind: {leftovers}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return problems


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
