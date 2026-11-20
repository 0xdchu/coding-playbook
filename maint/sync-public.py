#!/usr/bin/env python3
"""Keep the public copy of this repo in step with this one (APS-65).

The public repo (for students) holds every file of this repo's merged main, with the rewrites in
`maint/public-sync.json` "replace" applied to the files each one names, except the files listed as "public_only"
(its own CLAUDE.md, README.md and branch rule, written for that audience, and files only the public repo holds). Those are never written; each file
entry is reported until it has been brought in step by hand after its internal counterpart changed (`--reviewed`). An entry
ending in '/' is a folder only the public repo holds: every file under it is kept, nothing is reviewed, and the report lists
it only when this repo holds a file under it (not published; remove it here or ask the owner). Paths listed
"internal_only" (same path rules; an entry ending in '/' is a folder) are this repo's own: never published, never
reviewed, never leak-scanned, and a public file under one is deleted. An entry inside or equal to a public-only one
(or the other way round), or a key the config does not know, refuses the config. The script refuses to run when its
own file differs from its copy at the source ref, or is missing there: run it from a checkout whose script equals the
source ref's (pull first), so a copy that is behind or edited never reads a config it does not know. A copy older than
this check cannot refuse that way (see docs/internals.md, the sync-public.py section).

  python3 maint/sync-public.py            report what differs between internal and public main
                                            (exit 0 in step, 1 out of step, 2 refused or failed)
  python3 maint/sync-public.py --write    bring the public work tree in step, on a branch that contains public main
                                            (exit 0 done, 3 done with public-only files still to review, 2 refused)
  python3 maint/sync-public.py --reviewed CLAUDE.md README.md
                                            record that those public-only files are in step with internal main
  python3 maint/sync-public.py --self-test

Both sides are read from refs, never a work tree or index: the source is this repo's origin/main (fetched
first; the config too is read there), the comparison is against "public_ref" of the public repo (default
origin/main, fetched first). A failed fetch makes a report exit 2 instead of "in step", and refuses a write. So a run publishes only what is merged (and from a branch whose script differs from main's it is refused), and "in step" means the
published repo, not an unmerged branch. `--write` refuses, writing nothing, when the public tree has uncommitted
changes, a directory to replace by a file still holds files that stay, is on main, master or a detached HEAD, does not contain public_ref, has a symlink where a file goes, or a
file to publish matches a leak pattern (secret shapes and internal names). It never commits, pushes or merges: the
main session reads the diff and does that. State lives in the public repo's `.sync-source.json`.
"""
import argparse
import importlib.util
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = "maint/public-sync.json"
CONFIG_KEYS = {"target", "public_ref", "source_ref", "replace", "public_only", "internal_only", "leak_patterns"}
STATE = ".sync-source.json"


class Refused(Exception):
    pass


def git(repo, *args, binary=False, check=True):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if check and out.returncode != 0:
        raise Refused(f"git {' '.join(args)} in {repo}: {out.stderr.decode(errors='replace').strip()}")
    return out.stdout if binary else out.stdout.decode()


def ok(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True).returncode == 0


