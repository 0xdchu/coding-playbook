#!/usr/bin/env python3
"""The layout contract every layout module returns, text measuring, and the geometry gates run on the drawn coordinates.

A layout is a dict:

    {"width": float, "height": float,
     "shapes": [{"id": str, "kind": "actor" | "lifeline" | "node" | "frame", "shape": "box" | "start" | "end" | "decision",
                 "x": float, "y": float, "w": float, "h": float, "label": str, "sublabel": str | None,
                 "ref": str,               # participant or node id; a frame's fragment JSON path
                 "emphasis": bool}],
     "routes": [{"id": str, "ref": str,    # the step's or link's JSON path
                 "from": str, "to": str,   # shape ids it joins (a self-call joins one shape to itself)
                 "points": [[x, y], ...],  # orthogonal polyline, first point on the source, last on the target
                 "style": "solid" | "dashed" | "unproven", "head": "filled" | "open" | "none",
                 "emphasis": bool, "back": bool}],
     "labels": [{"id": str, "owner": str,  # the route or frame id it names
                 "text": str, "x": float, "y": float, "w": float, "h": float}]}

Lifelines are shapes of kind "lifeline" (w may be 0); routes may cross them and they are not obstacles. Frames are not
obstacles either. Coordinates are rounded with r() so the same input gives the same bytes.
"""

FONT = 13.0
LABEL_PAD_X = 6.0
LABEL_H = 18.0
# Width of a character as a fraction of the font size, for a common sans-serif. Unknown characters count as 'n'.
_NARROW = set("iljI.,:;'|!()[]{}` ")
_SEMI = set("frtJ1-\"*/\\")
_WIDE = set("mwMW@%&")
_CAPS = set("ABCDEFGHKLNOPQRSTUVXYZ")


def r(v):
    """Round to 0.5 px."""
    return round(v * 2) / 2


def text_width(text, size=FONT):
    total = 0.0
    for ch in text or "":
        if ch in _NARROW:
            total += 0.30
        elif ch in _SEMI:
            total += 0.40
        elif ch in _WIDE:
            total += 0.88
        elif ch in _CAPS:
            total += 0.68
        elif ord(ch) > 0x2E80:   # CJK and wide symbols
            total += 1.0
        else:
            total += 0.56
    return total * size


def label_box(text, cx, bottom, size=FONT):
    """A label box centred on cx whose bottom edge sits at bottom (so it sits above a route at that y)."""
    w = text_width(text, size) + 2 * LABEL_PAD_X
    return {"x": r(cx - w / 2), "y": r(bottom - LABEL_H), "w": r(w), "h": LABEL_H}


def _rect(o, pad=0.0):
    return (o["x"] - pad, o["y"] - pad, o["x"] + o["w"] + pad, o["y"] + o["h"] + pad)


def rects_overlap(a, b, pad=0.0):
    ax1, ay1, ax2, ay2 = _rect(a, pad)
    bx1, by1, bx2, by2 = _rect(b)
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


def segment_hits_rect(p, q, rect, pad=0.0):
    """True when the axis-aligned segment p-q passes through the inside of rect (shrunk by pad)."""
    x1, y1, x2, y2 = _rect(rect, -pad)
    if x1 >= x2 or y1 >= y2:
        return False
    sx1, sx2 = sorted((p[0], q[0]))
    sy1, sy2 = sorted((p[1], q[1]))
    return sx1 < x2 and sx2 > x1 and sy1 < y2 and sy2 > y1


def segments(points):
    return list(zip(points, points[1:]))


def _cross(a, b):
    """True when two axis-aligned segments cross at a point inside both (not at an end)."""
    (p1, p2), (q1, q2) = a, b
    a_h, b_h = p1[1] == p2[1], q1[1] == q2[1]
    if a_h == b_h:
        return False
    (h1, h2), (v1, v2) = (a, b) if a_h else (b, a)
    hx1, hx2 = sorted((h1[0], h2[0]))
    vy1, vy2 = sorted((v1[1], v2[1]))
    return hx1 < v1[0] < hx2 and vy1 < h1[1] < vy2


