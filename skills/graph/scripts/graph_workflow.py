#!/usr/bin/env python3
"""Workflow layout: a deterministic layered flowchart, in the layout contract of graph_geometry.

    layout(diagram) -> layout dict        diagram: a graph_ir.Diagram of kind "workflow" that graph_validate passed

The steps, all deterministic:

1. Links to a node on the DFS stack (DFS from the start nodes, then from the first node, in declaration order) are back
   edges; the rest are forward links. Ranks are the longest path over forward links.
2. Nodes in a rank start in declaration order, then four barycentre sweeps (down, up, down, up) reorder them; ties
   break by declaration order.
3. Cross axis: the first forward outgoing link of a node pulls its target into the node's column when no node declared
   earlier has claimed that target (so the main path runs straight); the others sit at the mean of their parents,
   pushed apart by 40 px.
4. Rank axis: 48 px between ranks, wider where many links share a gap (each gets its own channel) or a label needs room;
   nodes of one rank share their top (direction down) or left edge (direction right). If a label fits nowhere, every
   gap and node gap grows by 16 px and the layout is redone.
5. Routes are orthogonal. Forward: bottom centre to top centre (a decision leaves by its bottom vertex, or its side
   vertex toward a target on that side); a link that would cross a node runs down a side channel instead. Back edges
   leave the right side, run in a channel beyond the nodes of the ranks they span and enter the target's right side.
6. Labels: a decision's branch labels sit on the first segment near the exit, a back edge's beside its channel, any
   other at the middle of the longest segment; a position that touches a shape, label or route is skipped.

direction "right" runs the same algorithm on swapped axes (ranks left to right, back edges below).

    python3 graph_workflow.py --self-test
    python3 graph_workflow.py --layout FILE.json     print the layout of a workflow IR file as JSON
"""
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_geometry as geo  # noqa: E402
import graph_ir as ir  # noqa: E402
import graph_validate as val  # noqa: E402
from graph_geometry import LABEL_H, LABEL_PAD_X, r, text_width  # noqa: E402

TESTS = Path(__file__).resolve().parent.parent / "tests"

MARGIN = 40.0
RANK_GAP = 48.0
NODE_GAP = 40.0
MAX_LINE = 220.0
MAX_LINE_DECISION = 150.0
LINE_H = 18.0
LANE_FIRST = 24.0      # first channel beyond the nodes of the spanned ranks
LANE_NEXT = 16.0       # each further channel
SLOT = 14.0            # room for one channel line in a gap
LABEL_SLOT = 24.0      # a channel line whose label sits above it
CLEAR = 6.0            # a route keeps this far from a node it does not join
SIDE_EXIT = 16.0       # a decision leaves sideways when its target is this far beyond the vertex
WIDEN = 16.0           # added to every gap per retry when a label fits nowhere
MAX_WIDEN = 40


def _even(v):
    """Round up to an even whole number, so half sizes and centres stay on 0.5 px."""
    n = int(v)
    n = n if n >= v else n + 1
    return float(n + n % 2)


def _wrap(text, maxw):
    """Greedy word wrap; a word wider than maxw is cut."""
    lines = []
    for para in (text or "").split("\n"):
        cur = ""
        for word in para.split():
            while text_width(word) > maxw and len(word) > 1:
                k = len(word) - 1
                while k > 1 and text_width(word[:k]) > maxw:
                    k -= 1
                if cur:
                    lines.append(cur)
                    cur = ""
                lines.append(word[:k])
                word = word[k:]
            trial = f"{cur} {word}" if cur else word
            if text_width(trial) <= maxw:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines


class _Node:
    def __init__(self, idx, node, horizontal):
        self.idx, self.node, self.id = idx, node, node.id
        decision = node.shape == "decision"
        maxw = MAX_LINE_DECISION if decision else MAX_LINE
        self.lines = _wrap(node.label, maxw) + _wrap(node.detail, maxw) or [node.label]
        widest = max(text_width(x) for x in self.lines)
        if decision:
            w = _even(widest + 70)
            h = _even(max(80.0, 0.6 * w + LINE_H * (len(self.lines) - 1)))
        else:
            w = _even(max(140.0, widest + 32))
            h = _even(22 + LINE_H * len(self.lines))
        self.w, self.h = w, h
        # cs: size across the ranks, ps: size along them
        self.cs, self.ps = (h, w) if horizontal else (w, h)
        self.rank = 0
        self.c = 0.0
        self.p = 0.0
        self.out, self.fwd_in, self.fwd_out = [], [], []
        self.first_out = None
        self.claim = None      # the forward link whose source this node's column follows

    def rect(self):
        return {"x": self.c - self.cs / 2, "y": self.p - self.ps / 2, "w": self.cs, "h": self.ps}


class _Link:
    def __init__(self, i, link, src, dst):
        self.i, self.link, self.src, self.dst = i, link, src, dst
        self.back = False
        self.cand = None


