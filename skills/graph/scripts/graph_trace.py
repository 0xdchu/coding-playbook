#!/usr/bin/env python3
"""Convert the JSON a code-graph tool prints for a call trace into the flow-diagram IR.

    convert(trace) -> IR dict

The trace: {"paths": [{"steps": [{"from_name", "from_file", "from_line", "to_name", "to_file", "to_line",
"provenance", "site_file", "site_line"}, ...]}, ...]}. Only the first path is used. Participants are the files in
first-seen order (label: the file name), each hop is one step labelled with the callee name (kind "self" when both
ends are the same file) and one edge of its own (id "h1", "h2", ...; the step names it with "edge", so a later hop
between the same two files, or a hop inside one file, keeps its own call site) that cites the call site and keeps the
hop's provenance: "proven" stays proven, every other value is read as "heuristic" (it is drawn unproven).
"""
import posixpath


class TraceError(ValueError):
    pass


def _text(step, key, where, required=True):
    v = step.get(key)
    if v is None and not required:
        return None
    if not isinstance(v, str) or not v.strip():
        raise TraceError(f"{where}: '{key}' must be a non-empty string")
    return v


def _line(step, key):
    v = step.get(key)
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 1 else None


def convert(trace):
    if not isinstance(trace, dict) or not isinstance(trace.get("paths"), list) or not trace["paths"]:
        raise TraceError("the trace has no paths (expected a non-empty 'paths' list)")
    path0 = trace["paths"][0]
    steps = path0.get("steps") if isinstance(path0, dict) else None
    if not isinstance(steps, list) or not steps:
        raise TraceError("paths[0] has no steps")
    ids, parts, edges, out = {}, [], [], []
    heuristic = 0

    def pid(file):
        if file not in ids:
            ids[file] = f"f{len(ids) + 1}"
            parts.append({"id": ids[file], "label": posixpath.basename(file.replace("\\", "/")) or file})
        return ids[file]

    for i, st in enumerate(steps):
        where = f"paths[0].steps[{i}]"
        if not isinstance(st, dict):
            raise TraceError(f"{where}: expected an object")
        frm_file, to_file = _text(st, "from_file", where), _text(st, "to_file", where)
        name = _text(st, "to_name", where)
        frm, to = pid(frm_file), pid(to_file)
        edge = {"id": f"h{i + 1}", "from": frm, "to": to, "label": name}
        prov = st.get("provenance")
        if isinstance(prov, str) and prov.strip():
            edge["provenance"] = "proven" if prov == "proven" else "heuristic"
            heuristic += edge["provenance"] == "heuristic"
        site_file, site_line = st.get("site_file"), _line(st, "site_line")
        if isinstance(site_file, str) and site_file.strip() and site_line:
            edge["sources"] = [{"path": site_file, "line": site_line, "label": f"call to {name}"}]
        edges.append(edge)
        step = {"from": frm, "to": to, "label": name, "kind": "self" if frm == to else "call", "edge": edge["id"]}
        to_line = _line(st, "to_line")
        if to_line:
            step["note"] = f"{name} is defined at {to_file}:{to_line}"
        out.append(step)

    first, last = steps[0], steps[-1]
    title = f"Call trace: {first.get('from_name') or '?'} to {last.get('to_name') or '?'}"
    return {"kind": "sequence", "title": title,
            "subtitle": f"{len(steps)} hop(s), {heuristic} heuristic; imported from a call trace",
            "participants": parts, "edges": edges, "steps": out}
