#!/usr/bin/env python3
"""Draw a layout dict (graph_geometry.py) as SVG text, and list the steps or nodes of the walkthrough.

    to_svg(layout, diagram) -> str            deterministic; draws only what the layout holds, plus a header band
    walkthrough(layout, diagram) -> (items, kmap)

Every drawn step, node, route and label carries `data-ref` (its JSON path) and, when it belongs to the walkthrough,
`data-k` (its index in drawing order) so the viewer can highlight it. All text is XML-escaped. The SVG has no xmlns
(it is meant to sit inline in the viewer page; the viewer adds one when it exports); the colours are CSS variables
defined in its own <style>, dark by default, light under `:root[data-theme="light"]`.
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_geometry as geo  # noqa: E402
import graph_ir as ir  # noqa: E402
from graph_geometry import r, text_width  # noqa: E402

HEADER_PAD = 40.0
TITLE_SIZE = 22.0
SUB_SIZE = 14.0
ACTOR_SIZE = 14.0
NODE_SIZE = 13.0
BASELINE = 4.5          # text baseline below the vertical centre of a 13 px line
LINE_H = 18.0
TAB_H = 23.0

FONT = '-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'

_DARK = ("--c-bg:#0b0d12;--c-fg:#e8ebf2;--c-muted:#98a2b3;--c-border:#d5dbe8;--c-box:#141925;--c-line:#c7cedb;"
         "--c-accent:#4da3ff;--c-unproven:#7d8798;--c-frame:#7a8499;--c-tab:#1b2130;--c-pill:#1a2233;--c-dec:#1d2436;")
_LIGHT = ("--c-bg:#fafbfc;--c-fg:#1b2230;--c-muted:#5b6578;--c-border:#2b3548;--c-box:#ffffff;--c-line:#3b4558;"
          "--c-accent:#1668d6;--c-unproven:#8a93a4;--c-frame:#8a93a4;--c-tab:#eef1f6;--c-pill:#e8eef8;--c-dec:#f1f4fa;")

CSS = (
    f".flow{{{_DARK}font-family:{FONT};}}"
    f'.flow[data-theme="light"],:root[data-theme="light"] .flow{{{_LIGHT}}}'
    ".flow .bg{fill:var(--c-bg)}.flow .lblbg{fill:var(--c-bg)}"
    ".flow text{fill:var(--c-fg);font-size:13px;paint-order:stroke;stroke:var(--c-bg);stroke-width:6px;stroke-linejoin:round}"
    ".flow .title{font-size:22px;font-weight:700}"
    ".flow .subtitle{font-size:14px;fill:var(--c-muted)}"
    ".flow .actor rect{fill:var(--c-box);stroke:var(--c-border);stroke-width:1.5}"
    ".flow .actor text{font-size:14px;font-weight:700;stroke:var(--c-box)}"
    ".flow .lifeline{stroke:var(--c-frame);stroke-width:1;stroke-dasharray:4 4;fill:none}"
    ".flow .frame rect.box{fill:none;stroke:var(--c-frame);stroke-width:1;stroke-dasharray:1 3;stroke-linecap:round}"
    ".flow .frame rect.tab{fill:var(--c-tab);stroke:var(--c-frame);stroke-width:1}"
    ".flow .frame .divider{stroke:var(--c-frame);stroke-width:1;stroke-dasharray:6 4}"
    ".flow .frame .name{font-weight:700;stroke:var(--c-tab)}"
    ".flow .frame .cond,.flow .branch{fill:var(--c-muted)}"
    ".flow .route path.line{fill:none;stroke:var(--c-line);stroke-width:1.5;stroke-linejoin:round}"
    ".flow .route.dashed path.line{stroke-dasharray:6 4}"
    ".flow .route.unproven path.line{stroke:var(--c-unproven);stroke-dasharray:6 4}"
    ".flow .route.emphasis path.line{stroke:var(--c-accent);stroke-width:2.5}"
    ".flow .hit{fill:none;stroke:transparent;stroke-width:12;pointer-events:stroke}"
    ".flow .m-n{fill:var(--c-line);stroke:var(--c-line)}"
    ".flow .m-u{fill:var(--c-unproven);stroke:var(--c-unproven)}"
    ".flow .m-e{fill:var(--c-accent);stroke:var(--c-accent)}"
    ".flow .m-open{fill:none;stroke-width:1.5}"
    ".flow .lbl.emphasis{fill:var(--c-accent);font-weight:700}"
    ".flow .lbl.unproven{fill:var(--c-muted)}"
    ".flow .node .sh{fill:var(--c-box);stroke:var(--c-border);stroke-width:1.5}"
    ".flow .node.start .sh,.flow .node.end .sh{fill:var(--c-pill)}"
    ".flow .node.decision .sh{fill:var(--c-dec)}"
    ".flow .node text{stroke:var(--c-box)}"
    ".flow .node.start text,.flow .node.end text{stroke:var(--c-pill)}"
    ".flow .node.decision text{stroke:var(--c-dec)}"
    ".flow .node .t-b{font-weight:700}"
    ".flow .node .t-d{fill:var(--c-muted)}"
)


def esc(s):
    return html.escape(str(s), quote=True)


def _n(v):
    return f"{v:g}"


def _path(points):
    return "M" + " L".join(f"{_n(x)} {_n(y)}" for x, y in points)


def _sources(srcs):
    out = []
    for s in srcs:
        out.append({"path": s.path, "line": s.line, "end_line": s.end_line, "label": s.label, "snippet": s.snippet})
    return out


def walkthrough(layout, diagram):
    """(items, kmap): the walkthrough items in drawing order, and a map from route id / shape id to its index k."""
    items, kmap = [], {}
    if diagram.kind == "sequence":
        steps = {s.at: s for s in ir.walk_steps(diagram.steps) if isinstance(s, ir.Step)}
        parts = {p.id: p for p in diagram.participants}
        for rt in layout["routes"]:
            if rt["id"].endswith(":return"):
                kmap[rt["id"]] = kmap[rt["id"][:-len(":return")]]
                continue
            s = steps.get(rt["ref"])
            if s is None:
                continue
            k = len(items)
            kmap[rt["id"]] = k
            items.append({
                "k": k, "ref": s.at, "number": s.shown, "label": s.label,
                "kind": "reply" if (s.reply and s.kind == "call") else s.kind,
                "route": f"{parts[s.frm].label} -> {parts[s.to].label}" if s.frm in parts and s.to in parts else "",
                "note": s.note, "unproven": rt["style"] == "unproven",
                "external": bool(s.external or (s.frm in parts and parts[s.frm].external)
                                 or (s.to in parts and parts[s.to].external)),
                "sources": _sources(s.edge.sources) if s.edge is not None else []})
        return items, kmap
    nodes = {n.id: n for n in diagram.nodes}
    right = diagram.direction == "right"

    def key(sh):
        return (sh.get("rank", 0), sh["y"] + sh["h"] / 2 if right else sh["x"] + sh["w"] / 2, sh["id"])

    for sh in sorted((s for s in layout["shapes"] if s["kind"] == "node"), key=key):
        n = nodes.get(sh["ref"])
        if n is None:
            continue
        k = len(items)
        kmap[sh["id"]] = k
        items.append({"k": k, "ref": n.at, "number": str(k + 1), "label": n.label, "kind": n.shape, "route": "",
                      "detail": n.detail, "note": n.note, "unproven": False, "external": False,
                      "sources": _sources(n.sources)})
    for rt in layout["routes"]:
        if rt["from"] in kmap:
            kmap[rt["id"]] = kmap[rt["from"]]
    return items, kmap


def _attrs(ref, k):
    out = f' data-ref="{esc(ref)}"'
    if k is not None:
        out += f' data-k="{k}"'
    return out


def _markers():
    defs = []
    for variant in ("n", "u", "e"):
        defs.append(f'<marker id="m-filled-{variant}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" '
                    f'markerHeight="10" markerUnits="userSpaceOnUse" orient="auto">'
                    f'<path class="m-{variant}" d="M0 0 L10 5 L0 10 z"/></marker>')
        defs.append(f'<marker id="m-open-{variant}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" '
                    f'markerHeight="10" markerUnits="userSpaceOnUse" orient="auto">'
                    f'<path class="m-{variant} m-open" d="M1 1 L9 5 L1 9"/></marker>')
    return "<defs>" + "".join(defs) + "</defs>"


def _frame_box(sh):
    """The frame's border and dividers: drawn under the lifelines and routes."""
    out = [f'<g class="frame"{_attrs(sh["ref"], None)}>',
           f'<rect class="box" x="{_n(sh["x"])}" y="{_n(sh["y"])}" width="{_n(sh["w"])}" height="{_n(sh["h"])}" rx="4"/>']
    for dy in sh.get("dividers", []):
        out.append(f'<line class="divider" x1="{_n(sh["x"])}" y1="{_n(dy)}" x2="{_n(sh["x"] + sh["w"])}" y2="{_n(dy)}"/>')
    out.append("</g>")
    return "".join(out)