class _Flow:
    def __init__(self, d, extra=0.0):
        self.d = d
        self.rank_gap = RANK_GAP + extra
        self.node_gap = NODE_GAP + extra
        self.lane_next = LANE_NEXT + extra
        self.horizontal = d.direction == "right"
        self.nodes = [_Node(i, n, self.horizontal) for i, n in enumerate(d.nodes)]
        self.by_id = {}
        for n in self.nodes:
            self.by_id.setdefault(n.id, n)
        self.links = []
        for i, lk in enumerate(d.links):
            s, t = self.by_id.get(lk.frm), self.by_id.get(lk.to)
            if s is not None and t is not None and s is not t:
                link = _Link(i, lk, s, t)
                self.links.append(link)
                s.out.append(link)

    # ---- ranks and order ------------------------------------------------------------------------------------

    def _dfs(self):
        state, post = {}, []
        starts = [n for n in self.nodes if n.node.shape == "start"] or self.nodes[:1]
        for root in starts + self.nodes:
            if root in state:
                continue
            state[root] = 1
            stack = [(root, iter(root.out))]
            while stack:
                n, it = stack[-1]
                for lk in it:
                    t = lk.dst
                    if state.get(t) == 1:
                        lk.back = True
                    elif t not in state:
                        state[t] = 1
                        stack.append((t, iter(t.out)))
                        break
                else:
                    state[n] = 2
                    post.append(n)
                    stack.pop()
        for lk in self.links:
            if not lk.back:
                lk.src.fwd_out.append(lk)
                lk.dst.fwd_in.append(lk)
        for n in self.nodes:
            n.first_out = min(n.fwd_out, key=lambda x: x.i, default=None)
        for n in self.nodes:       # the node declared first claims the target of its first forward link
            lk = n.first_out
            if lk is not None and lk.dst.claim is None:
                lk.dst.claim = lk
        for n in reversed(post):
            for lk in n.fwd_out:
                lk.dst.rank = max(lk.dst.rank, n.rank + 1)

    def _order(self):
        count = max(n.rank for n in self.nodes) + 1
        self.ranks = [[n for n in self.nodes if n.rank == k] for k in range(count)]

        def sweep(ks, neighbours):
            for k in ks:
                bary = {}
                for n in self.ranks[k]:
                    near = neighbours(n)
                    bary[n] = (sum(Fraction(position[m]) for m in near) / len(near)) if near else Fraction(position[n])
                self.ranks[k].sort(key=lambda n: (bary[n], n.idx))
                for i, n in enumerate(self.ranks[k]):
                    position[n] = i

        position = {n: i for rank in self.ranks for i, n in enumerate(rank)}
        down = range(1, count)
        up = range(count - 2, -1, -1)
        for ks, near in ((down, lambda n: [x.src for x in n.fwd_in]), (up, lambda n: [x.dst for x in n.fwd_out]),
                         (down, lambda n: [x.src for x in n.fwd_in]), (up, lambda n: [x.dst for x in n.fwd_out])):
            sweep(ks, near)

    # ---- cross axis -----------------------------------------------------------------------------------------

    def _place_cross(self):
        for rank in self.ranks:
            want = []
            for n in rank:
                lk = n.claim
                if lk is not None:
                    want.append(lk.src.c)
                elif n.fwd_in:
                    want.append(r(sum(x.src.c for x in n.fwd_in) / len(n.fwd_in)))
                else:
                    want.append(None)
            sep = lambda i: rank[i - 1].cs / 2 + self.node_gap + rank[i].cs / 2
            x = []
            for i, w in enumerate(want):
                x.append(w if w is not None else (x[i - 1] + sep(i) if i else 0.0))
            anch = [n.claim is not None for n in rank]
            for _ in range(2 * len(rank) + 4):
                changed = False
                for i in range(1, len(rank)):
                    if x[i] < x[i - 1] + sep(i) and (not anch[i] or anch[i - 1]):
                        x[i] = x[i - 1] + sep(i)
                        changed = True
                for i in range(len(rank) - 2, -1, -1):
                    if x[i] > x[i + 1] - sep(i + 1) and not anch[i]:
                        x[i] = x[i + 1] - sep(i + 1)
                        changed = True
                if not changed:
                    break
            for i in range(1, len(rank)):
                x[i] = max(x[i], x[i - 1] + sep(i))
            for n, v in zip(rank, x):
                n.c = r(v)

    # ---- rank axis ------------------------------------------------------------------------------------------

    def _assign_p(self, gaps):
        """Set every node's p from the gap heights (gap k lies below rank k); return the start of each gap."""
        cursor, starts = 0.0, []
        for k, rank in enumerate(self.ranks):
            band = max(n.ps for n in rank)
            for n in rank:
                n.p = cursor + n.ps / 2
            cursor += band
            starts.append(cursor)
            cursor += gaps[k]
        return starts

    # ---- routes ---------------------------------------------------------------------------------------------

    def _lane(self, side, lo, hi):
        spanned = [n for n in self.nodes if lo <= n.rank <= hi]
        if side > 0:
            x = max(n.c + n.cs / 2 for n in spanned) + LANE_FIRST
        else:
            x = min(n.c - n.cs / 2 for n in spanned) - LANE_FIRST
        for sd, a, b, lx in self.lanes:
            if sd == side and a <= hi and lo <= b:
                x = max(x, lx + self.lane_next) if side > 0 else min(x, lx - self.lane_next)
        return x

    def _candidates(self, lk):
        s, t = lk.src, lk.dst
        out = []
        if lk.back:
            for sm, em in (("R", "R"), ("B", "R"), ("R", "T"), ("B", "T")):
                if em == "T" and t.rank == 0:
                    continue
                out.append(("B", sm, em, self._lane(1, t.rank, s.rank)))
            return out
        if s.node.shape == "decision":
            dc = t.c - s.c
            if abs(dc) >= s.cs / 2 + SIDE_EXIT:
                out.append(("D0", 1 if dc > 0 else -1))
        out.append(("F1", s.rank))
        if t.rank - 1 != s.rank and s.c != t.c:
            out.append(("F1", t.rank - 1))
        if t.rank - s.rank > 1:
            first = 1 if t.c >= s.c else -1
            for side in (first, -first):
                out.append(("F2", side, self._lane(side, s.rank, t.rank)))
        return out

    def _chan_gaps(self, lk, cand):
        """The gaps in which this route has a channel line."""
        s, t = lk.src, lk.dst
        if cand[0] == "F1":
            return [cand[1]] if s.c != t.c else []
        if cand[0] == "F2":
            return [s.rank, t.rank - 1]
        if cand[0] == "B":
            return ([s.rank] if cand[1] == "B" else []) + ([t.rank - 1] if cand[2] == "T" else [])
        return []

    def _points(self, lk, cand, chan):
        """The route in (cross, rank) coordinates."""
        s, t = lk.src, lk.dst
        top = (t.c, t.p - t.ps / 2)
        bottom = (s.c, s.p + s.ps / 2)
        kind = cand[0]
        if kind == "D0":
            return [(s.c + cand[1] * s.cs / 2, s.p), (t.c, s.p), top]
        if kind == "F1":
            if s.c == t.c:
                return [bottom, top]
            y = chan(cand[1], lk.i)
            return [bottom, (s.c, y), (t.c, y), top]
        if kind == "F2":
            x, y1, y2 = cand[2], chan(s.rank, lk.i), chan(t.rank - 1, lk.i)
            return [bottom, (s.c, y1), (x, y1), (x, y2), (t.c, y2), top]
        sm, em, x = cand[1], cand[2], cand[3]
        pts = [(s.c + s.cs / 2, s.p), (x, s.p)] if sm == "R" else [bottom, (s.c, chan(s.rank, lk.i)), (x, chan(s.rank, lk.i))]
        if em == "R":
            pts += [(x, t.p), (t.c + t.cs / 2, t.p)]
        else:
            y = chan(t.rank - 1, lk.i)
            pts += [(x, y), (t.c, y), top]
        return pts

    def _clear(self, pts, ends):
        for a, b in zip(pts, pts[1:]):
            for n in self.nodes:
                if geo.segment_hits_rect(a, b, n.rect(), 1.0 if n.id in ends else -CLEAR):
                    return False
        return True

    @staticmethod
    def _overlap(pts, other):
        """True when a segment of pts runs along a segment of other on the same line (compared at 0.5 px, as drawn)."""
        pts = [(r(x), r(y)) for x, y in pts]
        other = [(r(x), r(y)) for x, y in other]
        for a, b in zip(pts, pts[1:]):
            for c, d in zip(other, other[1:]):
                if a[0] == b[0] == c[0] == d[0] and min(max(a[1], b[1]), max(c[1], d[1])) > max(min(a[1], b[1]), min(c[1], d[1])):
                    return True
                if a[1] == b[1] == c[1] == d[1] and min(max(a[0], b[0]), max(c[0], d[0])) > max(min(a[0], b[0]), min(c[0], d[0])):
                    return True
        return False

    @staticmethod
    def _unrelated(a, b):
        return not ({a.src, a.dst} & {b.src, b.dst})

    @staticmethod
    def _key(cand):
        """A route shape without its lane position, which moves when other lanes do."""
        return cand[:3] if cand[0] == "B" else cand[:2]

    def _plan(self, banned):
        """Choose a route shape for every link; shapes depend on cross coordinates only. The first shape that clears
        every node and does not run along the route of an unrelated link (judged on nominal channel positions; run()
        judges the final ones and bans a shape that overlaps) wins; failing that, the first that clears every node;
        failing that, the first. A banned shape (lk.i, key) comes after every other."""
        count = len(self.ranks)
        starts = self._assign_p([self.rank_gap] * count)
        nominal = lambda g, key: starts[g] + 8 + (key % 5) * 6
        self.lanes = []
        planned = []
        for lk in self.links:
            cands = self._candidates(lk)
            pts = {id(c): self._points(lk, c, nominal) for c in cands}
            clear = [c for c in cands if self._clear(pts[id(c)], {lk.src.id, lk.dst.id})]
            free = [c for c in clear if not any(self._unrelated(o, lk) and self._overlap(pts[id(c)], op)
                                                for o, op in planned)]
            ok = lambda group: [c for c in group if (lk.i, self._key(c)) not in banned]
            chosen = (ok(free) or ok(clear) or free or clear or cands)[0]
            lk.cand = chosen
            planned.append((lk, self._points(lk, chosen, nominal)))
            if chosen[0] == "F2":
                self.lanes.append((chosen[1], lk.src.rank, lk.dst.rank, chosen[2]))
            elif chosen[0] == "B":
                self.lanes.append((1, lk.dst.rank, lk.src.rank, chosen[3]))

    def _overlapping(self, chan):
        """Every pair of links with no node in common whose final routes run along one line."""
        pts = {lk.i: self._points(lk, lk.cand, chan) for lk in self.links}
        return [(a, b) for i, a in enumerate(self.links) for b in self.links[i + 1:]
                if self._unrelated(a, b) and self._overlap(pts[a.i], pts[b.i])]

    def _label_size(self, lk):
        return text_width(lk.link.label) + 2 * LABEL_PAD_X, LABEL_H

    def _ordered(self, g, users):
        """The links of gap g from the top channel down. A link that leaves its source by the bottom in a column goes
        above a link that enters its target from the top in the same column, so their verticals do not overlap."""
        stem = {lk.i: lk.src.c for lk in users if lk.src.rank == g or lk.cand[0] == "F1"}
        entry = {lk.i: lk.dst.c for lk in users if lk.dst.rank - 1 == g}
        before = {lk.i: [o for o in users if o is not lk and o.i in stem and lk.i in entry and stem[o.i] == entry[lk.i]]
                  for lk in users}
        out, left = [], list(users)
        while left:
            pick = next((lk for lk in left if not [o for o in before[lk.i] if o in left]), left[0])
            out.append(pick)
            left.remove(pick)
        return out

    def _final_p(self):
        """Gap heights from the channels each gap carries; returns a channel resolver."""
        count = len(self.ranks)
        users = {g: [] for g in range(count)}
        for lk in self.links:
            for g in self._chan_gaps(lk, lk.cand):
                users[g].append(lk)
        minimum = {g: self.rank_gap for g in range(count)}
        if self.horizontal:
            for lk in self.links:
                if not lk.back and lk.link.label and lk.dst.rank == lk.src.rank + 1:
                    minimum[lk.src.rank] = max(minimum[lk.src.rank], _even(self._label_size(lk)[0] + 16))
        offset, heights = {}, {}
        for g in range(count):
            cursor = 8.0
            for lk in self._ordered(g, users[g]):
                if lk.link.label and self.horizontal:
                    size = _even(self._label_size(lk)[0] + 20)
                    offset[(g, lk.i)] = cursor + 8
                else:
                    size = LABEL_SLOT if lk.link.label else SLOT
                    offset[(g, lk.i)] = cursor + size
                cursor += size
            heights[g] = max(minimum[g], cursor + 8) if g < count - 1 else (cursor + 8 if users[g] else 0.0)
        starts = self._assign_p([heights[g] for g in range(count)])
        return lambda g, key: starts[g] + offset[(g, key)]

    # ---- labels ---------------------------------------------------------------------------------------------

    def _fits(self, box, shapes, labels, routes):
        for s in shapes:
            if geo.rects_overlap(box, s, 1.0):
                return False
        for other in labels:
            if geo.rects_overlap(box, other, 3.0):
                return False
        for pts in routes:
            for a, b in zip(pts, pts[1:]):
                if geo.segment_hits_rect(a, b, box, -2.0):
                    return False
        return True

    def _candidates_for_label(self, text, pts, mode):
        """Boxes in order of preference for a label on a route (actual coordinates)."""
        lw, lh = text_width(text) + 2 * LABEL_PAD_X, LABEL_H
        segs = list(zip(pts, pts[1:]))
        order = sorted(range(len(segs)), key=lambda i: (-(abs(segs[i][1][0] - segs[i][0][0]) + abs(segs[i][1][1] - segs[i][0][1])), i))
        if mode == "branch":
            order = [0] + [i for i in order if i != 0]
        step = 10.0
        for si in order:
            (ax, ay), (bx, by) = segs[si]
            horizontal = ay == by
            length = abs(bx - ax) + abs(by - ay)
            if length == 0:
                continue
            sign = 1 if (bx - ax) + (by - ay) > 0 else -1
            extent = lw if horizontal else lh
            if mode == "branch" and si == 0:
                first = 6.0 + extent / 2 if horizontal else 4.0 + extent / 2
                offsets = [first + k * step for k in range(int(max(0.0, length - extent - 6) / step) + 1)]
                offsets = [o for o in offsets if o + extent / 2 <= length + extent / 2] or [first]
                centres = [(ax + sign * o, ay) if horizontal else (ax, ay + sign * o) for o in offsets]
            else:
                mid = (ax + bx) / 2 if horizontal else (ay + by) / 2
                room = int(max(0.0, length - extent) / 2 / step)
                shifts = [0.0] + [s * k * step for k in range(1, room + 1) for s in (1, -1)]
                centres = [(mid + sh, ay) if horizontal else (ax, mid + sh) for sh in shifts]
            if horizontal:
                sides = ("below", "above") if mode == "back" and self.horizontal else ("above", "below")
            else:
                sides = ("right", "left")
            near = 3.0 if mode == "back" else 6.0     # a back edge's label hugs its channel
            for side in sides:
                for cx, cy in centres:
                    if side == "above":
                        yield cx - lw / 2, cy - 3 - lh, lw, lh
                    elif side == "below":
                        yield cx - lw / 2, cy + 3, lw, lh
                    elif side == "right":
                        yield cx + near, cy - lh / 2, lw, lh
                    else:
                        yield cx - near - lw, cy - lh / 2, lw, lh

    # ---- assembly -------------------------------------------------------------------------------------------

    def run(self, last=False):
        self._dfs()
        self._order()
        self._place_cross()
        banned = set()
        for _ in range(8):
            self._plan(banned)
            chan = self._final_p()
            bad = self._overlapping(chan)
            if not bad:
                break
            for a, b in bad:     # the later link gives way; when it already has, the earlier one does
                banned.add((b.i, self._key(b.cand)) if (b.i, self._key(b.cand)) not in banned
                           else (a.i, self._key(a.cand)))
        xy = (lambda c, p: (p, c)) if self.horizontal else (lambda c, p: (c, p))
        shapes = []
        for n in self.nodes:
            x, y = xy(n.c, n.p)
            shapes.append({"id": f"node:{n.id}", "kind": "node", "shape": _SHAPES.get(n.node.shape, "box"),
                           "x": x - n.w / 2, "y": y - n.h / 2, "w": n.w, "h": n.h, "label": n.node.label,
                           "sublabel": n.node.detail, "ref": n.id, "emphasis": False, "lines": list(n.lines),
                           "rank": n.rank})
        routes = []
        for lk in self.links:
            pts = []
            for c, p in self._points(lk, lk.cand, chan):
                pt = list(xy(c, p))
                if not pts or pts[-1] != pt:
                    pts.append(pt)
            routes.append({"id": f"link:{lk.i}", "ref": lk.link.at or f"links[{lk.i}]", "from": f"node:{lk.src.id}",
                           "to": f"node:{lk.dst.id}", "points": pts, "style": "solid", "head": "filled",
                           "emphasis": False, "back": lk.back})
        labels = self._labels(shapes, routes, last)
        if labels is None:
            return None
        return self._finish(shapes, routes, labels)

    def _labels(self, shapes, routes, last=False):
        """The labels, or None when one fits nowhere (and last is false: the caller widens the gaps and retries)."""
        by_route = {rt["id"]: rt for rt in routes}
        mode = {}
        for lk in self.links:
            mode[lk.i] = "back" if lk.back else "branch" if lk.src.node.shape == "decision" else "mid"
        todo = [lk for m in ("branch", "back", "mid") for lk in self.links if lk.link.label and mode[lk.i] == m]
        placed, out = [], {}
        all_points = [rt["points"] for rt in routes]
        for lk in todo:
            text, pts = lk.link.label, by_route[f"link:{lk.i}"]["points"]
            first = None
            for x, y, w, h in self._candidates_for_label(text, pts, mode[lk.i]):
                box = {"x": r(x), "y": r(y), "w": r(w), "h": h}
                if first is None:
                    first = box
                if self._fits(box, shapes, placed, all_points):
                    break
            else:
                if not last:
                    return None
                box = first
            placed.append(box)
            out[lk.i] = {"id": f"label:{lk.i}", "owner": f"link:{lk.i}", "text": text, **box}
        return [out[i] for i in sorted(out)]

    def _finish(self, shapes, routes, labels):
        xs, ys = [], []
        for s in shapes:
            xs += [s["x"], s["x"] + s["w"]]
            ys += [s["y"], s["y"] + s["h"]]
        for rt in routes:
            for x, y in rt["points"]:
                xs.append(x)
                ys.append(y)
        for lb in labels:
            xs += [lb["x"], lb["x"] + lb["w"]]
            ys += [lb["y"], lb["y"] + lb["h"]]
        dx, dy = MARGIN - min(xs), MARGIN - min(ys)
        for s in shapes:
            s["x"], s["y"] = r(s["x"] + dx), r(s["y"] + dy)
            s["w"], s["h"] = r(s["w"]), r(s["h"])
        for rt in routes:
            rt["points"] = [[r(x + dx), r(y + dy)] for x, y in rt["points"]]
        for lb in labels:
            lb["x"], lb["y"] = r(lb["x"] + dx), r(lb["y"] + dy)
            lb["w"], lb["h"] = r(lb["w"]), r(lb["h"])
        return {"width": r(max(xs) - min(xs) + 2 * MARGIN), "height": r(max(ys) - min(ys) + 2 * MARGIN),
                "shapes": shapes, "routes": routes, "labels": labels}


