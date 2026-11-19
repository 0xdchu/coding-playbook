#!/usr/bin/env python3
"""Sequence layout: a validated sequence Diagram in, the layout dict of graph_geometry.py out.

    layout(diagram, strict_sources=False) -> dict

The diagram must already have passed graph_validate.validate() (it sets Step.shown, Fragment.shown, Step.edge and
Step.reply). The look is a numbered "User Flow" sequence: compact actor boxes in a row at the top, dashed lifelines
down, one row per step, the label "N. text" centred just above its arrow. Column spacing is computed from the labels
(a step's label must fit between its two lifelines), never fixed. Everything is deterministic and rounded with r().

A fragment header is two labels: the name (on the tab, id "label:frame:N") and the condition ("label:frame:N:branch-cond",
text "[...]"), which starts at least 8 px right of the tab graph_svg draws. "back" is False on every route (a sequence
has no back edges); an arrow that points left is told from its points.

    python3 graph_sequence.py --self-test   lays out ../tests/valid/sequence-*.json and ../tests/sequence/*.json
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_geometry as geo  # noqa: E402
import graph_ir as ir  # noqa: E402
import graph_validate as val  # noqa: E402
from graph_geometry import LABEL_H, LABEL_PAD_X, label_box, r, text_width  # noqa: E402

TESTS = Path(__file__).resolve().parent.parent / "tests"

MARGIN = 40.0         # canvas margin on every side
BOX_H = 44.0
BOX_MIN_W = 120.0
BOX_FONT = 14.0
BOX_PAD = 40.0        # actor box width = label + BOX_PAD
BOX_GAP = 32.0        # minimum space between two adjacent actor boxes
SPAN_PAD = 40.0       # a step's label plus this must fit between its two lifelines
LOOP_W = 36.0         # a self-call loop: 36 wide, 24 tall
LOOP_H = 24.0
SELF_LABEL_X = 44.0   # a self-call label starts this far right of its lifeline
SELF_LABEL_GAP = 24.0  # and ends at least this far before the next lifeline
CALL_PITCH = 48.0
CALL_ARROW = 34.0     # arrow y below the top of its band (the label sits above it)
SELF_PITCH = 60.0
SELF_LOOP_TOP = 18.0
RETURN_PITCH = 36.0
RETURN_ARROW = 20.0
LABEL_GAP = 4.0       # label bottom above its arrow
FRAME_PAD = 24.0      # frame beyond the outermost lifeline it touches
FRAME_INSET = 8.0     # a nested frame sits at least this far inside its parent
FRAME_HEADER = 28.0
FRAME_FOOT = 12.0
FRAME_AFTER = 8.0     # space after a frame before whatever follows
FRAME_LABEL_X = 6.0
TAB_SCALE = 1.12      # graph_svg draws the fragment-name tab this wide: label x + pad + name * TAB_SCALE + TAB_END
TAB_END = 8.0
COND_GAP = 8.0        # the condition text starts at least this far right of the tab
DIVIDER_ABOVE = 10.0  # branch divider below the previous row
BRANCH_ROW = 26.0     # the branch label row under a divider (label 4 below the line)
TAIL = 16.0           # lifeline beyond the last row


def _ceil_half(v):
    return math.ceil(v * 2) / 2


def _step_text(step):
    return f"{step.shown}. {step.label}"


class _Frame:
    """What a fragment needs to know about the columns: the lifelines it touches and the least width its labels need."""

    def __init__(self, frag):
        self.frag = frag
        self.kids = []
        self.steps = []
        self.lo = self.hi = None
        self.tab, self.cond = _head_boxes(frag, 0.0)
        head_end = (self.cond or self.tab)["x"] + (self.cond or self.tab)["w"]
        texts = [f"[{b.label}]" for b in (frag.branches or [])]
        self.minw = max([head_end] + [label_box(t, 0, 0)["w"] + FRAME_LABEL_X for t in texts]) + FRAME_LABEL_X
        self.range = None


def _head_boxes(frag, left):
    """The two label boxes of a fragment header for a frame whose left edge is at left: the tab (the fragment name; it
    covers the tab graph_svg draws) and the condition (None without one), whose text starts COND_GAP right of the tab."""
    tab_w = _ceil_half(LABEL_PAD_X + TAB_SCALE * text_width(frag.fragment) + TAB_END)
    tab = {"x": r(left + FRAME_LABEL_X), "w": tab_w, "text": frag.fragment}
    sub = _sublabel(frag)
    cond = None
    if sub:
        text = f"[{sub}]"
        cond = {"x": r(left + FRAME_LABEL_X + tab_w + COND_GAP - LABEL_PAD_X), "w": label_box(text, 0, 0)["w"],
                "text": text}
    return tab, cond


def _sublabel(frag):
    if frag.label:
        return frag.label
    if frag.branches:
        return frag.branches[0].label
    return None


def layout(diagram, strict_sources=False):
    parts = diagram.participants
    n = len(parts)
    index = {p.id: i for i, p in enumerate(parts)}
    external = {p.id: p.external for p in parts}

    # ---- columns -------------------------------------------------------------------------------------------------
    widths = []
    for p in parts:
        w = max(BOX_MIN_W, text_width(p.label, BOX_FONT) + BOX_PAD)
        widths.append(2.0 * math.ceil(w / 2))        # even, so box edges stay on the 0.5 grid
    gaps = [_ceil_half((widths[i] + widths[i + 1]) / 2 + BOX_GAP) for i in range(n - 1)]

    label_w = {}
    wants = []       # (span start, span end, needed centre distance)
    frames = {}      # id(fragment) -> _Frame
    order = []       # frames in drawing order

    def build(frag):
        fr = _Frame(frag)
        frames[id(frag)] = fr
        order.append(fr)
        for it in frag.children():
            if isinstance(it, ir.Fragment):
                kid = build(it)
                fr.kids.append(kid)
                lo, hi = kid.lo, kid.hi
            else:
                fr.steps.append(it)
                lo, hi = sorted((index[it.frm], index[it.to]))
            fr.lo = lo if fr.lo is None else min(fr.lo, lo)
            fr.hi = hi if fr.hi is None else max(fr.hi, hi)
        return fr

    for it in ir.walk_steps(diagram.steps):
        if isinstance(it, ir.Step):
            label_w[id(it)] = label_box(_step_text(it), 0, 0)["w"]
            i, j = sorted((index[it.frm], index[it.to]))
            if it.kind == "self":
                if i + 1 < n:
                    wants.append((i, i + 1, SELF_LABEL_X + label_w[id(it)] + SELF_LABEL_GAP))
            else:
                wants.append((i, j, label_w[id(it)] + SPAN_PAD))
    for it in diagram.steps:
        if isinstance(it, ir.Fragment):
            build(it)

    for i, j, need in sorted(wants, key=lambda t: (t[1] - t[0], t[0], t[2])):
        have = sum(gaps[i:j])
        if have < need:
            add = _ceil_half((need - have) / (j - i))
            for k in range(i, j):
                gaps[k] += add

    def centres():
        c = [MARGIN + widths[0] / 2]
        for g in gaps:
            c.append(c[-1] + g)
        return c

    def frame_range(fr, c):
        left, right = c[fr.lo] - FRAME_PAD, c[fr.hi] + FRAME_PAD
        for s in fr.steps:
            if s.kind == "self":
                right = max(right, c[index[s.frm]] + SELF_LABEL_X + label_w[id(s)] + FRAME_INSET)
        for k in fr.kids:
            kl, kr = frame_range(k, c)
            left, right = min(left, kl - FRAME_INSET), max(right, kr + FRAME_INSET)
        right = max(right, left + fr.minw)
        fr.range = (left, right)
        return fr.range

    # a frame must not run over a lifeline it does not touch (its header label can be wider than its lifelines)
    for _ in range(500):
        c = centres()
        changed = False
        for fr in order:
            left, right = frame_range(fr, c)
            if fr.hi + 1 < n and right > c[fr.hi + 1] - FRAME_INSET - 4:
                gaps[fr.hi] += _ceil_half(right - (c[fr.hi + 1] - FRAME_INSET - 4))
                changed = True
                break
            if fr.lo > 0 and left < c[fr.lo - 1] + FRAME_INSET + 4:
                gaps[fr.lo - 1] += _ceil_half(c[fr.lo - 1] + FRAME_INSET + 4 - left)
                changed = True
                break
        if not changed:
            break
    c = centres()
    for fr in order:
        frame_range(fr, c)
    shift = max([0.0] + [MARGIN - fr.range[0] for fr in order])
    c = [x + shift for x in c]
    for fr in order:
        frame_range(fr, c)

    # ---- rows ----------------------------------------------------------------------------------------------------
    box_bottom = MARGIN + BOX_H
    shapes_frames, routes, labels = [], [], []

    def route_style(step):
        edge = step.edge
        if edge is not None:
            if edge.provenance == "heuristic":
                return "unproven"
            # the plan: an edge that starts at an internal participant and cites nothing is unproven (with a repo root)
            if strict_sources and not edge.sources and not step.external and not external[edge.frm]:
                return "unproven"
        if step.kind in ("async", "reply") or (step.reply and step.kind != "call-return"):
            return "dashed"
        return "solid"

    def emit_step(step, cur):
        x1, x2 = c[index[step.frm]], c[index[step.to]]
        sid = f"step:{step.shown}"
        a_from, a_to = f"actor:{step.frm}", f"actor:{step.to}"
        style = route_style(step)
        dashed = step.kind in ("async", "reply") or (step.reply and step.kind != "call-return")
        head = "open" if dashed else "filled"
        text = _step_text(step)
        if step.kind == "self":
            y = cur + SELF_LOOP_TOP
            pts = [[r(x1), r(y)], [r(x1 + LOOP_W), r(y)], [r(x1 + LOOP_W), r(y + LOOP_H)], [r(x1), r(y + LOOP_H)]]
            routes.append({"id": sid, "ref": step.at, "from": a_from, "to": a_to, "points": pts, "style": style,
                           "head": head, "emphasis": step.emphasis, "back": False})
            box = label_box(text, 0, 0)
            labels.append({"id": f"label:{sid}", "owner": sid, "text": text, "x": r(x1 + SELF_LABEL_X),
                           "y": r(y + LOOP_H / 2 - LABEL_H / 2), "w": box["w"], "h": box["h"]})
            return cur + SELF_PITCH
        y = cur + CALL_ARROW
        routes.append({"id": sid, "ref": step.at, "from": a_from, "to": a_to,
                       "points": [[r(x1), r(y)], [r(x2), r(y)]], "style": style, "head": head,
                       "emphasis": step.emphasis, "back": False})
        box = label_box(text, (x1 + x2) / 2, y - LABEL_GAP)
        labels.append({"id": f"label:{sid}", "owner": sid, "text": text, "x": box["x"], "y": box["y"],
                       "w": box["w"], "h": box["h"]})
        cur += CALL_PITCH
        if step.kind == "call-return":
            y2 = cur + RETURN_ARROW
            routes.append({"id": f"{sid}:return", "ref": step.at, "from": a_to, "to": a_from,
                           "points": [[r(x2), r(y2)], [r(x1), r(y2)]], "style": "dashed", "head": "open",
                           "emphasis": step.emphasis, "back": False})
            cur += RETURN_PITCH
        return cur

    def frame_label(fid, text, left, top, owner_suffix=""):
        box = label_box(text, 0, 0)
        labels.append({"id": f"label:{fid}{owner_suffix}", "owner": fid, "text": text, "x": r(left + FRAME_LABEL_X),
                       "y": r(top), "w": box["w"], "h": box["h"]})

    def emit_items(items, cur):
        for it in items:
            cur = emit_fragment(it, cur) if isinstance(it, ir.Fragment) else emit_step(it, cur)
        return cur

    def emit_fragment(frag, cur):
        fr = frames[id(frag)]
        left, right = fr.range
        fid = f"frame:{frag.shown}"
        top = cur
        shape = {"id": fid, "kind": "frame", "shape": "box", "x": r(left), "y": r(top), "w": r(right - left), "h": 0,
                 "label": frag.fragment, "sublabel": _sublabel(frag), "ref": frag.at, "emphasis": False,
                 "dividers": []}
        shapes_frames.append(shape)
        tab, cond = _head_boxes(frag, left)
        labels.append({"id": f"label:{fid}", "owner": fid, "text": tab["text"], "x": tab["x"], "y": r(top + 5),
                       "w": tab["w"], "h": LABEL_H})
        if cond:
            # the id carries ":branch" so graph_svg draws it as plain condition text, not as a second tab
            labels.append({"id": f"label:{fid}:branch-cond", "owner": fid, "text": cond["text"], "x": cond["x"],
                           "y": r(top + 5), "w": cond["w"], "h": LABEL_H})
        cur += FRAME_HEADER
        if frag.branches is not None:
            for bi, branch in enumerate(frag.branches):
                if bi > 0:
                    dy = cur + DIVIDER_ABOVE
                    shape["dividers"].append(r(dy))
                    frame_label(fid, f"[{branch.label}]", left, dy + 4, f":branch{bi}")
                    cur = dy + BRANCH_ROW - 4
                elif frag.label:
                    frame_label(fid, f"[{branch.label}]", left, cur + 4, ":branch0")
                    cur += BRANCH_ROW
                cur = emit_items(branch.steps, cur)
        else:
            cur = emit_items(frag.steps, cur)
        bottom = cur + FRAME_FOOT
        shape["h"] = r(bottom - top)
        return bottom + FRAME_AFTER

    end = emit_items(diagram.steps, box_bottom)
    life_bottom = end + TAIL

    # ---- shapes and canvas ---------------------------------------------------------------------------------------
    actors, lifelines = [], []
    for i, p in enumerate(parts):
        actors.append({"id": f"actor:{p.id}", "kind": "actor", "shape": "box", "x": r(c[i] - widths[i] / 2),
                       "y": r(MARGIN), "w": r(widths[i]), "h": r(BOX_H), "label": p.label, "sublabel": None,
                       "ref": p.id, "emphasis": False})
        lifelines.append({"id": f"lifeline:{p.id}", "kind": "lifeline", "shape": "box", "x": r(c[i]),
                          "y": r(box_bottom), "w": 0, "h": r(life_bottom - box_bottom), "label": p.label,
                          "sublabel": None, "ref": p.id, "emphasis": False})
    shapes = shapes_frames + lifelines + actors
    right_edge = max([s["x"] + s["w"] for s in shapes]
                     + [lb["x"] + lb["w"] for lb in labels]
                     + [pt[0] for rt in routes for pt in rt["points"]])
    return {"width": r(right_edge + MARGIN), "height": r(life_bottom + MARGIN),
            "shapes": shapes, "routes": routes, "labels": labels}


# ---------------------------------------------------------------------------------------------------------------------
# self-test


def _load(path):
    d, diags = val.load(path)
    errors = [x for x in diags if x["severity"] == "error"]
    return d, errors


def _contains(frame, x, y, w=0.0, h=0.0):
    return (frame["x"] <= x and x + w <= frame["x"] + frame["w"]
            and frame["y"] <= y and y + h <= frame["y"] + frame["h"])


def _verify(name, d, lay):
    """Structural problems of one layout, as a list of messages."""
    bad = []
    add = lambda m: bad.append(f"{name}: {m}")
    again = layout(d)
    if json.dumps(lay, sort_keys=True) != json.dumps(again, sort_keys=True):
        add("layout is not deterministic")
    for dg in geo.check(lay):
        if dg["severity"] == "error":
            add(f"geometry {dg['rule']}: {dg['message']}")
    ys = [rt["points"][0][1] for rt in lay["routes"]]
    if any(b <= a for a, b in zip(ys, ys[1:])):
        add(f"rows do not strictly increase: {ys}")
    W, H = lay["width"], lay["height"]
    for rt in lay["routes"]:
        for x, y in rt["points"]:
            if not (0 <= x <= W and 0 <= y <= H):
                add(f"point of {rt['id']} outside the canvas")
    for lb in lay["labels"]:
        if not _contains({"x": 0, "y": 0, "w": W, "h": H}, lb["x"], lb["y"], lb["w"], lb["h"]):
            add(f"label '{lb['text']}' outside the canvas")
    shapes = {s["id"]: s for s in lay["shapes"]}
    routes = {rt["id"]: rt for rt in lay["routes"]}
    for rt in lay["routes"]:
        if rt["from"] not in shapes or rt["to"] not in shapes:
            add(f"route {rt['id']} names a missing shape")
    for s in lay["shapes"]:
        if s["kind"] != "frame" and not (0 <= s["x"] and s["x"] + s["w"] <= W and 0 <= s["y"] + s["h"] <= H):
            add(f"shape {s['id']} outside the canvas")
        if s["kind"] == "frame" and not (0 <= s["x"] and s["x"] + s["w"] <= W and 0 <= s["y"] and s["y"] + s["h"] <= H):
            add(f"frame {s['id']} outside the canvas")
    actors = sorted((s for s in lay["shapes"] if s["kind"] == "actor"), key=lambda s: s["x"])
    for a, b in zip(actors, actors[1:]):
        if b["x"] - (a["x"] + a["w"]) < 32:
            add(f"actors {a['label']} and {b['label']} are {b['x'] - (a['x'] + a['w'])} apart (< 32)")
    lifeline_x = {s["ref"]: s["x"] for s in lay["shapes"] if s["kind"] == "lifeline"}
    walked = list(ir.walk_steps(d.steps))
    steps = [it for it in walked if isinstance(it, ir.Step)]
    if [rt["id"] for rt in lay["routes"] if not rt["id"].endswith(":return")] != [f"step:{s.shown}" for s in steps]:
        add("routes are not one per step in drawing order")
    for s in steps:
        rt = routes.get(f"step:{s.shown}")
        if rt is None:
            continue
        if rt["ref"] != s.at:
            add(f"route {rt['id']} ref {rt['ref']} != {s.at}")
        lb = [x for x in lay["labels"] if x["owner"] == rt["id"]]
        if len(lb) != 1 or lb[0]["text"] != f"{s.shown}. {s.label}":
            add(f"step {s.shown} does not have exactly one label '{s.shown}. {s.label}'")
            continue
        if s.kind != "self":
            lo, hi = sorted((lifeline_x[s.frm], lifeline_x[s.to]))
            if lb[0]["x"] < lo + 20 or lb[0]["x"] + lb[0]["w"] > hi - 20:
                add(f"label of step {s.shown} does not fit between its lifelines with 20 px each side")
            if lb[0]["y"] + lb[0]["h"] != rt["points"][0][1] - 4:
                add(f"label of step {s.shown} is not 4 px above its arrow")
        else:
            if lb[0]["x"] <= rt["points"][1][0]:
                add(f"self-call label {s.shown} is not right of its loop")
            own = lifeline_x[s.frm]
            for pid, lx in lifeline_x.items():
                if pid != s.frm and lb[0]["x"] - 4 <= lx <= lb[0]["x"] + lb[0]["w"] + 4:
                    add(f"self-call label {s.shown} lies over the lifeline of {pid}")
                elif lx > own and lx - (lb[0]["x"] + lb[0]["w"]) < 20:
                    add(f"self-call label {s.shown} ends {lx - (lb[0]['x'] + lb[0]['w'])} before the next lifeline (< 20)")
        ret = routes.get(f"step:{s.shown}:return")
        if (s.kind == "call-return") != (ret is not None):
            add(f"step {s.shown} ({s.kind}) has the wrong number of routes")
        if ret is not None and (ret["points"][0][1] <= rt["points"][0][1] or ret["style"] != "dashed"
                                or ret["from"] != rt["to"] or ret["to"] != rt["from"]
                                or [x for x in lay["labels"] if x["owner"] == ret["id"]]):
            add(f"return of step {s.shown} is wrong")
    for it in walked:
        if not isinstance(it, ir.Fragment):
            continue
        fid = f"frame:{it.shown}"
        fr = shapes.get(fid)
        if fr is None or fr["kind"] != "frame" or fr["ref"] != it.at:
            add(f"missing or wrong frame {fid}")
            continue
        inner = list(ir.walk_steps(it.children()))
        for s in (x for x in inner if isinstance(x, ir.Step)):
            for rid in (f"step:{s.shown}", f"step:{s.shown}:return"):
                rt = routes.get(rid)
                if rt is None:
                    continue
                for x, y in rt["points"]:
                    if not _contains(fr, x, y):
                        add(f"point of {rid} outside {fid}")
                for lb in (x for x in lay["labels"] if x["owner"] == rid):
                    if not _contains(fr, lb["x"], lb["y"], lb["w"], lb["h"]):
                        add(f"label of {rid} outside {fid}")
        for lb in (x for x in lay["labels"] if x["owner"] == fid):
            if not _contains(fr, lb["x"], lb["y"], lb["w"], lb["h"]):
                add(f"label '{lb['text']}' outside {fid}")
        touched = set()
        for x in inner:
            if isinstance(x, ir.Step):
                touched |= {x.frm, x.to}
        order = [p.id for p in d.participants]
        span = [order.index(t) for t in touched]
        for k, pid in enumerate(order):
            if not min(span) <= k <= max(span) and fr["x"] - 8 < lifeline_x[pid] < fr["x"] + fr["w"] + 8:
                add(f"{fid} runs over (or within 8 px of) the lifeline of {pid}, which lies outside the lifelines it spans")
        tab = [x for x in lay["labels"] if x["id"] == f"label:{fid}"]
        cond = [x for x in lay["labels"] if x["id"] == f"label:{fid}:branch-cond"]
        sub = it.label or (it.branches[0].label if it.branches else None)
        if len(tab) != 1 or tab[0]["text"] != it.fragment or len(cond) != (1 if sub else 0) \
                or (sub and cond[0]["text"] != f"[{sub}]"):
            add(f"{fid}: the header must be one tab label '{it.fragment}' and one condition label [{sub}]")
        elif cond:
            # graph_svg ends the tab at label x + 6 + 1.12 * name width + 8 and draws the condition text 6 px right of
            # its label's x: the text must start at least 8 px after the tab ends
            tab_end = tab[0]["x"] + 6 + 1.12 * text_width(it.fragment) + 8
            if cond[0]["x"] + 6 - tab_end < 8:
                add(f"{fid}: the condition starts {cond[0]['x'] + 6 - tab_end} after the tab (< 8)")
            if tab[0]["x"] + tab[0]["w"] < tab_end:
                add(f"{fid}: the tab label does not cover the drawn tab")
        for kid in (x for x in inner if isinstance(x, ir.Fragment)):
            k = shapes[f"frame:{kid.shown}"]
            ins = (k["x"] - fr["x"], k["y"] - fr["y"], fr["x"] + fr["w"] - k["x"] - k["w"],
                   fr["y"] + fr["h"] - k["y"] - k["h"])
            if min(ins) < 8:
                add(f"frame {k['id']} sits {min(ins)} inside {fid} (< 8)")
        if it.branches is not None and len(fr["dividers"]) != len(it.branches) - 1:
            add(f"frame {fid} has {len(fr['dividers'])} dividers for {len(it.branches)} branches")
        if any(b <= a for a, b in zip(fr["dividers"], fr["dividers"][1:])):
            add(f"dividers of {fid} do not increase")
        if not all(fr["y"] < dv < fr["y"] + fr["h"] for dv in fr["dividers"]):
            add(f"dividers of {fid} outside the frame")
    return bad


def _tiny():
    d, _ = ir.parse({"kind": "sequence", "title": "t",
                     "participants": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                     "edges": [{"from": "a", "to": "b"}],
                     "steps": [{"from": "a", "to": "b", "label": "go", "kind": "call-return"},
                               {"from": "b", "to": "b", "label": "think", "kind": "self"},
                               {"fragment": "loop", "label": "each", "steps": [
                                   {"from": "b", "to": "a", "label": "ping", "kind": "async"}]}]})
    val.validate(d)
    return d


def _selfcall():
    """A long self-call label on the first of two participants, nothing else wide: only the self-call rule can space them."""
    d, _ = ir.parse({"kind": "sequence", "title": "t",
                     "participants": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
                     "edges": [{"from": "a", "to": "b"}],
                     "steps": [{"from": "a", "to": "b", "label": "go"},
                               {"from": "a", "to": "a", "label": "a rather long self call label to think about", "kind": "self"}]})
    val.validate(d)
    return d


def self_test():
    problems = []
    files = sorted((TESTS / "valid").glob("sequence-*.json")) + sorted((TESTS / "sequence").glob("*.json"))
    extra = sorted((TESTS / "sequence").glob("*.json"))
    if len(extra) < 4 or not sorted((TESTS / "valid").glob("sequence-*.json")):
        problems.append(f"need >= 4 fixtures under {TESTS / 'sequence'} and the valid sequence fixtures")
    for f in files:
        d, errors = _load(f)
        if errors:
            problems.append(f"{f.name}: load errors {errors}")
            continue
        problems.extend(_verify(f.name, d, layout(d)))

    d = _selfcall()
    problems.extend(_verify("self-call spacing", d, layout(d)))
    lay = layout(d)
    lx = {x["ref"]: x["x"] for x in lay["shapes"] if x["kind"] == "lifeline"}
    lb = next(x for x in lay["labels"] if x["text"].endswith("think about"))
    if lx["b"] - (lb["x"] + lb["w"]) < 24:
        problems.append(f"self-call label ends {lx['b'] - (lb['x'] + lb['w'])} before the next lifeline (< 24)")

    # exact values on a tiny diagram, so a layout regression is caught
    lay = layout(_tiny())
    shapes = {s["id"]: s for s in lay["shapes"]}
    expect = [
        (lay["width"], 394.0), (lay["height"], 380.0),
        ((shapes["actor:a"]["x"], shapes["actor:a"]["y"], shapes["actor:a"]["w"], shapes["actor:a"]["h"]),
         (40.0, 40.0, 120.0, 44.0)),
        (shapes["actor:b"]["x"], 192.0),
        ((shapes["lifeline:a"]["x"], shapes["lifeline:a"]["y"], shapes["lifeline:a"]["h"]), (100.0, 84.0, 256.0)),
        ([rt["id"] for rt in lay["routes"]], ["step:1", "step:1:return", "step:2", "step:3.1"]),
        (lay["routes"][0]["points"], [[100.0, 118.0], [252.0, 118.0]]),
        ((lay["routes"][0]["style"], lay["routes"][0]["head"]), ("solid", "filled")),
        (lay["routes"][1]["points"], [[252.0, 152.0], [100.0, 152.0]]),
        ((lay["routes"][1]["style"], lay["routes"][1]["head"], lay["routes"][1]["back"]), ("dashed", "open", False)),
        (lay["routes"][2]["points"], [[252.0, 186.0], [288.0, 186.0], [288.0, 210.0], [252.0, 210.0]]),
        (lay["routes"][3]["points"], [[252.0, 290.0], [100.0, 290.0]]),
        ((lay["routes"][3]["style"], lay["routes"][3]["head"]), ("dashed", "open")),
        ((lay["labels"][0]["text"], lay["labels"][0]["x"], lay["labels"][0]["y"]), ("1. go", 156.0, 96.0)),
        ((lay["labels"][1]["text"], lay["labels"][1]["x"], lay["labels"][1]["y"]), ("2. think", 296.0, 189.0)),
        ((shapes["frame:3"]["x"], shapes["frame:3"]["y"], shapes["frame:3"]["w"], shapes["frame:3"]["h"]),
         (76.0, 228.0, 200.0, 88.0)),
        ((shapes["frame:3"]["label"], shapes["frame:3"]["sublabel"]), ("loop", "each")),
        ([lb["text"] for lb in lay["labels"] if lb["owner"] == "frame:3"], ["loop", "[each]"]),
    ]
    for got, want in expect:
        if got != want:
            problems.append(f"tiny diagram: got {got!r}, expected {want!r}")

    # a step is unproven when its edge is heuristic, and also when its edge starts at an internal participant and cites
    # no sources (also toward an external service: the call is in our code), but that second rule applies only with strict_sources=True (the caller gave a repo root, so sources can be
    # checked); without it a source-less edge is not marked. This is the specified behaviour.
    d, _ = _load(TESTS / "valid" / "sequence-basic.json")
    plain = {rt["id"]: rt["style"] for rt in layout(d)["routes"]}
    strict = {rt["id"]: (rt["style"], rt["head"]) for rt in layout(d, strict_sources=True)["routes"]}
    if "unproven" in plain.values():
        problems.append("sequence-basic: a step is unproven without strict_sources")
    if strict["step:5"] != ("unproven", "filled"):
        problems.append(f"sequence-basic: step 5 (api -> db, edge without sources) is {strict['step:5']}")
    if [k for k, v in strict.items() if v[0] == "unproven"] != ["step:2", "step:5", "step:6"]:
        problems.append(f"sequence-basic: unproven steps {[k for k, v in strict.items() if v[0] == 'unproven']}")
    d.edges[0].provenance = "heuristic"
    if {rt["id"]: rt["style"] for rt in layout(d)["routes"]}["step:5"] != "unproven":
        problems.append("a heuristic edge is not unproven without strict_sources")
    # styles
    d, _ = _load(TESTS / "valid" / "sequence-fragments.json")
    styles = {rt["id"]: (rt["style"], rt["head"]) for rt in layout(d)["routes"]}
    for rid, want in (("step:1", ("solid", "filled")), ("step:3.1", ("dashed", "open")),
                      ("step:3.3.1", ("solid", "filled")), ("step:3.3.1:return", ("dashed", "open"))):
        if styles.get(rid) != want:
            problems.append(f"sequence-fragments {rid}: {styles.get(rid)} != {want}")
    return problems


def main(argv):
    if argv == ["--self-test"]:
        found = self_test()
        print("FAIL\n" + "\n".join(found) if found else "PASS: graph_sequence self-test")
        return 1 if found else 0
    print("usage: graph_sequence.py --self-test (layout(diagram) is called by graph.py)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
