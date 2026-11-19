#!/usr/bin/env python3
"""Model rules for a parsed diagram: every step tied to a declared edge, fragments well formed, numbers unique,
flowchart decisions labelled and every node reachable, cited sources verified against the repo root.

    python3 graph_validate.py --self-test   runs every fixture in ../tests/valid (no error, no warning) and
                                            ../tests/invalid (<rule>[--<case>].json must raise <rule>)
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_ir as ir  # noqa: E402
import graph_sources  # noqa: E402

TESTS = Path(__file__).resolve().parent.parent / "tests"


def number_steps(items, prefix=""):
    """Set .shown on every Step and Fragment: 1, 2, 3 at top level; N.1, N.2 inside fragment N, across its branches."""
    for i, it in enumerate(items, 1):
        n = f"{prefix}{i}"
        if isinstance(it, ir.Fragment):
            it.shown = n
            number_steps(it.children(), n + ".")
        else:
            it.shown = it.number or n


def _sequence(d, diags):
    err = lambda rule, path, msg: diags.append(ir.diag("error", rule, path, msg))
    parts = {}
    for p in d.participants:
        if p.id in parts:
            err("duplicate-id", f"{p.at}.id", f"participant id '{p.id}' is used twice")
        parts[p.id] = p
    forward = {}
    seen_edge_ids = set()
    by_id = {}
    for e in d.edges:
        for end in ("frm", "to"):
            if getattr(e, end) not in parts:
                err("unknown-participant", f"{e.at}.{'from' if end == 'frm' else 'to'}",
                    f"edge names '{getattr(e, end)}', which is not a participant")
        if e.id:
            if e.id in seen_edge_ids:
                err("duplicate-id", f"{e.at}.id", f"edge id '{e.id}' is used twice")
            seen_edge_ids.add(e.id)
            by_id.setdefault(e.id, e)
        forward.setdefault((e.frm, e.to), e)
    if not d.steps:
        err("empty-diagram", "steps", "a sequence needs at least one step")
    shown = {}
    for it in ir.walk_steps(d.steps):
        if isinstance(it, ir.Fragment):
            if it.branches is not None:
                if len(it.branches) < 2:
                    err(f"{it.fragment}-one-branch", it.at, f"'{it.fragment}' needs at least two branches")
                for b in it.branches:
                    if not b.steps:
                        err("empty-fragment", b.at, f"branch '{b.label}' of '{it.fragment}' has no steps")
                if it.fragment == "par":
                    for b in it.branches:
                        for s in b.steps:
                            if isinstance(s, ir.Fragment) and s.fragment == "par":
                                err("par-in-par", s.at, "a 'par' directly inside a 'par'; merge their branches")
            elif not it.children():
                err("empty-fragment", it.at, f"'{it.fragment}' has no steps")
        else:
            missing = [x for x in (it.frm, it.to) if x not in parts]
            for x in missing:
                err("unknown-participant", it.at, f"step names '{x}', which is not a participant")
            if (it.frm == it.to) != (it.kind == "self"):
                err("self-mismatch", it.at, "a step from a participant to itself needs kind 'self', and only it")
            elif not missing and it.edge_id is not None:
                e = by_id.get(it.edge_id)
                if e is None:
                    err("unknown-edge", f"{it.at}.edge", f"no edge has id '{it.edge_id}'")
                elif (e.frm, e.to) == (it.frm, it.to):
                    it.edge = e
                elif (e.to, e.frm) == (it.frm, it.to):
                    it.edge, it.reply = e, True
                else:
                    err("edge-mismatch", f"{it.at}.edge",
                        f"edge '{it.edge_id}' joins '{e.frm}' and '{e.to}', not '{it.frm}' and '{it.to}'")
            elif not missing and it.kind != "self":
                # Exempt: a step marked external, or one that starts at an external party (a click, a webhook arriving).
                # A step from an internal party needs an edge even toward an external service: the call is in the code.
                external = it.external or parts[it.frm].external
                if (it.frm, it.to) in forward:
                    it.edge = forward[(it.frm, it.to)]
                elif (it.to, it.frm) in forward and not external:
                    # A step an external party starts (a webhook, a click) is its own message, never the reply of a
                    # call our code made the other way, so it does not borrow that edge (or its proof).
                    it.edge, it.reply = forward[(it.to, it.frm)], True
                elif not external:
                    err("step-without-edge", it.at,
                        f"no edge declared between '{it.frm}' and '{it.to}'; declare it in 'edges' (with sources), "
                        "or mark the step external (an external participant exempts only the steps it starts)")
        if it.shown in shown:
            err("duplicate-number", it.at, f"number {it.shown} is already used at {shown[it.shown]}")
        shown.setdefault(it.shown, it.at)


def _workflow(d, diags):
    err = lambda rule, path, msg: diags.append(ir.diag("error", rule, path, msg))
    nodes = {}
    for n in d.nodes:
        if n.id in nodes:
            err("duplicate-id", f"{n.at}.id", f"node id '{n.id}' is used twice")
        nodes[n.id] = n
    if not d.nodes:
        err("empty-diagram", "nodes", "a workflow needs at least one node")
        return
    out = {n.id: [] for n in d.nodes}
    for link in d.links:
        bad = False
        for end, name in ((link.frm, "from"), (link.to, "to")):
            if end not in nodes:
                err("unknown-node", f"{link.at}.{name}", f"link names '{end}', which is not a node")
                bad = True
        if bad:
            continue
        if link.frm == link.to:
            err("self-link", link.at, "a link from a node to itself; draw the loop through the steps it repeats")
            continue
        out[link.frm].append(link)
    for n in d.nodes:
        if n.shape == "decision":
            if len(out[n.id]) < 2:
                err("decision-one-branch", n.at, f"decision '{n.label}' needs at least two outgoing links")
            for link in out[n.id]:
                if not link.label:
                    err("decision-unlabelled", link.at, f"a link out of decision '{n.label}' needs a label (e.g. Yes / No)")
        if n.shape == "end" and out[n.id]:
            err("end-has-exit", n.at, f"end node '{n.label}' has outgoing links")
    starts = [n.id for n in d.nodes if n.shape == "start"] or [d.nodes[0].id]
    seen, todo = set(starts), list(starts)
    while todo:
        for link in out[todo.pop()]:
            if link.to not in seen:
                seen.add(link.to)
                todo.append(link.to)
    for n in d.nodes:
        if n.id not in seen:
            err("unreachable-node", n.at, f"node '{n.label}' cannot be reached from a start node")


def all_sources(d):
    for group in (d.participants, d.edges, d.nodes):
        for x in group:
            yield from x.sources


def validate(d, repo_root=None):
    """Diagnostics for a parsed Diagram; numbers steps and matches edges in place."""
    diags = []
    if d.kind == "sequence":
        number_steps(d.steps)
        _sequence(d, diags)
        if repo_root:
            externals = {p.id for p in d.participants if p.external}
            for e in d.edges:
                if not e.sources and e.frm not in externals:
                    diags.append(ir.diag("warning", "edge-without-source", e.at,
                                         f"edge '{e.frm}' -> '{e.to}' cites no source; it is drawn as unproven"))
    else:
        _workflow(d, diags)
    sources = list(all_sources(d))
    if repo_root:
        for s in sources:
            diags.extend(graph_sources.verify(repo_root, s))
    elif sources:
        diags.append(ir.diag("warning", "sources-not-verified", "",
                             f"{len(sources)} source(s) cited but no --repo-root given; they are shown unverified"))
    return diags


def load(path, repo_root=None):
    """(Diagram or None, diagnostics) for an IR file."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, [ir.diag("error", "bad-json", "", f"{path}: {e}")]
    d, diags = ir.parse(data)
    if d is None or any(x["severity"] == "error" for x in diags):
        return d, diags
    return d, diags + validate(d, repo_root)