def fetch_if_remote(repo, ref, notes):
    if ref.startswith("origin/") and not ok(repo, "fetch", "-q", "origin"):
        notes.append(f"could not fetch origin in {repo}; {ref} is the last fetched one")
    if not ok(repo, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"):
        raise Refused(f"{repo}: no commit at {ref}")


def tree(repo, ref):
    """{path: (mode, blob sha)} of a commit; a submodule or symlink entry is refused."""
    files = {}
    for entry in git(repo, "ls-tree", "-r", "-z", ref).split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        mode, kind, sha = meta.split()
        if kind != "blob" or mode == "120000":
            raise Refused(f"{repo} {ref}: {path} is a {'symlink' if mode == '120000' else kind}; not supported")
        files[path] = (mode, sha)
    return files


def blob(repo, sha):
    return git(repo, "cat-file", "blob", sha, binary=True)


def merged_config(src, ref, notes):
    """The config as merged at the source ref, never the work tree's, so a local edit changes nothing."""
    fetch_if_remote(src, ref, notes)
    try:
        cfg = json.loads(git(src, "show", f"{ref}:{CONFIG}"))
    except ValueError as e:
        raise Refused(f"{CONFIG} at {ref}: not JSON ({e})")
    if not isinstance(cfg, dict):
        raise Refused(f"{CONFIG} at {ref}: not an object")
    for key in ("target", "replace", "public_only", "leak_patterns"):
        if key not in cfg:
            raise Refused(f"{CONFIG} at {ref}: missing '{key}'")
    unknown = sorted(set(cfg) - CONFIG_KEYS)
    if unknown:
        raise Refused(f"{CONFIG} at {ref}: unknown key '{unknown[0]}'")
    check_public_only(cfg["public_only"], ref)
    cfg.setdefault("internal_only", [])
    check_public_only(cfg["internal_only"], ref, "internal-only")
    covers = lambda e, p: p == e or (e.endswith("/") and p.startswith(e))
    both = sorted(i for i in cfg["internal_only"] for o in cfg["public_only"] if covers(o, i) or covers(i, o))
    if both:
        raise Refused(f"{CONFIG} at {ref}: {both[0]} is both internal-only and inside or around a public-only entry")
    cfg["source_ref"] = ref
    cfg.setdefault("public_ref", "origin/main")
    return cfg


def check_public_only(entries, ref="the config", kind="public-only"):
    """A public-only (or internal-only) entry is a repo-relative path; one ending in '/' is a folder and covers
    every file under it."""
    if not isinstance(entries, list):
        raise Refused(f"{CONFIG} at {ref}: {kind.replace('-', '_')} is not a list")
    for e in entries:
        if not isinstance(e, str):
            raise Refused(f"{CONFIG} at {ref}: {kind} entry {e!r} is not a string")
        body = e[:-1] if e.endswith("/") else e
        if not body or e.startswith("/") or any(x in ("", ".", "..") for x in body.split("/")):
            raise Refused(f"{CONFIG} at {ref}: {kind} entry {e!r} is not a repo-relative path")


def public_only(path, cfg, key="public_only"):
    """True when path is listed public-only, or lies under a listed folder (an entry ending in '/')."""
    return any(path == e or (e.endswith("/") and path.startswith(e)) for e in cfg.get(key, []))


def internal_only(path, cfg):
    """True when path is listed internal-only (or lies under such a folder): never published, never reviewed."""
    return public_only(path, cfg, "internal_only")


def load_state(text):
    try:
        state = json.loads(text) if text else {}
    except ValueError as e:
        raise Refused(f"{STATE}: not JSON ({e})")
    if not isinstance(state, dict) or not isinstance(state.get("reviewed", {}), dict):
        raise Refused(f"{STATE}: not the expected object")
    state.setdefault("internal_commit", None)
    state.setdefault("reviewed", {})
    return state


def rewrite(path, data, cfg):
    rules = [r for r in cfg["replace"] if any(fnmatch.fnmatchcase(path, g) for g in r["paths"])]
    if not rules:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused(f"{path}: a replace rule names it but it is not UTF-8")
    for r in rules:
        text = text.replace(r["from"], r["to"])
    return text.encode("utf-8")


def desired(src, cfg):
    """{path: (mode, bytes)} the public repo should hold, public-only files and the config left out."""
    return {p: (mode, rewrite(p, blob(src, sha), cfg))
            for p, (mode, sha) in tree(src, cfg["source_ref"]).items()
            if p not in (CONFIG, STATE) and not public_only(p, cfg) and not internal_only(p, cfg)}


def compare(want, have_files, read):
    """add / update / mode / delete lists between the wanted files and a public file set."""
    add, update, mode, delete = [], [], [], []
    for p, (m, data) in sorted(want.items()):
        if p not in have_files:
            add.append(p)
            continue
        if read(p) != data:
            update.append(p)
        if have_files[p] != m:
            mode.append(p)
    return add, update, mode, delete


def reviews(src, dst_files, state, cfg, head):
    out = []
    for path in cfg["public_only"]:
        if path.endswith("/"):
            held = sorted(p for p in tree(src, head) if p.startswith(path))
            if held:
                out.append((path, f"internal holds {held[0]} under this public-only folder; it is not published "
                                  "(remove it here, or ask the owner whether the folder stays public-only)"))
            continue
        last = state["reviewed"].get(path)
        if path not in dst_files:
            if ok(src, "cat-file", "-e", f"{head}:{path}"):
                out.append((path, "missing in the public repo"))
        elif not last:
            out.append((path, "never recorded as in step"))
        elif not ok(src, "cat-file", "-e", f"{last}^{{commit}}"):
            out.append((path, f"recorded commit {last} not found"))
        elif not ok(src, "diff", "--quiet", last, head, "--", path):
            out.append((path, f"internal {path} changed since {last}"))
    return out


def leaks(want, paths, cfg):
    pats = [re.compile(p.encode()) for p in cfg["leak_patterns"]]
    return [f"{p}: matches {pat.pattern.decode()}" for p in paths for pat in pats if pat.search(want[p][1])]


def run(src, override=None, write=False, reviewed=None, out=print, source_ref="origin/main"):
    notes = []
    cfg = merged_config(src, source_ref, notes)
    me = Path(__file__).resolve()
    self_path = me.relative_to(ROOT).as_posix()  # follows the script if it moves
    at_ref = tree(src, source_ref).get(self_path)
    if at_ref is None and Path(src).resolve() == ROOT:
        raise Refused(f"{self_path} is not at {source_ref}; run the script from a checkout of {source_ref}")
    if at_ref and blob(src, at_ref[1]) != me.read_bytes():
        raise Refused(f"this {self_path} differs from the one at {source_ref}; run the script from a checkout of {source_ref}")
    dst = Path(os.path.expanduser(override or cfg["target"])).resolve()
    if not (dst / ".git").exists():
        raise Refused(f"public repo not found at {dst}")
    fetch_if_remote(dst, cfg["public_ref"], notes)
    if notes and (write or reviewed):
        raise Refused("; ".join(notes) + "; writing from a stale ref is refused")
    for n in notes:
        out("note: " + n)
    head = git(src, "rev-parse", "--short", cfg["source_ref"]).strip()
    if write or reviewed:
        if write and git(dst, "status", "--porcelain").strip():
            raise Refused(f"{dst} has uncommitted changes; commit or stash them first")
        branch = git(dst, "rev-parse", "--abbrev-ref", "HEAD").strip()
        if branch in ("main", "master", "HEAD"):
            raise Refused(f"{dst} is on {branch}; create a branch from {cfg['public_ref']} first")
        if not ok(dst, "merge-base", "--is-ancestor", cfg["public_ref"], "HEAD"):
            raise Refused(f"{dst}: branch {branch} does not contain {cfg['public_ref']}; start it from there")
    if reviewed:
        folders = [p for p in reviewed if p.endswith("/") and p in cfg["public_only"]]
        if folders:
            raise Refused(f"a public-only folder has nothing to review: {', '.join(folders)} (if the report lists it, "
                          "remove the internal file under it, or ask the owner)")
        bad = [p for p in reviewed if p not in cfg["public_only"]]
        if bad:
            raise Refused(f"not public-only: {', '.join(bad)}")
        state = load_state((dst / STATE).read_text(encoding="utf-8") if (dst / STATE).exists() else "")
        synced = state["internal_commit"]
        if not synced or git(src, "rev-parse", f"{synced}^{{commit}}", check=False).strip() != \
                git(src, "rev-parse", f"{head}^{{commit}}").strip():
            raise Refused(f"the public tree was synced from {synced or 'nothing yet'}, internal is now {head}; "
                          f"run --write first, then review against that")
        for p in reviewed:
            state["reviewed"][p] = head
        (dst / STATE).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        out(f"recorded {', '.join(reviewed)} in step with internal {head}")
        return 0
    want = desired(src, cfg)
    if not write:
        pub = tree(dst, cfg["public_ref"])
        add, update, mode, _ = compare(want, {p: m for p, (m, _) in pub.items()}, lambda p: blob(dst, pub[p][1]))
        delete = sorted(p for p in set(pub) - set(want) - {STATE} if not public_only(p, cfg))
        state = load_state(blob(dst, pub[STATE][1]).decode("utf-8") if STATE in pub else "")
        todo = reviews(src, pub, state, cfg, head)
        for label, items in (("add", add), ("update", update), ("mode", mode), ("delete", delete)):
            for p in items:
                out(f"{label:7} {p}")
        for p, why in todo:
            out(f"review  {p} by hand: {why}")
        if add or update or mode or delete or todo:
            out(f"OUT OF STEP: {len(add)} to add, {len(update)} to update, {len(mode)} mode, {len(delete)} to delete, "
                f"{len(todo)} public-only to review (internal {cfg['source_ref']} {head} vs public {cfg['public_ref']})")
            return 1
        if notes:
            out(f"UNKNOWN: in step with the last fetched refs only ({'; '.join(notes)})")
            return 2
        out(f"IN STEP: public {cfg['public_ref']} matches internal {cfg['source_ref']} {head}")
        return 0
    have = {p: m for p, (m, _) in tree(dst, "HEAD").items()}
    for p in list(want) + [STATE]:
        for parent in [dst / p, *list((dst / p).parents)]:
            if parent == dst:
                break
            if parent.is_symlink():
                raise Refused(f"{parent} is a symlink; not written through")
    add, update, mode, _ = compare(want, have, lambda p: (dst / p).read_bytes())
    delete = sorted(p for p in set(have) - set(want) - {STATE} if not public_only(p, cfg))
    found = leaks(want, add + update, cfg)
    if found:
        raise Refused("leak pattern in a file to publish: " + "; ".join(found))
    gone = set(delete)
    clear_dirs = []
    for p in add:
        if (dst / p).is_dir():
            inside = [os.path.relpath(os.path.join(d, f), dst) for d, _, fs in os.walk(dst / p) for f in fs]
            kept = [f for f in inside if f.replace(os.sep, "/") not in gone]
            if kept:
                raise Refused(f"{p} is a directory in the public tree holding files that stay ({kept[0]}); not replaced")
            clear_dirs.append(dst / p)
    for p in delete:
        (dst / p).unlink()
        parent = (dst / p).parent
        while parent != dst and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    for d in clear_dirs:
        if d.is_dir():
            shutil.rmtree(d)
    for p in sorted(set(add + update + mode)):
        f = dst / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(want[p][1])
        os.chmod(f, 0o755 if want[p][0] == "100755" else 0o644)
    state = load_state((dst / STATE).read_text(encoding="utf-8") if (dst / STATE).exists() else "")
    state["internal_commit"] = head
    (dst / STATE).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out(f"wrote {len(add)} added, {len(update)} updated, {len(mode)} mode, {len(delete)} deleted from internal {head}; "
        f"read `git -C {dst} add -A && git -C {dst} diff --cached` (new files included) before committing")
    todo = reviews(src, have, state, cfg, head)
    for p, why in todo:
        out(f"review  {p} by hand: {why}")
    return 3 if todo else 0


def self_test():
    problems = []
    tmp = Path(tempfile.mkdtemp(prefix="sync-public-"))
    quiet = lambda s: None
    try:
        def sh(repo, *args):
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)

        def init(repo):
            repo.mkdir()
            sh(repo, "init", "-q", "-b", "main")
            sh(repo, "config", "user.email", "t@example.invalid")
            sh(repo, "config", "user.name", "t")
            (repo / CONFIG).parent.mkdir(parents=True, exist_ok=True)  # the config's folder (maint/ since APS-91)

        def refused(**kw):
            try:
                run(src, None, out=quiet, source_ref="main", **kw)
            except Refused:
                return True
            return False

        def report():
            lines = []
            return run(src, None, out=lines.append, source_ref="main"), "\n".join(lines)

        src, dst = tmp / "internal", tmp / "public"
        init(src)
        init(dst)
        cfg = {"target": str(dst), "public_ref": "main", "source_ref": "no-such-ref",
               "replace": [{"from": "~/work/in/repo", "to": "~/work/pub/repo", "paths": ["rules/*"]},
                           {"from": "secret-name", "to": "a name", "paths": ["intent/*.md"]}],
               "public_only": ["CLAUDE.md", "README.md", "RULES.md", "PUB.md", "pubdir/"],
               "internal_only": ["mapdir/"],
               "leak_patterns": ["gh" + "p_[A-Za-z0-9]{20}", "secret-" + "name"]}
        (src / CONFIG).write_text(json.dumps(cfg))
        (src / "rules").mkdir()
        (src / "intent").mkdir()
        (src / "CLAUDE.md").write_text("internal rules\n")
        (src / "README.md").write_text("internal readme\n")
        (src / "rules" / "g.md").write_text("run ~/work/in/repo/x.py\n")
        (src / "keys.txt").write_text("answer key ~/work/in/repo stays\n")
        (src / "intent" / "i.md").write_text("from secret-name\n")
        (src / "bin.dat").write_bytes(b"\xff\x00\xfe")
        (src / "tool.sh").write_text("#!/bin/sh\n")
        os.chmod(src / "tool.sh", 0o755)
        (src / "plain.py").write_text("x = 1\n")
        sh(src, "add", "-A")
        sh(src, "commit", "-qm", "one")
        (dst / "CLAUDE.md").write_text("public rules\n")
        (dst / "README.md").write_text("public readme\n")
        (dst / "PUB.md").write_text("only the public repo has this\n")
        (dst / "old.md").write_text("gone soon\n")
        (dst / "pubdir" / "sub").mkdir(parents=True)
        (dst / "pubdir" / "a.md").write_text("a public-only folder\n")
        (dst / "pubdir" / "sub" / "b.md").write_text("nested in it\n")
        (dst / "pubdirx.md").write_text("a name that only starts like the folder\n")
        (dst / "PUB.md.old").write_text("a name that only starts like a public-only file\n")
        (dst / "plain.py").write_text("x = 1\n")
        os.chmod(dst / "plain.py", 0o755)
        (dst / "docs" / "a").mkdir(parents=True)
        (dst / "docs" / "a" / "inner.md").write_text("a directory the source replaces by a file\n")
        (dst / "docs" / "a" / "empty").mkdir()
        (src / "docs").mkdir()
        (src / "docs" / "a").write_text("now a file\n")
        sh(src, "add", "-A")
        sh(src, "commit", "-qm", "dir to file")
        sh(dst, "add", "-A")
        sh(dst, "commit", "-qm", "pub")
        rc, text = report()
        for want in ("add     rules/g.md", "delete  old.md", "mode    plain.py", "review  CLAUDE.md", "review  PUB.md"):
            if want not in text:
                problems.append(f"first report lacks {want!r}: {text!r}")
        if "pubdir/" in text or "delete  pubdirx.md" not in text or "delete  PUB.md.old" not in text:
            problems.append(f"public-only folder reported, or a look-alike name kept: {text!r}")
        if "RULES.md" in text:
            problems.append(f"public-only file missing on both sides reported: {text!r}")
        if rc != 1:
            problems.append(f"first report exit {rc}")
        if not refused(write=True):
            problems.append("write on main not refused")
        sh(dst, "checkout", "-q", "--detach")
        if not refused(write=True):
            problems.append("write on a detached HEAD not refused")
        sh(dst, "checkout", "-q", "-b", "sync", "main")
        (dst / "scratch").write_text("x")
        if not refused(write=True):
            problems.append("dirty public tree not refused")
        (dst / "scratch").unlink()
        (src / "rules" / "g.md").write_text("edited in the work tree, not committed\n")
        (src / "staged.md").write_text("staged only\n")
        sh(src, "add", "staged.md")
        if run(src, None, write=True, out=quiet, source_ref="main") != 3:
            problems.append("write with reviews pending did not exit 3")
        if (dst / "rules" / "g.md").read_text() != "run ~/work/pub/repo/x.py\n":
            problems.append("path not rewritten, or work-tree content published")
        if (dst / "staged.md").exists():
            problems.append("staged file published (index read instead of the ref)")
        if (dst / "keys.txt").read_text() != "answer key ~/work/in/repo stays\n":
            problems.append("rewrite applied outside its paths")
        if (dst / "intent" / "i.md").read_text() != "from a name\n":
            problems.append("redaction not applied")
        if (dst / "bin.dat").read_bytes() != b"\xff\x00\xfe":
            problems.append("binary file changed")
        if not os.access(dst / "tool.sh", os.X_OK) or os.access(dst / "plain.py", os.X_OK):
            problems.append("executable bits not taken from the source")
        if (dst / "old.md").exists():
            problems.append("stale file not deleted")
        if not (dst / "docs" / "a").is_file() or (dst / "docs" / "a").read_text() != "now a file\n":
            problems.append("directory not replaced by the source's file")
        if (dst / "CLAUDE.md").read_text() != "public rules\n" or (dst / CONFIG).exists():
            problems.append("public-only file overwritten or config published")
        if not (dst / "pubdir" / "a.md").exists() or not (dst / "pubdir" / "sub" / "b.md").exists():
            problems.append("file under a public-only folder deleted")
        if (dst / "pubdirx.md").exists():
            problems.append("a name that only starts like a public-only folder was kept")
        if not (dst / "PUB.md").exists() or (dst / "PUB.md").read_text() != "only the public repo has this\n":
            problems.append("public-only file held only by the public repo deleted or changed")
        (dst / "README.md").write_text("public readme, brought in step by hand\n")
        try:
            run(src, None, reviewed=["CLAUDE.md", "README.md", "PUB.md"], out=quiet, source_ref="main")
        except Refused as e:
            problems.append(f"--reviewed refused before the commit, with only hand edits pending: {e}")
        if (dst / "README.md").read_text() != "public readme, brought in step by hand\n":
            problems.append("--reviewed touched a public-only file")
        sh(dst, "add", "-A")
        sh(dst, "commit", "-qm", "synced")
        rc, text = report()
        if rc != 1 or not re.search(r"^(add|update|mode|delete) ", text, re.M):
            problems.append(f"unmerged sync branch counted as in step: {text!r}")
        sh(dst, "checkout", "-q", "main")
        sh(dst, "merge", "-q", "--ff-only", "sync")
        rc, text = report()
        if rc != 0:
            problems.append(f"not in step after merge: {text!r}")
        if not refused(reviewed=["CLAUDE.md"]):
            problems.append("--reviewed on main not refused")
        (src / "pubdir").mkdir()
        (src / "pubdir" / "x.md").write_text("internal file under the public-only folder\n")
        sh(src, "add", "pubdir")
        sh(src, "commit", "-qm", "internal under pubdir", "--", "pubdir")
        rc, text = report()
        if rc != 1 or "review  pubdir/ by hand: internal holds pubdir/x.md" not in text or re.search(r"^add +pubdir/", text, re.M):
            problems.append(f"internal file under a public-only folder not reported, or published: {text!r}")
        sh(src, "rm", "-rq", "pubdir")
        sh(src, "commit", "-qm", "drop it again", "--", "pubdir")
        rc, text = report()
        if rc != 0:
            problems.append(f"not in step after the internal file under the folder left: {text!r}")
        (src / "mapdir").mkdir()
        (src / "mapdir" / "view.html").write_text("embeds secret-name from an internal file\n")
        sh(src, "add", "mapdir")
        sh(src, "commit", "-qm", "an internal-only folder", "--", "mapdir")
        rc, text = report()
        if rc != 0 or "mapdir" in text:
            problems.append(f"an internal-only folder was published, reviewed or leak-scanned: {text!r}")
        n_odd = 0
        for bad_key in ({"internal_only": ["../x"]}, {"internal_only": "mapdir/"}, {"internal_only": ["pubdir/"]},
                        {"internal_only": ["pubdir/x/"]}, {"internal_only": ["PUB.md"]}, {"public_only": cfg["public_only"] + ["mapdir/a/"]},
                        {"internal-only": ["mapdir/"]}):
            odd = tmp / f"odd-config-{n_odd}"
            n_odd += 1
            init(odd)
            (odd / CONFIG).write_text(json.dumps(cfg | bad_key))
            sh(odd, "add", "-A")
            sh(odd, "commit", "-qm", "odd")
            try:
                merged_config(odd, "main", [])
                problems.append(f"a config with {bad_key!r} loaded")
            except Refused:
                pass
        src2, dst2 = tmp / "internal2", tmp / "public2"
        init(src2)
        init(dst2)
        cfg2 = {"target": str(dst2), "public_ref": "main", "replace": [], "public_only": [],
                "internal_only": ["mapdir/"], "leak_patterns": ["secret-" + "name"]}
        (src2 / CONFIG).write_text(json.dumps(cfg2))
        (src2 / "a.md").write_text("published\n")
        (src2 / "mapdir").mkdir()
        (src2 / "mapdir" / "v.html").write_text("embeds secret-name\n")
        sh(src2, "add", "-A")
        sh(src2, "commit", "-qm", "one")
        (dst2 / "mapdir").mkdir()
        (dst2 / "mapdir" / "old.html").write_text("a copy that should never have been published\n")
        sh(dst2, "add", "-A")
        sh(dst2, "commit", "-qm", "pub")
        sh(dst2, "checkout", "-q", "-b", "sync")
        lines2 = []
        run(src2, None, out=lines2.append, source_ref="main")
        if not any(l.startswith("delete  mapdir/old.html") for l in lines2) or any("mapdir/v.html" in l for l in lines2):
            problems.append(f"internal-only report: the public copy under it not listed for deletion, or the internal file listed: {lines2!r}")
        try:
            rc = run(src2, None, write=True, out=quiet, source_ref="main")
            if rc != 0 or not (dst2 / "a.md").exists() or (dst2 / "mapdir" / "v.html").exists() or (dst2 / "mapdir" / "old.html").exists():
                problems.append(f"internal-only write: rc {rc}, or a file under it published or kept in public")
        except Refused as e:
            problems.append(f"internal-only write refused (published and leak-scanned?): {e}")
        sh(dst2, "checkout", "-q", "--", ".")
        sh(dst2, "clean", "-qfd")
        me = Path(__file__).resolve()
        mine = src2 / me.relative_to(ROOT)
        mine.parent.mkdir(parents=True, exist_ok=True)
        mine.write_bytes(me.read_bytes())
        sh(src2, "add", "-A")
        sh(src2, "commit", "-qm", "the same copy, on a branch")
        sh(src2, "checkout", "-qb", "same")
        sh(src2, "checkout", "-q", "main")
        mine.write_text("# an older copy\n")
        sh(src2, "commit", "-qam", "another copy of the script on main")
        sh(src2, "checkout", "-q", "same")  # HEAD holds the same copy; the source ref does not
        for write in (False, True):
            try:
                run(src2, None, write=write, out=quiet, source_ref="main")
                problems.append(f"ran (write={write}) although this script differs from the copy at the source ref")
            except Refused as e:
                if "differs from the one at main" not in str(e):
                    problems.append(f"a differing copy refused for another reason: {e}")
        sh(src2, "checkout", "-q", "main")  # HEAD and the ref both hold the other copy; the running file differs
        try:
            run(src2, None, out=quiet, source_ref="main")
            problems.append("ran although the running file differs from the copy at the ref and at HEAD")
        except Refused as e:
            if "differs from the one at main" not in str(e):
                problems.append(f"a differing running file refused for another reason: {e}")
        mine.write_bytes(me.read_bytes())
        sh(src2, "commit", "-qam", "the same copy")
        src3 = tmp / "internal3"  # a checkout whose script is not committed at the source ref
        init(src3)
        (src3 / CONFIG).write_text(json.dumps(cfg2))
        sh(src3, "add", "-A")
        sh(src3, "commit", "-qm", "config only")
        loose = src3 / me.relative_to(ROOT)
        loose.parent.mkdir(parents=True, exist_ok=True)
        loose.write_bytes(me.read_bytes())
        spec = importlib.util.spec_from_file_location("sync_public_copy", loose)
        copy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(copy)
        try:
            copy.run(src3, None, out=quiet, source_ref="main")
            problems.append("ran although this script is not at the source ref of its own repo")
        except copy.Refused as e:
            if "is not at main" not in str(e):
                problems.append(f"a script missing at the ref refused for another reason: {e}")
        try:
            run(src2, None, out=quiet, source_ref="main")
        except Refused as e:
            problems.append(f"the same copy of the script refused: {e}")
        for bad in (["/"], [""], ["../x/"], ["a/../b"], ["/abs"], ["./x"], ["a//b"], ["a//"], [3], {"a": 1}):
            try:
                check_public_only(bad)
                problems.append(f"public-only entry {bad} accepted")
            except Refused:
                pass
        check_public_only(["CLAUDE.md", "skills/graph/", "intent/a.plan.md"])
        sh(dst, "checkout", "-q", "-b", "review-checks", "main")
        if not refused(reviewed=["plain.py"]):
            problems.append("--reviewed accepted a synced file")
        try:
            run(src, None, reviewed=["pubdir/"], out=quiet, source_ref="main")
            problems.append("--reviewed accepted a public-only folder")
        except Refused as e:
            if "nothing to review" not in str(e):
                problems.append(f"--reviewed of a folder refused for another reason: {e}")
        bad_cfg = tmp / "bad-config"
        init(bad_cfg)
        (bad_cfg / CONFIG).write_text(json.dumps(cfg | {"public_only": ["skills/graph//"]}))
        sh(bad_cfg, "add", "-A")
        sh(bad_cfg, "commit", "-qm", "bad")
        try:
            merged_config(bad_cfg, "main", [])
            problems.append("a config with a bad public-only entry loaded")
        except Refused:
            pass
        os.symlink(tmp / "elsewhere", dst / "linked")
        with open(dst / ".git" / "info" / "exclude", "a") as f:
            f.write("linked\n")
        (tmp / "elsewhere").mkdir()
        sh(dst, "checkout", "-q", "main")
        for bad in ("[]", '{"reviewed": []}'):
            try:
                load_state(bad)
                problems.append(f"state {bad} accepted")
            except Refused:
                pass
        notes = []
        sh(src, "remote", "add", "origin", str(tmp / "no-such-remote"))
        sh(src, "update-ref", "refs/remotes/origin/main", "main")
        fetch_if_remote(src, "origin/main", notes)
        if not notes:
            problems.append("failed fetch not noted")
        lines = []
        if run(src, None, out=lines.append, source_ref="origin/main") != 2 or "UNKNOWN" not in "\n".join(lines):
            problems.append(f"failed fetch reported as in step: {lines!r}")
        import inspect
        if inspect.signature(run).parameters["source_ref"].default != "origin/main":
            problems.append("the source ref default is not origin/main")
        sh(dst, "checkout", "-q", "-b", "fetch-failed", "main")
        try:
            run(src, None, write=True, out=quiet, source_ref="origin/main")
            problems.append("--write after a failed fetch not refused")
        except Refused:
            pass
        try:
            run(src, None, reviewed=["CLAUDE.md"], out=quiet, source_ref="origin/main")
            problems.append("--reviewed after a failed fetch not refused")
        except Refused:
            pass
        sh(dst, "checkout", "-q", "main")
        sh(src, "remote", "remove", "origin")
        try:
            rewrite("rules/x.md", b"\xff\xfe", cfg)
            problems.append("non-UTF-8 file under a replace rule not refused")
        except Refused:
            pass
        sub = tmp / "with-submodule"
        init(sub)
        sh(sub, "update-index", "--add", "--cacheinfo", "160000," + git(src, "rev-parse", "main").strip() + ",mod")
        sh(sub, "commit", "-qm", "gitlink")
        try:
            tree(sub, "HEAD")
            problems.append("submodule not refused")
        except Refused:
            pass
        sh(src, "checkout", "-q", "--", "rules/g.md")
        (src / "CLAUDE.md").write_text("internal rules, changed\n")
        (src / "plain.py").write_text("x = 2\n")
        (src / "RULES.md").write_text("internal branch rule\n")
        sh(src, "add", "-A")
        sh(src, "commit", "-qm", "two")
        rc, text = report()
        if rc != 1 or "review  CLAUDE.md" not in text or "README.md" in text:
            problems.append(f"changed internal CLAUDE.md not reported alone: {text!r}")
        if "update  plain.py" not in text or "review  RULES.md by hand: missing in the public repo" not in text:
            problems.append(f"content change or missing public-only file not reported: {text!r}")
        sh(dst, "checkout", "-q", "-b", "stale", "main")
        if not refused(reviewed=["CLAUDE.md"]):
            problems.append("--reviewed against a newer internal commit than the sync not refused")
        (src / "linked").mkdir()
        (src / "linked" / "f.md").write_text("must not land outside the public tree\n")
        sh(src, "add", "-A")
        sh(src, "commit", "-qm", "under an ignored symlink")
        if not refused(write=True) or (tmp / "elsewhere" / "f.md").exists():
            problems.append("write through an ignored symlink not refused")
        sh(src, "rm", "-rq", "linked")
        sh(src, "commit", "-qm", "drop linked")
        os.unlink(dst / "linked")
        run(src, None, write=True, out=quiet, source_ref="main")
        if json.loads((dst / STATE).read_text())["reviewed"].get("README.md") is None:
            problems.append("a write lost the recorded reviews (state deleted)")
        sh(dst, "add", "-A")
        sh(dst, "commit", "-qm", "stale sync")
        sh(dst, "checkout", "-q", "main")
        sh(dst, "checkout", "-q", "-b", "sync2", "main")
        st = json.loads((dst / STATE).read_text())
        st["reviewed"]["README.md"] = "0" * 40
        (dst / STATE).write_text(json.dumps(st))
        sh(dst, "commit", "-qam", "bad review")
        sh(dst, "checkout", "-q", "main")
        sh(dst, "merge", "-q", "--ff-only", "sync2")
        rc, text = report()
        if "review  README.md by hand: recorded commit" not in text:
            problems.append(f"unknown reviewed commit not reported: {text!r}")
        sh(dst, "checkout", "-q", "-b", "sync3", "main")
        (src / "new.md").write_text("token " + "gh" + "p_" + "A" * 24 + "\n")
        sh(src, "add", "-A")
        sh(src, "commit", "-qm", "leak in a new file")
        if not refused(write=True):
            problems.append("leak in an added file not refused")
        loose = dict(cfg, leak_patterns=[])
        (src / CONFIG).write_text(json.dumps(loose))
        if not refused(write=True):
            problems.append("an uncommitted config edit weakened the leak check")
        (src / CONFIG).write_text(json.dumps(cfg))
        if (dst / "new.md").exists():
            problems.append("refused write left a file")
        sh(src, "rm", "-q", "new.md")
        sh(src, "commit", "-qm", "unleak")
        (src / "plain.py").write_text("x = '" + "gh" + "p_" + "B" * 24 + "'\n")
        sh(src, "commit", "-qam", "leak in an updated file")
        if not refused(write=True):
            problems.append("leak in an updated file not refused")
        (src / "plain.py").write_text("x = 2\n")
        sh(src, "commit", "-qam", "unleak update")
        (src / "intent" / "j.md").write_text("plain secret-" + "name outside a redaction\n")
        (src / "notes.txt").write_text("secret-" + "name\n")
        sh(src, "add", "-A")
        sh(src, "commit", "-qm", "internal name")
        if not refused(write=True):
            problems.append("internal name outside a redaction not refused")
        sh(src, "rm", "-q", "notes.txt")
        sh(src, "commit", "-qm", "drop")
        (dst / "docs" / "b").mkdir()
        (dst / "docs" / "b" / "local.tmp").write_text("ignored, not the sync's to delete\n")
        with open(dst / ".git" / "info" / "exclude", "a") as f:
            f.write("local.tmp\n")
        (src / "docs" / "b").write_text("a file where the public tree has a directory\n")
        sh(src, "add", "-A")
        sh(src, "commit", "-qm", "file over a kept directory")
        if not refused(write=True) or not (dst / "docs" / "b" / "local.tmp").exists() \
                or git(dst, "status", "--porcelain").strip():
            problems.append("directory holding a kept file replaced, or a refused write changed the tree")
        sh(src, "rm", "-q", "docs/b")
        sh(src, "commit", "-qm", "undo")
        shutil.rmtree(dst / "docs" / "b")
        sh(dst, "checkout", "-q", "-b", "behind", "main~1")
        if not refused(write=True):
            problems.append("branch that does not contain public main not refused")
        sh(dst, "checkout", "-q", "sync3")
        if not refused(reviewed=["plain.py"]):
            problems.append("--reviewed accepted a synced file")
        sh(dst, "checkout", "-q", "main")
        if not refused(reviewed=["CLAUDE.md"]):
            problems.append("--reviewed on main not refused")
        sh(dst, "checkout", "-q", "sync3")
        (dst / "rules").rename(dst / "rules-real")
        os.symlink(dst / "rules-real", dst / "rules")
        sh(dst, "add", "-A")
        sh(dst, "commit", "-qm", "link")
        if not refused(write=True):
            problems.append("symlinked directory written through")
        try:
            tree(dst, "HEAD")
            problems.append("symlink in a tree not refused")
        except Refused:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PASS: sync-public self-test (refs not trees, rewrite scope, redaction, modes, delete, public-only review, "
          "leak, dirty, main, detached, behind, symlink, submodule, fetch failure, directory to file, review order)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--reviewed", nargs="+", metavar="FILE")
    ap.add_argument("--target", help="public repo path (default: maint/public-sync.json 'target')")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    try:
        return run(ROOT, a.target, write=a.write, reviewed=a.reviewed)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # anything unexpected is a failure, never "out of step"
        print(f"FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
