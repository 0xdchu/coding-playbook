#!/usr/bin/env python3
"""Read-only, contained reading of the `path:line` sources a diagram cites.

A cited path must stay inside --repo-root (no absolute path, no `..`, no symlink that leaves the root), must not be a
secret-shaped file (refused before it is opened), must be a regular text file, and its line range must exist. A verified
source gets a snippet of at most SNIPPET_LINES lines. Nothing is ever written.
"""
import fnmatch
import os
import re

SNIPPET_LINES = 30
MAX_BYTES = 2 * 1024 * 1024
# File names refused anywhere in a path, and folders refused as any path part. Add-only.
SECRET_NAMES = (".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks", "id_rsa*",
                "id_ed25519*", "id_ecdsa*", "id_dsa*", ".npmrc", ".pypirc", ".netrc", ".git-credentials",
                "credentials", "credentials.json", "*.kdbx")
SECRET_DIRS = ("secrets", ".ssh", ".aws", ".gnupg", ".git")
# Text shapes refused inside a cited range, so a key kept in an ordinary source file is not rendered. Add-only.
SECRET_TEXT = [re.compile(p) for p in (
    r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_[A-Za-z0-9_]{20,}", r"sk-[A-Za-z0-9_-]{20,}", r"sk-ant-[A-Za-z0-9_-]{10,}",
    r"AKIA[0-9A-Z]{16}", r"AIza[0-9A-Za-z_-]{30,}", r"xox[abprs]-[A-Za-z0-9-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)\b[\"']?\s*[:=]\s*[\"'][^\"'\s]{6,}[\"']")]


def secret_reason(rel):
    """Why rel is refused as secret-shaped, or None."""
    parts = rel.replace("\\", "/").split("/")
    for part in parts[:-1]:
        if part.lower() in SECRET_DIRS:
            return f"inside a secret folder '{part}'"
    name = parts[-1].lower()
    for pat in SECRET_NAMES:
        if fnmatch.fnmatchcase(name, pat):
            return f"secret-shaped file name (matches '{pat}')"
    return None


def resolve(root, rel):
    """(absolute real path, None) or (None, (rule, message))."""
    if not isinstance(rel, str) or not rel or "\x00" in rel:
        return None, ("source-bad-path", "empty or invalid path")
    norm = rel.replace("\\", "/")
    if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":"):
        return None, ("source-outside-root", f"'{rel}' is absolute; cite a path relative to the repo root")
    if any(p == ".." for p in norm.split("/")):
        return None, ("source-outside-root", f"'{rel}' leaves the repo root with '..'")
    why = secret_reason(norm)
    if why:
        return None, ("source-secret", f"'{rel}' is refused: {why}")
    real_root = os.path.realpath(root)
    real = os.path.realpath(os.path.join(real_root, *[p for p in norm.split("/") if p not in ("", ".")]))
    if os.path.commonpath([real_root, real]) != real_root:
        return None, ("source-outside-root", f"'{rel}' resolves outside the repo root (a symlink leaves it)")
    why = secret_reason(os.path.relpath(real, real_root).replace(os.sep, "/"))
    if why:
        return None, ("source-secret", f"'{rel}' points at a refused file: {why}")
    if not os.path.isfile(real):
        return None, ("source-missing", f"'{rel}' is not a file in the repo root")
    return real, None


def read_lines(real):
    """The file's lines, or (None, message) when it is too large or not text."""
    if os.path.getsize(real) > MAX_BYTES:
        return None, f"larger than {MAX_BYTES} bytes"
    with open(real, "rb") as f:
        data = f.read(MAX_BYTES + 1)
    if b"\x00" in data[:8192]:
        return None, "a binary file"
    return data.decode("utf-8", errors="replace").splitlines(), None


def verify(root, src):
    """Check one graph_ir.Source against root; fill src.snippet. Returns a list of diagnostics."""
    real, problem = resolve(root, src.path)
    if problem:
        return [{"severity": "error", "rule": problem[0], "path": src.at, "message": problem[1]}]
    lines, why = read_lines(real)
    if lines is None:
        return [{"severity": "error", "rule": "source-not-text", "path": src.at, "message": f"'{src.path}' is {why}"}]
    last = src.end_line or src.line
    if src.line > len(lines) or last > len(lines):
        return [{"severity": "error", "rule": "source-line-past-end", "path": src.at,
                 "message": f"'{src.path}' has {len(lines)} lines; cited {src.line}" + (f"-{last}" if last != src.line else "")}]
    for n in range(src.line, last + 1):
        if any(p.search(lines[n - 1]) for p in SECRET_TEXT):
            return [{"severity": "error", "rule": "source-secret-content", "path": src.at,
                     "message": f"'{src.path}' line {n} looks like a secret (a token, key or password literal); "
                                "cite other lines"}]
    shown = lines[src.line - 1:min(last, src.line + SNIPPET_LINES - 1)]
    src.snippet = "\n".join(shown)
    return []