def _frame_text(sh, labels):
    """The frame's name tab, condition and branch labels: drawn above the lifelines so no line runs over them."""
    out = [f'<g class="frame"{_attrs(sh["ref"], None)}>']
    for lb in labels:
        by = lb["y"] + lb["h"] / 2 + BASELINE
        if ":branch" in lb["id"]:
            # An opaque plate (as under step labels) so a lifeline never runs through the condition or branch text.
            out.append(f'<rect class="lblbg" x="{_n(lb["x"] + 2)}" y="{_n(lb["y"] + 2)}" width="{_n(max(lb["w"] - 4, 0))}" '
                       f'height="{_n(max(lb["h"] - 4, 0))}" rx="3"/>')
            out.append(f'<text class="branch" x="{_n(lb["x"] + geo.LABEL_PAD_X)}" y="{_n(by)}"{_attrs(sh["ref"], None)}>'
                       f'{esc(lb["text"])}</text>')
            continue
        name = sh["label"]      # the tab holds only the fragment name; the condition is its own label
        tab_w = lb["x"] + geo.LABEL_PAD_X + text_width(name) * 1.12 + 8 - sh["x"]
        out.append(f'<rect class="tab" x="{_n(sh["x"])}" y="{_n(sh["y"])}" width="{_n(r(tab_w))}" height="{_n(TAB_H)}" rx="3"/>')
        out.append(f'<text x="{_n(lb["x"] + geo.LABEL_PAD_X)}" y="{_n(by)}"{_attrs(sh["ref"], None)}>'
                   f'<tspan class="name">{esc(name)}</tspan></text>')
    out.append("</g>")
    return "".join(out)


