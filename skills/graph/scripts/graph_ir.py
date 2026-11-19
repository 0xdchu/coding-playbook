#!/usr/bin/env python3
"""Strict reader for the flow-diagram IR (a JSON file): an unknown field, a wrong type or a missing field is an error
with its JSON path, never silently ignored.

The format (documented for authors in SKILL.md):

    {"kind": "sequence" | "workflow", "title": str, "subtitle"?: str, "theme"?: "dark" | "light",
     "direction"?: "down" | "right",                        # workflow only
     "participants": [...], "edges": [...], "steps": [...], # sequence
     "nodes": [...], "links": [...]}                        # workflow

A diagnostic is a dict {"severity": "error" | "warning", "rule": str, "path": str, "message": str}.
"""
from dataclasses import dataclass, field

KINDS = ("sequence", "workflow")
THEMES = ("dark", "light")
DIRECTIONS = ("down", "right")
STEP_KINDS = ("call", "call-return", "async", "reply", "self")
FRAGMENTS = ("alt", "opt", "loop", "par", "break")
BRANCHED = ("alt", "par")
SHAPES = ("start", "step", "decision", "end")
PROVENANCE = ("proven", "heuristic")


def diag(severity, rule, path, message):
    return {"severity": severity, "rule": rule, "path": path, "message": message}


MAX_DEPTH = 32   # fragments inside fragments; deeper input is refused, not recursed into


@dataclass
class Source:
    path: str
    line: int
    end_line: int = None
    label: str = None
    at: str = ""          # JSON path, for diagnostics
    snippet: str = None   # filled by graph_sources when verified


@dataclass
class Participant:
    id: str
    label: str
    external: bool = False
    sources: list = field(default_factory=list)
    at: str = ""


@dataclass
class Edge:
    frm: str
    to: str
    id: str = None
    label: str = None
    provenance: str = None
    sources: list = field(default_factory=list)
    at: str = ""


@dataclass
class Step:
    frm: str
    to: str
    label: str
    kind: str = "call"
    note: str = None
    emphasis: bool = False
    external: bool = False
    number: str = None     # the author's override of the shown number
    shown: str = None      # the number drawn (set by graph_validate.number_steps)
    edge: object = None    # the matched Edge, or None (set by graph_validate)
    reply: bool = False    # matched an edge in the reverse direction (set by graph_validate)
    at: str = ""
    edge_id: str = None    # the author's pick of one edge by id (IR key "edge"), when a pair has several


@dataclass
class Branch:
    label: str
    steps: list
    at: str = ""


@dataclass
class Fragment:
    fragment: str
    label: str
    steps: list = None       # opt, loop, break
    branches: list = None    # alt, par
    shown: str = None
    at: str = ""

    def children(self):
        """Every direct child step or fragment, branches in order."""
        if self.branches is not None:
            return [s for b in self.branches for s in b.steps]
        return list(self.steps or [])


@dataclass
class Node:
    id: str
    label: str
    shape: str = "step"
    detail: str = None
    note: str = None
    sources: list = field(default_factory=list)
    at: str = ""


@dataclass
class Link:
    frm: str
    to: str
    label: str = None
    at: str = ""


@dataclass
class Diagram:
    kind: str
    title: str
    subtitle: str = None
    theme: str = "dark"
    direction: str = "down"
    participants: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    steps: list = field(default_factory=list)
    nodes: list = field(default_factory=list)
    links: list = field(default_factory=list)