_SHAPES = {"start": "start", "end": "end", "decision": "decision", "step": "box"}


def layout(diagram):
    """The layout dict for a validated workflow Diagram. A label that fits nowhere widens every gap by WIDEN and the
    layout is redone, so the labels of a valid diagram never overlap anything."""
    if not diagram.nodes:
        return {"width": 2 * MARGIN, "height": 2 * MARGIN, "shapes": [], "routes": [], "labels": []}
    for k in range(MAX_WIDEN):
        lay = _Flow(diagram, k * WIDEN).run(last=k == MAX_WIDEN - 1)
        if lay is not None:
            return lay


# ---- self-test ----------------------------------------------------------------------------------------------


def _shape(lay, node_id):
    return next(s for s in lay["shapes"] if s["id"] == f"node:{node_id}")


def _centre(s):
    return s["x"] + s["w"] / 2, s["y"] + s["h"] / 2


def _inside(lay):
    out = []
    w, h = lay["width"], lay["height"]
    for s in lay["shapes"]:
        if s["x"] < 0 or s["y"] < 0 or s["x"] + s["w"] > w or s["y"] + s["h"] > h:
            out.append(f"shape {s['id']} outside the canvas")
    for rt in lay["routes"]:
        for x, y in rt["points"]:
            if not (0 <= x <= w and 0 <= y <= h):
                out.append(f"route {rt['id']} point {x},{y} outside the canvas")
    for lb in lay["labels"]:
        if lb["x"] < 0 or lb["y"] < 0 or lb["x"] + lb["w"] > w or lb["y"] + lb["h"] > h:
            out.append(f"label '{lb['text']}' outside the canvas")
    return out


