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
LINE_CHARS = 400          # a longer line is cut in the snippet
MAX_BYTES = 2 * 1024 * 1024
# File names refused anywhere in a path, and folders refused as any path part. Add-only.
SECRET_NAMES = (".env", ".env.*", ".env*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks", "id_rsa*",
                "id_ed25519*", "id_ecdsa*", "id_dsa*", ".npmrc", ".pypirc", ".netrc", ".git-credentials",
                "credentials", "credentials.json", "*.kdbx")
SECRET_DIRS = ("secrets", ".ssh", ".aws", ".gnupg", ".git")
# Lines hidden inside a cited snippet, so a key kept in an ordinary source file is never rendered (owner decision
# 2026-11-19: hide, do not refuse, so the scan can be strict). The citation stays and is still verified. Add-only.
HIDDEN = "[line hidden: may hold a secret]"
# 1. Known token shapes, wherever they appear.
SECRET_SHAPES = {name: re.compile(p) for name, p in (
    ("github token", r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"),
    ("gitlab token", r"glpat-[A-Za-z0-9_-]{20,}"),
    ("npm token", r"\bnpm_[A-Za-z0-9]{30,}"),
    ("openai-style key", r"sk-[A-Za-z0-9_-]{20,}"),
    ("stripe-style key", r"\b(?:[sr]k|whsec)_(?:live_|test_)?[A-Za-z0-9]{16,}"),
    ("aws key id", r"\bA(?:KIA|SIA)[0-9A-Z]{16}\b"),
    ("google api key", r"AIza[0-9A-Za-z_-]{30,}"),
    ("slack token", r"xox[abeprs]-[A-Za-z0-9-]{10,}"),
    ("private key header", r"-----BEGIN [A-Z ]*PRIVATE KEY"),
    ("json web token", r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    ("key body line", r"^\s*[A-Za-z0-9+/]{40,}={0,2}\s*$"),
    ("long opaque literal", r"[\"'`][A-Za-z0-9+/_=-]{32,}[\"'`]"),
    ("url with a password", r"://[^/\s:@\"']*:[^/\s@\"']+@"),
    ("bearer or basic credential", r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"),
)}
# 2. A line that names a secret (any of these, any case, anywhere: `DB_PASS`, `client_secret`, `<password>`) and
#    holds anything that could be a value: a quote, or `=`, `:`, `=>` or `>` followed by more text. Strict on
#    purpose: hiding a harmless line (`self.password = password`) costs nothing but that line in the snippet.
SECRET_WORDS = ("pass", "pwd", "secret", "token", "apikey", "api_key", "api-key", "accesskey", "access_key",
                "private_key", "privatekey", "credential", "auth", "bearer", "salt", "signing", "session_key", "dsn",
                "database_url", "conn_str", "connection_string", "cookie")
_VALUE = re.compile(r"[\"'`]|(?:=>|:=|[:=>])\s*\S")
# 3. A line continuing an assignment to a secret name opened on the line above (`password = \`, `KEY = (`,
#    `"password":`), also when that line is just before the cited range.
_OPENS = re.compile(r"(?:=>|:=|[:=(\[{,\\])\s*$")


def _names_secret(text):
    low = text.lower()
    return any(w in low for w in SECRET_WORDS)


def secret_line(text, above=""):
    """Why one line of a cited file is hidden, or None. above is the line before it. Linear in the line's length."""
    for name, pat in SECRET_SHAPES.items():
        if pat.search(text):
            return name
    if _names_secret(text) and _VALUE.search(text):
        return "a secret name next to a value"
    if above and _names_secret(above) and _OPENS.search(above):
        return "continues a secret assignment from the line above"
    return None


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
    if b"\x00" in data:
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
    shown, hidden = [], []
    for n in range(src.line, min(last, src.line + SNIPPET_LINES - 1) + 1):
        text = lines[n - 1]
        if secret_line(text, lines[n - 2] if n > 1 else ""):
            hidden.append(n)
            text = HIDDEN
        shown.append(text if len(text) <= LINE_CHARS else text[:LINE_CHARS] + " …")
    src.snippet = "\n".join(shown)
    if hidden:
        return [{"severity": "info", "rule": "source-lines-hidden", "path": src.at,
                 "message": f"'{src.path}' line(s) {', '.join(map(str, hidden))} hidden in the snippet: they may hold a "
                            "secret"}]
    return []


# One line per shape (the reason it must give), lines that must be hidden, and lines that must be shown.
_SHAPE_CASES = {
    "github token": "t = 'ghp_" + "A" * 36 + "'",
    "gitlab token": "GL = glpat-" + "x" * 20,
    "npm token": "//registry/:_authToken npm_" + "a1" * 18,
    "openai-style key": "client = Client(sk-" + "a1" * 12 + ")",
    "stripe-style key": "hook = whsec_" + "4eC39HqLyjWDarjtT1zdp7dc",
    "aws key id": "aws_id = AKIA" + "IOSFODNN7EXAMPLE",
    "google api key": "maps = AIza" + "SyA" + "1" * 32,
    "slack token": "hook = xoxb-" + "1234567890-abcdefghij",
    "private key header": "-----BEGIN RSA PRIVATE" + " KEY-----",
    "json web token": "jwt = eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
    "key body line": "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7",
    "long opaque literal": "digest = '" + "0123456789abcdef" * 3 + "'",
    "url with a password": "CACHE = redis://:hunter2hunter2@cache",
    "bearer or basic credential": "curl -H Authorization: Bearer abcdefghijklmnop",
}
_HIDE = ['API_KEY = "ABCD1234EFGH5678"', 'TOTP_SECRET = "JBSWY3DPEHPK3PXP"', "POSTGRES_PASSWORD: rootpassword1",
         "JWT_SECRET: supersecretjwtkey2024", "SENDGRID_API_KEY: SG.abc.def", "ADMIN_PASSWORD: 12345678",
         "spring.datasource.password=Passw0rd.2024", 'SMTP_PASSWORD = """hunter2hunter2"""', "DB_PASS=hunter2",
         "<password>hunter2</password>", 'password = "my dog spot runs"', "TOKEN=abcdef123456", "password: changeme",
         'conn = connect(password="s3cr3tpass")', "self.password = password", 'token_type = "Bearer"',
         "auth_cookie => abc", "client_secret: x"]
_SHOW = ["def handle(request):", "def check_password(user, raw):", "if not secret:", "    return render(request)",
         "order = Order.objects.create(user=user, total=total)", "db.session.add(ticket)", "x = 1", "}",
         "for item in items:", 'url = f"{base}/v1/checkout/sessions"']


def self_test(tmp):
    """Problems with the secret scan and the reader, using the folder tmp for scratch files."""
    import time
    from types import SimpleNamespace
    problems = []
    for want, line in _SHAPE_CASES.items():
        if secret_line(line) != want:
            problems.append(f"secret shape '{want}' not found in {line!r} (got {secret_line(line)!r})")
    problems += [f"secret line not hidden: {x!r}" for x in _HIDE if not secret_line(x)]
    problems += [f"ordinary line hidden: {x!r} ({secret_line(x)})" for x in _SHOW if secret_line(x)]
    for word in SECRET_WORDS:
        if not secret_line(f"MY_{word.upper()}_X = 'v'"):
            problems.append(f"the secret word '{word}' is not acted on")
    start = time.monotonic()
    for long in ("a" * 50000, "token" + "a" * 50000, "token = " + "b" * 50000):
        secret_line(long)
    if time.monotonic() - start > 2:
        problems.append("the secret scan is slow on a long line")
    root = tmp / "scan"
    root.mkdir()
    (root / "cont.py").write_text("x = 1\nPASSWORD = (\n    'my dog spot runs'\n)\nAPI_KEY = \\\n  'abcdefgh'\ny = 2\n")
    (root / "late-nul.txt").write_bytes(b"a\n" * 10000 + b"\x00\n")
    (root / "wide.py").write_text("x = " + "y + " * 2000 + "1\n")
    def check(rel, line, end=None):
        src = SimpleNamespace(path=rel, line=line, end_line=end, at="t", snippet=None)
        return [d["rule"] for d in verify(root, src)], src
    for line in (2, 3, 6):
        rules, src = check("cont.py", line)
        if rules != ["source-lines-hidden"] or src.snippet != HIDDEN or "spot" in src.snippet:
            problems.append(f"secret line {line} of a continued assignment is not hidden: {rules} {src.snippet!r}")
    rules, src = check("cont.py", 1, 7)
    want = ["x = 1", HIDDEN, HIDDEN, ")", HIDDEN, HIDDEN, "y = 2"]
    if src.snippet != "\n".join(want) or rules != ["source-lines-hidden"]:
        problems.append(f"a range is not hidden line by line: {src.snippet!r}")
    if check("late-nul.txt", 1)[0] != ["source-not-text"]:
        problems.append("a NUL byte past the first 8 KB is not treated as binary")
    rules, src = check("wide.py", 1)
    if rules or not src.snippet or len(src.snippet) > LINE_CHARS + 2:
        problems.append("a very long line is not cut in the snippet")
    return problems