class _Reader:
    def __init__(self):
        self.diags = []

    def err(self, rule, path, message):
        self.diags.append(diag("error", rule, path, message))

    def obj(self, value, path, required, optional):
        """The dict at path with its keys checked; None (and an error) when it is not an object."""
        if not isinstance(value, dict):
            self.err("bad-type", path, "expected an object")
            return None
        for k in value:
            if value[k] is None and (k in required or k in optional):
                self.err("bad-type", f"{path}.{k}" if path else k, f"'{k}' is null; give a value or leave the field out")
            if k not in required and k not in optional:
                self.err("unknown-field", f"{path}.{k}" if path else k,
                         f"unknown field '{k}' (allowed: {', '.join(sorted(set(required) | set(optional)))})")
        for k in required:
            if k not in value:
                self.err("missing-field", f"{path}.{k}" if path else k, f"missing field '{k}'")
        return value

    def text(self, value, path, required=True, empty=False):
        if value is None:
            return None   # a missing required field was already reported by obj(), a null one too
        if not isinstance(value, str) or (not empty and not value.strip()):
            self.err("bad-type", path, "expected a non-empty string")
            return None
        return value

    def choice(self, value, path, allowed, default):
        if value is None:
            return default
        if value not in allowed:
            self.err("bad-value", path, f"expected one of {', '.join(allowed)}, got {value!r}")
            return default
        return value

    def flag(self, value, path):
        if value is None:
            return False
        if not isinstance(value, bool):
            self.err("bad-type", path, "expected true or false")
            return False
        return value

    def items(self, value, path):
        if value is None:
            return []
        if not isinstance(value, list):
            self.err("bad-type", path, "expected a list")
            return []
        return value

    def source(self, value, path):
        v = self.obj(value, path, ("path", "line"), ("end_line", "label"))
        if v is None:
            return None
        p = self.text(v.get("path"), f"{path}.path")
        line, end = v.get("line"), v.get("end_line")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            self.err("bad-type", f"{path}.line", "expected a line number >= 1")
            line = None
        if end is not None and (not isinstance(end, int) or isinstance(end, bool) or (line and end < line)):
            self.err("bad-type", f"{path}.end_line", "expected a line number >= line")
            end = None
        if p is None or line is None:
            return None
        return Source(p, line, end, self.text(v.get("label"), f"{path}.label", required=False), at=path)

    def sources(self, value, path):
        return [s for i, raw in enumerate(self.items(value, path)) if (s := self.source(raw, f"{path}[{i}]"))]

    def step_or_fragment(self, value, path):
        if isinstance(value, dict) and "fragment" in value:
            return self.fragment(value, path)
        v = self.obj(value, path, ("from", "to", "label"),
                     ("kind", "note", "emphasis", "external", "number", "edge"))
        if v is None:
            return None
        frm, to = self.text(v.get("from"), f"{path}.from"), self.text(v.get("to"), f"{path}.to")
        label = self.text(v.get("label"), f"{path}.label")
        number = v.get("number")
        if number is not None and (not isinstance(number, str) or not number.strip()):
            self.err("bad-type", f"{path}.number", "expected a non-empty string")
            number = None
        if frm is None or to is None or label is None:
            return None
        return Step(frm, to, label, self.choice(v.get("kind"), f"{path}.kind", STEP_KINDS, "call"),
                    self.text(v.get("note"), f"{path}.note", required=False),
                    self.flag(v.get("emphasis"), f"{path}.emphasis"), self.flag(v.get("external"), f"{path}.external"),
                    number, at=path, edge_id=self.text(v.get("edge"), f"{path}.edge", required=False))

    def step_list(self, value, path):
        return [s for i, raw in enumerate(self.items(value, path)) if (s := self.step_or_fragment(raw, f"{path}[{i}]"))]

    def fragment(self, value, path):
        self.depth = getattr(self, "depth", 0) + 1
        try:
            if self.depth > MAX_DEPTH:
                self.err("bad-value", path, f"fragments nested deeper than {MAX_DEPTH}; flatten the diagram")
                return None
            return self._fragment(value, path)
        finally:
            self.depth -= 1

    def _fragment(self, value, path):
        name = value.get("fragment")
        if name not in FRAGMENTS:
            self.err("bad-value", f"{path}.fragment", f"expected one of {', '.join(FRAGMENTS)}, got {name!r}")
            return None
        if name in BRANCHED:
            v = self.obj(value, path, ("fragment", "branches"), ("label",))
        else:
            v = self.obj(value, path, ("fragment", "label", "steps"), ())
        if v is None:
            return None
        label = self.text(v.get("label"), f"{path}.label", required=name not in BRANCHED)
        frag = Fragment(name, label or "", at=path)
        if name in BRANCHED:
            frag.branches = []
            for i, raw in enumerate(self.items(v.get("branches"), f"{path}.branches")):
                bp = f"{path}.branches[{i}]"
                b = self.obj(raw, bp, ("label", "steps"), ())
                if b is None:
                    continue
                frag.branches.append(Branch(self.text(b.get("label"), f"{bp}.label") or "",
                                            self.step_list(b.get("steps"), f"{bp}.steps"), at=bp))
        else:
            frag.steps = self.step_list(v.get("steps"), f"{path}.steps")
        return frag