def _overlaps(lay):
    """Messages for every pair of routes without a node in common that run along one line over some length."""
    out = []
    routes = lay["routes"]
    for i, a in enumerate(routes):
        for b in routes[i + 1:]:
            if {a["from"], a["to"]} & {b["from"], b["to"]}:
                continue
            if _Flow._overlap(a["points"], b["points"]):
                out.append(f"routes {a['id']} and {b['id']} share no node but run along one line")
    return out


def _check_file(path, tag):
    problems = []
    d, diags = val.load(path)
    errs = [x for x in diags if x["severity"] == "error"]
    if errs or d is None:
        return [f"{tag}: load: {errs}"], None
    lay = layout(d)
    if json.dumps(lay, sort_keys=True) != json.dumps(layout(d), sort_keys=True):
        problems.append(f"{tag}: layout differs on a second run")
    d2, _ = val.load(path)
    if json.dumps(lay, sort_keys=True) != json.dumps(layout(d2), sort_keys=True):
        problems.append(f"{tag}: layout differs after a reload")
    problems += [f"{tag}: geometry {x['rule']}: {x['message']}" for x in geo.check(lay) if x["severity"] == "error"]
    problems += [f"{tag}: {x}" for x in _inside(lay)]
    right = d.direction == "right"
    for rt in lay["routes"]:
        a, b = _shape(lay, rt["from"][5:]), _shape(lay, rt["to"][5:])
        if not rt["back"] and not b["rank"] > a["rank"]:
            problems.append(f"{tag}: forward link {rt['id']} does not go to a later rank")
        pa, pb = (_centre(a)[0], _centre(b)[0]) if right else (_centre(a)[1], _centre(b)[1])
        if not rt["back"] and not pb > pa:
            problems.append(f"{tag}: forward link {rt['id']} does not go {'right' if right else 'down'}")
        for (x1, y1), (x2, y2) in zip(rt["points"], rt["points"][1:]):
            if x1 != x2 and y1 != y2:
                problems.append(f"{tag}: route {rt['id']} has a diagonal segment")
        ax, ay = rt["points"][0]
        if not (a["x"] <= ax <= a["x"] + a["w"] and a["y"] <= ay <= a["y"] + a["h"]):
            problems.append(f"{tag}: route {rt['id']} does not start on its source")
        bx, by = rt["points"][-1]
        if not (b["x"] <= bx <= b["x"] + b["w"] and b["y"] <= by <= b["y"] + b["h"]):
            problems.append(f"{tag}: route {rt['id']} does not end on its target")
    problems += [f"{tag}: {x}" for x in _overlaps(lay)]
    by_rank = {}
    for s in lay["shapes"]:
        by_rank.setdefault(s["rank"], []).append(s["x"] if right else s["y"])
    for k, edge in by_rank.items():
        if len(set(edge)) != 1:
            problems.append(f"{tag}: nodes of rank {k} do not share their {'left' if right else 'top'} edge: {sorted(edge)}")
    for s in lay["shapes"]:
        if s["shape"] != "decision" and any(len(x) and geo.text_width(x) > 220 for x in s["lines"]):
            problems.append(f"{tag}: a line of {s['id']} is wider than 220")
        if s["shape"] == "decision" and any(geo.text_width(x) > 150 for x in s["lines"]):
            problems.append(f"{tag}: a line of {s['id']} is wider than 150")
    return problems, (d, lay)