def _label_lines(sh):
    """How many leading lines of a node's wrapped text belong to its label (the rest is the detail)."""
    want = (sh.get("label") or "").replace(" ", "")
    acc = ""
    for i, line in enumerate(sh.get("lines") or [], 1):
        acc += line.replace(" ", "")
        if acc == want:
            return i
    return len(sh.get("lines") or [])


def _node(sh, k, ref):
    x, y, w, h = sh["x"], sh["y"], sh["w"], sh["h"]
    kind = sh["shape"]
    if kind == "decision":
        shape = (f'<polygon class="sh" points="{_n(x + w / 2)},{_n(y)} {_n(x + w)},{_n(y + h / 2)} '
                 f'{_n(x + w / 2)},{_n(y + h)} {_n(x)},{_n(y + h / 2)}"/>')
    elif kind in ("start", "end"):
        shape = f'<rect class="sh" x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" rx="{_n(h / 2)}"/>'
    else:
        shape = f'<rect class="sh" x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" rx="8"/>'
    lines = [ln for ln in (sh.get("lines") or [sh["label"]])]
    nl = _label_lines(sh) if sh.get("lines") else 1
    cy = y + h / 2 - (len(lines) - 1) * LINE_H / 2
    texts = []
    for i, ln in enumerate(lines):
        if not ln:
            continue
        cls = "t-b" if i < nl else "t-d"
        texts.append(f'<text class="{cls}" x="{_n(x + w / 2)}" y="{_n(r(cy + i * LINE_H + BASELINE))}" '
                     f'text-anchor="middle">{esc(ln)}</text>')
    return (f'<g class="node {esc(kind)}"{_attrs(ref, k)}>' + shape + "".join(texts) + "</g>")


def _route(rt, k):
    style = rt["style"]
    variant = "e" if rt.get("emphasis") else ("u" if style == "unproven" else "n")
    cls = f'route {style}' + (" emphasis" if rt.get("emphasis") else "") + (" return" if rt["id"].endswith(":return") else "")
    d = _path(rt["points"])
    marker = ""
    if rt["head"] in ("filled", "open"):
        marker = f' marker-end="url(#m-{rt["head"]}-{variant})"'
    return (f'<g class="{cls}"{_attrs(rt["ref"], k)}><path class="hit" d="{d}"/>'
            f'<path class="line" d="{d}"{marker}/></g>')


