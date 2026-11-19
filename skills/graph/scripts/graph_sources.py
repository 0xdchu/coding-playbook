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
# Secret content refused inside a cited range, so a key kept in an ordinary source file is not rendered. Add-only.
# Conservative on purpose: a false refusal costs the author one other line to cite; a miss publishes a key.
# 1. Known token shapes, wherever they appear.
SECRET_SHAPES = {name: re.compile(p) for name, p in (
    ("github token", r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"),
    ("openai-style key", r"sk-[A-Za-z0-9_-]{20,}"),
    ("stripe-style key", r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{10,}"),
    ("aws key id", r"\bA(?:KIA|SIA)[0-9A-Z]{16}\b"),
    ("google api key", r"AIza[0-9A-Za-z_-]{30,}"),
    ("slack token", r"xox[abeprs]-[A-Za-z0-9-]{10,}"),
    ("private key header", r"-----BEGIN [A-Z ]*PRIVATE KEY"),
    ("json web token", r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    ("key body line", r"^\s*[A-Za-z0-9+/]{40,}={0,2}\s*$"),
    ("long opaque literal", r"[\"'`][A-Za-z0-9+/_=-]{32,}[\"'`]"),
    ("url with a password", r"://[^/\s:@\"']+:[^/\s@\"']+@"),
    ("bearer or basic credential", r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"),
)}
# 2. A line that names a secret (any of these, any case, anywhere in an identifier or key) and also holds a value:
#    a string literal (other than an ALL_CAPS name such as an environment variable's), or an assigned value that
#    contains a digit or a symbol (a bare name like `password` or `settings.API_KEY` is not a value).
SECRET_WORDS = ("passw", "pwd", "secret", "token", "apikey", "api_key", "api-key", "accesskey", "access_key",
                "private_key", "privatekey", "credential", "auth", "bearer", "salt", "signing", "session_key", "dsn",
                "database_url", "conn_str", "connection_string", "cookie")
_LITERAL = re.compile(r"[\"'`]{1,3}([^\"'`\n]{4,})")
_ASSIGNED = re.compile(r"(?:=>|:=|[:=])\s*([^\s\"'`(\[{,;\\]+)")
_NAME_ONLY = re.compile(r"[A-Z][A-Z0-9_]*")
_NUMBER = re.compile(r"-?[0-9][0-9_.]*")
_LITERAL_WORDS = ("none", "null", "nil", "true", "false", "undefined", "return", "pass", "raise", "yield", "await",
                  "not", "lambda", "new", "function", "this", "self", "continue", "break", "else", "if", "await")
# 3. An assignment to a secret name continued on the next lines (`password = \`, `KEY = (`): checked on the
#    window of SECRET_CONTEXT lines before the range joined with the range.
_OPEN_ASSIGN = re.compile(r"(?:=>|:=|[:=])\s*[\\(\[{]+\s*$")
# How many lines before a cited range are read with it, so a literal continued from an assignment above is caught.
SECRET_CONTEXT = 2


def _plain_value(value):
    """True for a right-hand side that names something rather than holding a secret: an attribute path
    (`settings.API_KEY`), a number, null/true/false, or a name that itself names a secret (`token`, `hash_password`)."""
    low = value.lower()
    return ("." in value and not value.startswith(".")) or bool(_NUMBER.fullmatch(value)) or low in _LITERAL_WORDS \
        or any(w in low for w in SECRET_WORDS)


def secret_line(text):
    """Why one line of a cited file looks like it holds a secret, or None. Linear in the line's length."""
    for name, pat in SECRET_SHAPES.items():
        if pat.search(text):
            return name
    low = text.lower()
    if not any(w in low for w in SECRET_WORDS):
        return None
    for m in _LITERAL.finditer(text):
        if not _NAME_ONLY.fullmatch(m.group(1).strip()):
            return "a value next to a secret name"
    for m in _ASSIGNED.finditer(text):
        value = m.group(1).rstrip(")]};,")
        if value and not _plain_value(value):
            return "a value assigned to a secret name"
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
    first = max(1, src.line - SECRET_CONTEXT)
    for n in range(src.line, last + 1):
        why = secret_line(lines[n - 1])
        # a line before the range counts only through an assignment it opens and this line continues
        if why is None and n > first and _OPEN_ASSIGN.search(lines[n - 2]) and secret_line(lines[n - 2] + " 'v4lue'"):
            why = "a secret assignment continued from the line above"
        if why:
            return [{"severity": "error", "rule": "source-secret-content", "path": src.at,
                     "message": f"'{src.path}' line {n} looks like a secret ({why}); cite other lines "
                                "(lines naming a secret next to a value are refused, even harmless ones)"}]
    shown = [x if len(x) <= LINE_CHARS else x[:LINE_CHARS] + " …"
             for x in lines[src.line - 1:min(last, src.line + SNIPPET_LINES - 1)]]
    src.snippet = "\n".join(shown)
    return []


# One line per refusal reason (the reason it must give), lines that must be refused, and ordinary lines that must not.
_SHAPE_CASES = {
    "github token": "t = 'ghp_" + "A" * 36 + "'",
    "openai-style key": "client = Client('sk-" + "a1" * 12 + "')",
    "stripe-style key": "stripe_key: sk_live_" + "4eC39HqLyjWDarjtT1zdp7dc",
    "aws key id": "aws_id = AKIA" + "IOSFODNN7EXAMPLE",
    "google api key": "maps = 'AIza" + "SyA" + "1" * 32 + "'",
    "slack token": "hook = xoxb-" + "1234567890-abcdefghij",
    "private key header": "-----BEGIN RSA PRIVATE" + " KEY-----",
    "json web token": "jwt = eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
    "key body line": "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7",
    "long opaque literal": "digest = '" + "0123456789abcdef" * 3 + "'",
    "url with a password": "DATABASE_URL = postgres://app:hunter2hunter2@db/prod",
    "bearer or basic credential": "curl -H Authorization: Bearer abcdefghijklmnop",
}
_REFUSED = ['app.config["SECRET_KEY"] = "dev-secret-key-123"', 'SMTP_PASSWORD = """hunter2hunter2"""',
            "spring.datasource.password=p@ssw0rd!23", 'password = "my dog spot runs"', 'client_secret: "abc123def456"',
            "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY", "TOKEN=abcdef123456", "password: changeme",
            'conn = connect(password="s3cr3tpass")', '"api_key": "abcdef0123"', "auth_token = 'tok_12345678'"]
_ALLOWED = ["def handle(request):", "    token = get_token(request)", '    api_key = os.environ["API_KEY"]',
            "self.password = password", "stripe.api_key = settings.STRIPE_API_KEY", "password = None", "if not secret:",
            "TOKEN_TTL = 3600", 'return render(request, "checkout.html", {"order": order})',
            "password_hash = hash_password(raw)", "auth = Auth(app)", 'SECRET_KEY = os.environ.get("SECRET_KEY")',
            "if token is None: return None", "order = Order.objects.create(user=user, total=total)"]


def self_test(tmp):
    """Problems with the secret scan and the reader, using the folder tmp for scratch files."""
    import time
    from types import SimpleNamespace
    problems = []
    for want, line in _SHAPE_CASES.items():
        if secret_line(line) != want:
            problems.append(f"secret shape '{want}' not found in {line!r} (got {secret_line(line)!r})")
    problems += [f"secret not refused: {x!r}" for x in _REFUSED if not secret_line(x)]
    problems += [f"ordinary line refused: {x!r} ({secret_line(x)})" for x in _ALLOWED if secret_line(x)]
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
    for line in (3, 6):
        if check("cont.py", line)[0] != ["source-secret-content"]:
            problems.append(f"a secret continued onto line {line} is not refused")
    if check("cont.py", 1)[0] or check("cont.py", 7)[0]:
        problems.append("a line next to a refused one is refused too")
    if check("late-nul.txt", 1)[0] != ["source-not-text"]:
        problems.append("a NUL byte past the first 8 KB is not treated as binary")
    rules, src = check("wide.py", 1)
    if rules or not src.snippet or len(src.snippet) > LINE_CHARS + 2:
        problems.append("a very long line is not cut in the snippet")
    return problems