def _tiny(direction):
    d = ir.Diagram("workflow", "t", direction=direction)
    d.nodes = [ir.Node("a", "A", "start"), ir.Node("b", "B")]
    d.links = [ir.Link("a", "b", None, "links[0]")]
    return d


def _flow(nodes, links, direction="down"):
    """A workflow Diagram from node specs (id, shape) and link specs (from, to[, label]); validated."""
    d = ir.Diagram("workflow", "t", direction=direction)
    d.nodes = [ir.Node(i, i, shape, None, None, [], f"nodes[{k}]") for k, (i, shape) in enumerate(nodes)]
    d.links = [ir.Link(x[0], x[1], x[2] if len(x) > 2 else None, f"links[{k}]") for k, x in enumerate(links)]
    errs = [x for x in val.validate(d) if x["severity"] == "error"]
    if errs:
        raise ValueError(f"test diagram is invalid: {errs}")
    return d


def _col(lay, node_id):
    return _centre(_shape(lay, node_id))[0]


def _test_columns():
    """The first forward outgoing link of a node pulls its target into the node's column; the node declared first wins
    a target two nodes claim."""
    problems = []
    d = _flow([("s", "start"), ("a", "step"), ("x", "step"), ("b", "step"), ("e", "step")],
              [("s", "a"), ("x", "b"), ("a", "b"), ("s", "x"), ("b", "e")])
    lay = layout(d)
    if not (_col(lay, "a") == _col(lay, "b") == _col(lay, "e")):
        problems.append(f"columns: a, b, e should share a column (a is declared before x, so a's first link claims b): "
                        f"{[_col(lay, i) for i in 'abe']}")
    if _col(lay, "x") == _col(lay, "a"):
        problems.append("columns: x shares a column with a")
    return problems