def scratch_repo(tmp):
    """A repo root for the source fixtures: app.py (20 lines), .env, secrets/, a link out of the root."""
    root = tmp / "repo"
    root.mkdir()
    (root / "app.py").write_text("".join(f"line {i}\n" for i in range(1, 21)))
    (root / ".env").write_text("TOKEN=not-a-real-one\n")
    (root / "settings.py").write_text("DEBUG = True\nAPI_KEY = \"abcd1234efgh5678\"\nNAME = 'x'\n")
    (root / "secrets").mkdir()
    (root / "secrets" / "notes.txt").write_text("x\n")
    (tmp / "outside.txt").write_text("outside\n")
    try:
        os.symlink(tmp / "outside.txt", root / "link.txt")
    except OSError:
        pass
    return root


def self_test():
    problems = []
    tmp = Path(tempfile.mkdtemp(prefix="graph-validate-"))
    try:
        root = scratch_repo(tmp)
        valid = sorted((TESTS / "valid").glob("*.json"))
        invalid = sorted((TESTS / "invalid").glob("*.json"))
        if not valid or not invalid:
            problems.append(f"no fixtures under {TESTS}")
        for f in valid:
            _, diags = load(f, root if f.name.startswith("source-") else None)
            bad = [x for x in diags if x["severity"] in ("error", "warning")]
            if bad:
                problems.append(f"valid/{f.name}: {bad}")
        for f in invalid:
            rule = f.stem.split("--")[0]
            with_root = rule.startswith("source-") or rule == "edge-without-source"
            _, diags = load(f, root if with_root else None)
            rules = {x["rule"] for x in diags if x["severity"] in ("error", "warning")}
            if rule not in rules:
                problems.append(f"invalid/{f.name}: expected {rule}, got {sorted(rules) or 'nothing'}")
        if (root / ".env").read_text() != "TOKEN=not-a-real-one\n":
            problems.append("a fixture changed the scratch repo")
        seq = ir.parse({"kind": "sequence", "title": "t",
                        "participants": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                        "edges": [{"from": "a", "to": "b"}],
                        "steps": [{"from": "a", "to": "b", "label": "x"},
                                  {"fragment": "alt", "branches": [
                                      {"label": "ok", "steps": [{"from": "b", "to": "a", "label": "y"}]},
                                      {"label": "no", "steps": [{"from": "a", "to": "b", "label": "z"},
                                                                {"fragment": "loop", "label": "each",
                                                                 "steps": [{"from": "a", "to": "b", "label": "w"}]}]}]},
                                  {"from": "a", "to": "b", "label": "v"}]})[0]
        validate(seq)
        got = [it.shown for it in ir.walk_steps(seq.steps)]
        if got != ["1", "2", "2.1", "2.2", "2.3", "2.3.1", "3"]:
            problems.append(f"numbering wrong: {got}")
        reply = [it for it in ir.walk_steps(seq.steps) if isinstance(it, ir.Step) and it.label == "y"][0]
        if not reply.reply:
            problems.append("reverse step not marked as a reply")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return problems


def main(argv):
    if argv == ["--self-test"]:
        found = self_test()
        print("FAIL\n" + "\n".join(found) if found else "PASS: graph_validate self-test")
        return 1 if found else 0
    print("usage: graph_validate.py --self-test (validate diagrams with graph.py validate)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