def check(layout):
    """Geometry diagnostics for a layout: errors for a route through a shape that is not its end and for labels that
    overlap each other, a shape or a route they do not name; an info line with the crossing count."""
    out = []
    solid = [s for s in layout["shapes"] if s["kind"] in ("actor", "node")]
    for route in layout["routes"]:
        ends = {route["from"], route["to"]}
        for seg in segments(route["points"]):
            for s in solid:
                if s["id"] in ends:
                    continue
                if segment_hits_rect(seg[0], seg[1], s, pad=1.0):
                    out.append({"severity": "error", "rule": "route-through-node", "path": route["ref"],
                                "message": f"route {route['id']} passes through '{s['label']}'"})
                    break
    labels = layout["labels"]
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            if rects_overlap(a, b):
                out.append({"severity": "error", "rule": "label-overlap", "path": a["owner"],
                            "message": f"label '{a['text']}' overlaps label '{b['text']}'"})
        for s in solid:
            if rects_overlap(a, s):
                out.append({"severity": "error", "rule": "label-overlap", "path": a["owner"],
                            "message": f"label '{a['text']}' overlaps '{s['label']}'"})
        for route in layout["routes"]:
            if route["id"] == a["owner"]:
                continue
            for seg in segments(route["points"]):
                if segment_hits_rect(seg[0], seg[1], a, pad=1.0):
                    out.append({"severity": "error", "rule": "label-overlap", "path": a["owner"],
                                "message": f"label '{a['text']}' lies on route {route['id']}"})
                    break
    crossings = 0
    routes = layout["routes"]
    for i, a in enumerate(routes):
        for b in routes[i + 1:]:
            crossings += sum(_cross(sa, sb) for sa in segments(a["points"]) for sb in segments(b["points"]))
    out.append({"severity": "info", "rule": "crossings", "path": "", "message": f"{crossings} route crossing(s)"})
    return out


def self_test():
    problems = []
    box = {"x": 100, "y": 100, "w": 50, "h": 40}
    if not segment_hits_rect([80, 120], [200, 120], box):
        problems.append("horizontal segment through a box not detected")
    if segment_hits_rect([80, 90], [200, 90], box):
        problems.append("segment above a box reported")
    if segment_hits_rect([100, 120], [60, 120], box, pad=1.0):
        problems.append("segment ending on the box edge reported")
    if not rects_overlap({"x": 0, "y": 0, "w": 10, "h": 10}, {"x": 5, "y": 5, "w": 10, "h": 10}):
        problems.append("overlap not detected")
    if rects_overlap({"x": 0, "y": 0, "w": 10, "h": 10}, {"x": 10, "y": 0, "w": 10, "h": 10}):
        problems.append("touching boxes reported as overlapping")
    if not _cross(([0, 5], [10, 5]), ([5, 0], [5, 10])) or _cross(([0, 5], [10, 5]), ([10, 0], [10, 10])):
        problems.append("crossing test wrong")
    if not (text_width("mmmm") > text_width("iiii") > 0):
        problems.append("text widths not ordered")
    lay = {"width": 400, "height": 300,
           "shapes": [{"id": "a", "kind": "node", "x": 0, "y": 0, "w": 60, "h": 30, "label": "A"},
                      {"id": "b", "kind": "node", "x": 200, "y": 0, "w": 60, "h": 30, "label": "B"},
                      {"id": "c", "kind": "node", "x": 100, "y": 0, "w": 60, "h": 30, "label": "C"}],
           "routes": [{"id": "r1", "ref": "links[0]", "from": "a", "to": "b", "points": [[60, 15], [200, 15]]}],
           "labels": [{"id": "l1", "owner": "r1", "text": "x", "x": 300, "y": 100, "w": 20, "h": 18},
                      {"id": "l2", "owner": "r1", "text": "y", "x": 305, "y": 105, "w": 20, "h": 18}]}
    rules = [d["rule"] for d in check(lay) if d["severity"] == "error"]
    if rules.count("route-through-node") != 1 or rules.count("label-overlap") != 1:
        problems.append(f"check() rules wrong: {rules}")
    over_node = dict(lay, labels=[{"id": "l3", "owner": "r1", "text": "z", "x": 110, "y": 5, "w": 20, "h": 18}],
                     shapes=lay["shapes"][:2] + [{"id": "c", "kind": "node", "x": 100, "y": 0, "w": 60, "h": 30,
                                                  "label": "C"}], routes=[])
    if [d["rule"] for d in check(over_node) if d["severity"] == "error"] != ["label-overlap"]:
        problems.append("a label over a node is not reported")
    on_route = dict(lay, shapes=lay["shapes"][:2],
                    routes=lay["routes"] + [{"id": "r2", "ref": "links[1]", "from": "a", "to": "b",
                                             "points": [[60, 60], [200, 60]]}],
                    labels=[{"id": "l4", "owner": "r2", "text": "w", "x": 120, "y": 6, "w": 20, "h": 18}])
    if [d["rule"] for d in check(on_route) if d["severity"] == "error"] != ["label-overlap"]:
        problems.append("a label lying on a route it does not name is not reported")
    lay["shapes"].pop()
    lay["labels"].pop()
    if [d for d in check(lay) if d["severity"] == "error"]:
        problems.append("clean layout reported errors")
    return problems


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--self-test"]:
        found = self_test()
        print("FAIL\n" + "\n".join(found) if found else "PASS: graph_geometry self-test")
        sys.exit(1 if found else 0)
    print("usage: graph_geometry.py --self-test", file=sys.stderr)
    sys.exit(2)