def _test_order():
    problems = []
    # ties break by declaration order, not by the order a depth-first walk meets the nodes
    d = _flow([("s", "start"), ("a", "step"), ("b", "step")], [("s", "b"), ("s", "a")])
    lay = layout(d)
    if not _col(lay, "a") < _col(lay, "b"):
        problems.append("order: a (declared first) is not left of b when both hang from s")
    # barycentre sweeps uncross links that declaration order would cross
    d = _flow([("s", "start"), ("p", "step"), ("q", "step"), ("x", "step"), ("y", "step")],
              [("s", "p"), ("s", "q"), ("p", "y"), ("q", "x")])
    lay = layout(d)
    if not (_col(lay, "p") < _col(lay, "q") and _col(lay, "y") < _col(lay, "x")):
        problems.append("order: the barycentre sweep did not put y (child of p) left of x (child of q)")
    if geo.check(lay)[-1]["message"] != "0 route crossing(s)":
        problems.append(f"order: the uncrossed diagram still has {geo.check(lay)[-1]['message']}")
    return problems


def _test_back_edges():
    """Back edges try several exits and entries; each of these needs a later one than the first."""
    problems = []
    # a and b share a rank, a left of b: a's right exit would run through b
    d = _flow([("s", "start"), ("r", "step"), ("a", "step"), ("b", "step"), ("e", "end")],
              [("s", "r"), ("r", "a"), ("r", "b"), ("a", "e"), ("b", "e"), ("a", "s", "again"), ("b", "r", "retry")])
    lay = layout(d)
    problems += [f"back edges (siblings): geometry {x['rule']}: {x['message']}" for x in geo.check(lay) if x["severity"] == "error"]
    a = _shape(lay, "a")
    leave = next(rt for rt in lay["routes"] if rt["from"] == "node:a" and rt["to"] == "node:s")
    if leave["points"][0][1] != a["y"] + a["h"]:
        problems.append(f"back edges (siblings): a's loop should leave by its bottom, starts at {leave['points'][0]}")
    # u sits right of t in t's rank, so a loop entering t's right side would run through u: it enters from the top
    d = _flow([("s", "start"), ("t", "step"), ("u", "step"), ("m", "step"), ("e", "end")],
              [("s", "t"), ("s", "u"), ("t", "m"), ("u", "m"), ("m", "e"), ("m", "t", "again")])
    lay = layout(d)
    problems += [f"back edges (entry): geometry {x['rule']}: {x['message']}" for x in geo.check(lay) if x["severity"] == "error"]
    t = _shape(lay, "t")
    loop = next(rt for rt in lay["routes"] if rt["back"])
    if loop["points"][-1][1] != t["y"]:
        problems.append(f"back edges (entry): the loop should enter t from the top, ends at {loop['points'][-1]}")
    return problems