def parse(data):
    """(Diagram or None, diagnostics) from the decoded JSON value."""
    r = _Reader()
    common = ("subtitle", "theme")
    if not isinstance(data, dict):
        r.err("bad-type", "", "expected a JSON object at the top level")
        return None, r.diags
    kind = data.get("kind")
    if kind not in KINDS:
        r.err("bad-value", "kind", f"expected one of {', '.join(KINDS)}, got {kind!r}")
        return None, r.diags
    if kind == "sequence":
        v = r.obj(data, "", ("kind", "title", "participants", "steps"), common + ("edges",))
    else:
        v = r.obj(data, "", ("kind", "title", "nodes"), common + ("links", "direction"))
    d = Diagram(kind, r.text(v.get("title"), "title") or "", r.text(v.get("subtitle"), "subtitle", required=False),
                r.choice(v.get("theme"), "theme", THEMES, "dark"), r.choice(v.get("direction"), "direction", DIRECTIONS, "down"))
    if kind == "sequence":
        for i, raw in enumerate(r.items(v.get("participants"), "participants")):
            p = f"participants[{i}]"
            o = r.obj(raw, p, ("id", "label"), ("external", "sources"))
            if o is None:
                continue
            pid, label = r.text(o.get("id"), f"{p}.id"), r.text(o.get("label"), f"{p}.label")
            if pid and label:
                d.participants.append(Participant(pid, label, r.flag(o.get("external"), f"{p}.external"),
                                                  r.sources(o.get("sources"), f"{p}.sources"), at=p))
        for i, raw in enumerate(r.items(v.get("edges"), "edges")):
            p = f"edges[{i}]"
            o = r.obj(raw, p, ("from", "to"), ("id", "label", "provenance", "sources"))
            if o is None:
                continue
            frm, to = r.text(o.get("from"), f"{p}.from"), r.text(o.get("to"), f"{p}.to")
            if frm and to:
                d.edges.append(Edge(frm, to, r.text(o.get("id"), f"{p}.id", required=False),
                                    r.text(o.get("label"), f"{p}.label", required=False),
                                    r.choice(o.get("provenance"), f"{p}.provenance", PROVENANCE, None),
                                    r.sources(o.get("sources"), f"{p}.sources"), at=p))
        d.steps = r.step_list(v.get("steps"), "steps")
    else:
        for i, raw in enumerate(r.items(v.get("nodes"), "nodes")):
            p = f"nodes[{i}]"
            o = r.obj(raw, p, ("id", "label"), ("shape", "detail", "note", "sources"))
            if o is None:
                continue
            nid, label = r.text(o.get("id"), f"{p}.id"), r.text(o.get("label"), f"{p}.label")
            if nid and label:
                d.nodes.append(Node(nid, label, r.choice(o.get("shape"), f"{p}.shape", SHAPES, "step"),
                                    r.text(o.get("detail"), f"{p}.detail", required=False),
                                    r.text(o.get("note"), f"{p}.note", required=False),
                                    r.sources(o.get("sources"), f"{p}.sources"), at=p))
        for i, raw in enumerate(r.items(v.get("links"), "links")):
            p = f"links[{i}]"
            o = r.obj(raw, p, ("from", "to"), ("label",))
            if o is None:
                continue
            frm, to = r.text(o.get("from"), f"{p}.from"), r.text(o.get("to"), f"{p}.to")
            if frm and to:
                d.links.append(Link(frm, to, r.text(o.get("label"), f"{p}.label", required=False), at=p))
    return d, r.diags


def walk_steps(items):
    """Every Step and Fragment in drawing order, depth first (a fragment before what it contains)."""
    for it in items:
        yield it
        if isinstance(it, Fragment):
            yield from walk_steps(it.children())