def to_svg(layout, diagram):
    items, kmap = walkthrough(layout, diagram)
    title, sub = diagram.title, diagram.subtitle
    head_w = 2 * HEADER_PAD + max(text_width(title, TITLE_SIZE) * 1.1, text_width(sub or "", SUB_SIZE))
    width = r(max(layout["width"], head_w))
    band = r(HEADER_PAD + TITLE_SIZE + (24.0 if sub else 0.0) - 8)
    height = r(layout["height"] + band)
    dx = r((width - layout["width"]) / 2)

    routes = {rt["id"]: rt for rt in layout["routes"]}
    shapes = {sh["id"]: sh for sh in layout["shapes"]}
    body = []
    frame_labels = {}
    route_labels = []
    for lb in layout["labels"]:
        if lb["owner"] in shapes and shapes[lb["owner"]]["kind"] == "frame":
            frame_labels.setdefault(lb["owner"], []).append(lb)
        else:
            route_labels.append(lb)
    for sh in layout["shapes"]:
        if sh["kind"] == "frame":
            body.append(_frame_box(sh))
    for sh in layout["shapes"]:
        if sh["kind"] == "lifeline":
            body.append(f'<line class="lifeline" x1="{_n(sh["x"])}" y1="{_n(sh["y"])}" x2="{_n(sh["x"])}" '
                        f'y2="{_n(sh["y"] + sh["h"])}"{_attrs(sh["ref"], None)}/>')
    for sh in layout["shapes"]:
        if sh["kind"] == "actor":
            body.append(f'<g class="actor"{_attrs(sh["ref"], None)}>'
                        f'<rect x="{_n(sh["x"])}" y="{_n(sh["y"])}" width="{_n(sh["w"])}" height="{_n(sh["h"])}" rx="8"/>'
                        f'<text x="{_n(sh["x"] + sh["w"] / 2)}" y="{_n(r(sh["y"] + sh["h"] / 2 + 5))}" '
                        f'text-anchor="middle">{esc(sh["label"])}</text></g>')
    for rt in layout["routes"]:
        body.append(_route(rt, kmap.get(rt["id"])))
    for sh in layout["shapes"]:
        if sh["kind"] == "node":
            body.append(_node(sh, kmap.get(sh["id"]), sh["ref"]))
    for sh in layout["shapes"]:
        if sh["kind"] == "frame":
            body.append(_frame_text(sh, frame_labels.get(sh["id"], [])))
    for lb in route_labels:
        rt = routes.get(lb["owner"])
        cls = "lbl"
        if rt is not None:
            cls += (" emphasis" if rt.get("emphasis") else "") + (" unproven" if rt["style"] == "unproven" else "")
        ref = rt["ref"] if rt else ""
        k = kmap.get(lb["owner"])
        # An opaque plate under the text, inset from the box edges so it never covers the label's own arrow:
        # lifelines and frame lines pass behind the label at any zoom (a stroke halo alone thins out when scaled).
        body.append(f'<rect class="lblbg" x="{_n(lb["x"] + 2)}" y="{_n(lb["y"] + 2)}" width="{_n(max(lb["w"] - 4, 0))}" '
                    f'height="{_n(max(lb["h"] - 4, 0))}" rx="3"/>')
        body.append(f'<text class="{cls}" x="{_n(r(lb["x"] + lb["w"] / 2))}" y="{_n(r(lb["y"] + lb["h"] / 2 + BASELINE))}" '
                    f'text-anchor="middle"{_attrs(ref, k)}>{esc(lb["text"])}</text>')

    head = [f'<text class="title" x="{_n(HEADER_PAD)}" y="{_n(HEADER_PAD)}">{esc(title)}</text>']
    if sub:
        head.append(f'<text class="subtitle" x="{_n(HEADER_PAD)}" y="{_n(HEADER_PAD + 24)}">{esc(sub)}</text>')
    return (f'<svg class="flow" viewBox="0 0 {_n(width)} {_n(height)}" width="{_n(width)}" height="{_n(height)}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title><style>{CSS}</style>{_markers()}'
            f'<rect class="bg" x="0" y="0" width="{_n(width)}" height="{_n(height)}"/>'
            + "".join(head) + f'<g transform="translate({_n(dx)} {_n(band)})">' + "".join(body) + "</g></svg>")