def _random_flow(rng, direction):
    """A random valid workflow: a spanning tree from the start, extra links (back edges and skips among them),
    decisions with at least two labelled branches, labels of many lengths."""
    n = rng.randint(3, 14)
    words = ["alpha", "beta gamma", "a much longer step label that wraps over lines", "Check", "Run the whole thing again",
             "x", "Review + approve"]
    labels = ["Yes", "No", "next scheduled run", "retry later", "ok", "fails and the whole run is retried"]
    shapes = ["start"] + [rng.choice(["step"] * 5 + ["decision", "end"]) for _ in range(n - 1)]
    links = []

    def add(a, b, label=None):
        links.append((f"n{a}", f"n{b}", label))

    for i in range(1, n):
        cand = [j for j in range(i) if shapes[j] != "end"]
        if not cand:
            shapes[i - 1] = "step"
            cand = [i - 1]
        add(rng.choice(cand[-4:] if rng.random() < 0.7 else cand), i, rng.choice(labels) if rng.random() < 0.35 else None)
    for _ in range(rng.randint(0, n)):
        a, b = rng.randrange(n), rng.randrange(n)
        if a != b and shapes[a] != "end" and not any(x[0] == f"n{a}" and x[1] == f"n{b}" for x in links):
            add(a, b, rng.choice(labels) if rng.random() < 0.5 else None)
    for i, shape in enumerate(shapes):
        if shape == "decision":
            outs = [k for k, x in enumerate(links) if x[0] == f"n{i}"]
            while len(outs) < 2:
                taken = {links[k][1] for k in outs}
                j = rng.choice([j for j in range(n) if j != i and f"n{j}" not in taken])
                add(i, j)
                outs.append(len(links) - 1)
            for k in outs:
                if not links[k][2]:
                    links[k] = (links[k][0], links[k][1], rng.choice(["Yes", "No", "maybe"]))
    d = ir.Diagram("workflow", "t", direction=direction)
    d.nodes = [ir.Node(f"n{i}", rng.choice(words), shapes[i], "some detail text" if rng.random() < 0.3 else None,
                       None, [], f"nodes[{i}]") for i in range(n)]
    d.links = [ir.Link(a, b, c, f"links[{k}]") for k, (a, b, c) in enumerate(links)]
    return d


def _test_random():
    """300 seeded random workflows, both directions: valid input never fails a geometry gate; routes with no node in
    common seldom run along one line (an exchange of two columns across one gap cannot avoid it with every route on
    the node centres)."""
    problems = []
    gate = overlapping = 0
    for seed in range(300):
        for direction in ("down", "right"):
            d = _random_flow(random.Random(seed), direction)
            errs = [x for x in val.validate(d) if x["severity"] == "error"]
            if errs:
                problems.append(f"random {seed} {direction}: generator made an invalid diagram {errs}")
                continue
            lay = layout(d)
            found = [x for x in geo.check(lay) if x["severity"] == "error"]
            if found:
                gate += 1
                if gate <= 3:
                    problems.append(f"random {seed} {direction}: geometry {found[0]['rule']}: {found[0]['message']}")
            overlapping += bool(_overlaps(lay))
    if gate:
        problems.append(f"random: {gate} of 600 layouts fail the geometry gates")
    if overlapping > 6:
        problems.append(f"random: {overlapping} of 600 layouts have routes with no node in common along one line (limit 6)")
    return problems


def _test_core_flow(d, lay):
    """The path of first forward links from the start runs straight; the loop's label hugs its channel; the two
    branches of the decision share a top."""
    problems = []
    back = {(rt["from"], rt["to"]) for rt in lay["routes"] if rt["back"]}
    node = d.nodes[0].id
    chain = [node]
    while True:
        nxt = next((lk.to for lk in d.links if lk.frm == node and (f"node:{lk.frm}", f"node:{lk.to}") not in back), None)
        if nxt is None or nxt in chain:
            break
        chain.append(nxt)
        node = nxt
    if len(chain) < 9:
        problems.append(f"core-flow: the first-link path is only {len(chain)} nodes long")
    xs = {_col(lay, c) for c in chain}
    if len(xs) != 1:
        problems.append(f"core-flow: the path of first links is not on one x: {sorted(xs)}")
    rt = next(x for x in lay["routes"] if x["back"])
    vertical = max(((a, b) for a, b in zip(rt["points"], rt["points"][1:]) if a[0] == b[0]),
                   key=lambda ab: abs(ab[0][1] - ab[1][1]))
    label = next(x for x in lay["labels"] if x["owner"] == rt["id"])
    if not 0 < label["x"] - vertical[0][0] <= 4:
        problems.append(f"core-flow: the loop's label starts {label['x'] - vertical[0][0]} from its channel (want 0 to 4)")
    decision = next(s for s in lay["shapes"] if s["shape"] == "decision")
    kids = {rt["to"] for rt in lay["routes"] if rt["from"] == decision["id"]}
    if len({s["y"] for s in lay["shapes"] if s["id"] in kids}) != 1:
        problems.append("core-flow: the two branches of the decision do not share a top")
    return problems


def self_test():
    problems = []
    files = [TESTS / "valid" / "workflow-basic.json"] + sorted((TESTS / "workflow").glob("*.json"))
    if len(files) < 6:
        problems.append(f"need workflow-basic.json and at least 5 fixtures under {TESTS / 'workflow'}, found {len(files)}")
    loaded = {}
    for f in files:
        found, res = _check_file(f, f.name)
        problems += found
        if res:
            loaded[f.name] = res
    # Core flow: one straight main path, the loop beside every node it passes.
    if "core-flow.json" in loaded:
        d, lay = loaded["core-flow.json"]
        ids = {n.label: n.id for n in d.nodes}
        chain = [ids["1. Onboarding"], ids["2. Agent setup"], ids["User's own agent"],
                 ids["Agent checks itself: can it connect MCP?"]]
        xs = {_centre(_shape(lay, c))[0] for c in chain}
        if len(xs) != 1:
            problems.append(f"core-flow: the main chain is not on one x: {sorted(xs)}")
        back = [rt for rt in lay["routes"] if rt["back"]]
        if len(back) != 1:
            problems.append(f"core-flow: expected 1 back edge, got {len(back)}")
        for rt in back:
            vertical = max(((a, b) for a, b in zip(rt["points"], rt["points"][1:]) if a[0] == b[0]),
                           key=lambda ab: abs(ab[0][1] - ab[1][1]))
            vx, lo, hi = vertical[0][0], min(vertical[0][1], vertical[1][1]), max(vertical[0][1], vertical[1][1])
            for s in lay["shapes"]:
                if s["y"] < hi and s["y"] + s["h"] > lo and s["x"] + s["w"] >= vx:
                    problems.append(f"core-flow: the loop's vertical at x={vx} is not right of {s['id']}")
        decisions = [s for s in lay["shapes"] if s["shape"] == "decision"]
        branch = [rt for rt in lay["routes"] if rt["from"] == decisions[0]["id"]]
        if len(branch) != 2 or len({tuple(rt["points"][0]) for rt in branch}) != 2:
            problems.append("core-flow: the two branches of the decision do not leave by two vertices")
        if len(lay["labels"]) != 3:
            problems.append(f"core-flow: expected 3 labels, got {len(lay['labels'])}")
    if "two-loops.json" in loaded:
        if sum(rt["back"] for rt in loaded["two-loops.json"][1]["routes"]) != 2:
            problems.append("two-loops: expected 2 back edges")
    if "skip-rank.json" in loaded:
        lay = loaded["skip-rank.json"][1]
        skip = next(rt for rt in lay["routes"] if rt["id"] == "link:4")
        if len(skip["points"]) < 5:
            problems.append("skip-rank: the long link was not routed around the nodes in between")
    if "direction-right.json" in loaded:
        lay = loaded["direction-right.json"][1]
        if not all(rt["back"] is False or max(p[1] for p in rt["points"]) > _centre(_shape(lay, rt["from"][5:]))[1]
                   for rt in lay["routes"]):
            problems.append("direction-right: a back edge does not route below")
    # Exact values on a tiny diagram.
    exact = {"down": {"width": 220.0, "height": 208.0, "a": (40.0, 40.0), "b": (40.0, 128.0),
                      "points": [[110.0, 80.0], [110.0, 128.0]]},
             "right": {"width": 408.0, "height": 120.0, "a": (40.0, 40.0), "b": (228.0, 40.0),
                       "points": [[180.0, 60.0], [228.0, 60.0]]}}
    for direction, want in exact.items():
        lay = layout(_tiny(direction))
        got = {"width": lay["width"], "height": lay["height"], "a": (lay["shapes"][0]["x"], lay["shapes"][0]["y"]),
               "b": (lay["shapes"][1]["x"], lay["shapes"][1]["y"]), "points": lay["routes"][0]["points"]}
        if got != want:
            problems.append(f"tiny {direction}: expected {want}, got {got}")
        s = lay["shapes"][0]
        if (s["id"], s["kind"], s["shape"], s["w"], s["h"], s["lines"]) != ("node:a", "node", "start", 140.0, 40.0, ["A"]):
            problems.append(f"tiny {direction}: shape fields wrong: {s}")
        rt = lay["routes"][0]
        if (rt["id"], rt["ref"], rt["from"], rt["to"], rt["style"], rt["head"], rt["back"]) != \
                ("link:0", "links[0]", "node:a", "node:b", "solid", "filled", False):
            problems.append(f"tiny {direction}: route fields wrong: {rt}")
    # Wrapping and sizes: a long label wraps at 220 px, a decision at 150 px.
    d = ir.Diagram("workflow", "t")
    long = "Writes straight into the app through the connected tool and confirms"
    d.nodes = [ir.Node("a", long, "step", "detail words"), ir.Node("b", long, "decision")]
    lay = layout(d)
    a, b = lay["shapes"]
    if len(a["lines"]) < 3 or a["lines"][-1] != "detail words" or a["h"] != 22 + 18 * len(a["lines"]):
        problems.append(f"wrap: box lines/height wrong: {a['lines']} h={a['h']}")
    if any(text_width(x) > 220 for x in a["lines"]) or any(text_width(x) > 150 for x in b["lines"]):
        problems.append("wrap: a line is wider than its limit")
    if b["w"] < max(text_width(x) for x in b["lines"]) + 70 or b["h"] < 80:
        problems.append("wrap: diamond smaller than its text plus 70")
    problems += _test_columns()
    problems += _test_order()
    problems += _test_back_edges()
    problems += _test_random()
    if "core-flow.json" in loaded:
        problems += _test_core_flow(*loaded["core-flow.json"])
    return problems


def main(argv):
    if argv == ["--self-test"]:
        found = self_test()
        print("FAIL\n" + "\n".join(found) if found else "PASS: graph_workflow self-test")
        return 1 if found else 0
    if len(argv) == 2 and argv[0] == "--layout":
        d, diags = val.load(argv[1])
        errs = [x for x in diags if x["severity"] == "error"]
        if errs or d is None or d.kind != "workflow":
            print(json.dumps(errs, indent=1), file=sys.stderr)
            return 1
        print(json.dumps(layout(d), indent=1))
        return 0
    print("usage: graph_workflow.py --self-test | --layout FILE.json", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
