import ast
import io
import os
import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TOOL_VERSION = "1"

CODE_EXTENSIONS = {
    ".py": "python",
    ".js": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".jsx": "js",
    ".ts": "js",
    ".tsx": "js",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".vbs": "vbs",
    ".cmd": "cmd",
    ".bat": "cmd",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".r": "hashline",
    ".fish": "hashline",
    ".sh": "hashline",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".cache",
    ".eggs",
    ".tox",
    "dist",
}

JS_REGEX_KEYWORDS = frozenset(
    "return throw case delete void typeof new in of yield await else do instanceof".split()
)
JS_REGEX_PRECEDING = frozenset("([{,:;=!?&|+-*%^~<>")
JS_WHITE = frozenset(" \t\r\n")

DIRECTIVE_PREFIXES = ("#requires",)


def read_text(path):
    return path.read_text(encoding="utf-8", errors="surrogateescape")


def write_text(path, text):
    path.write_text(text, encoding="utf-8", errors="surrogateescape", newline="")


def load_patterns(path):
    if not path.is_file():
        return []
    out = []
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(re.compile(line))
    return out


def matches_any(rel, patterns):
    return any(p.search(rel) for p in patterns)


def collect_files(root):
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-c", "-o", "--exclude-standard", "-z"],
            capture_output=True,
        )
    except OSError:
        proc = None
    if proc is not None and proc.returncode == 0:
        out = []
        for name in proc.stdout.decode("utf-8", "replace").split("\0"):
            if not name:
                continue
            full = root / name
            if full.is_file():
                out.append((full, name))
        if out:
            return out
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in sorted(dirnames) if d not in SKIP_DIRS]
        for name in sorted(filenames):
            full = Path(dirpath) / name
            out.append((full, full.relative_to(root).as_posix()))
    return out


def iter_files(root, patterns):
    for full, rel in collect_files(root):
        if matches_any(rel, patterns):
            continue
        if full.suffix.lower() in CODE_EXTENSIONS:
            yield full, rel


def python_docstring_spans(text, spans):
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    starts = []
    total = 0
    for line in lines:
        starts.append(total)
        total += len(line)
    starts.append(total)

    def to_offset(lineno, byte_col):
        line = lines[lineno - 1]
        col = len(line.encode("utf-8")[:byte_col].decode("utf-8", "ignore"))
        return starts[lineno - 1] + col

    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        first = body[0]
        if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)):
            continue
        if not isinstance(first.value.value, str):
            continue
        if not hasattr(first, "end_lineno") or first.end_lineno is None:
            continue
        start = to_offset(first.lineno, first.col_offset)
        end = to_offset(first.end_lineno, first.end_col_offset)
        spans.append((start, end, "pass" if len(body) == 1 else ""))


def python_spans(text):
    spans = []
    stream = io.StringIO(text)
    for tok in tokenize.generate_tokens(stream.readline):
        if tok.type == tokenize.COMMENT:
            start = _offset(text, tok.start)
            end = _offset(text, tok.end)
            spans.append((start, end, ""))
    python_docstring_spans(text, spans)
    return spans


def _offset(text, pos):
    line, col = pos
    if line <= 1:
        return col
    idx = 0
    count = 1
    while count < line:
        nxt = text.find("\n", idx)
        if nxt < 0:
            return len(text)
        idx = nxt + 1
        count += 1
    return idx + col


def js_spans(text):
    n = len(text)
    i = 0
    spans = []
    if text.startswith("#!"):
        end = text.find("\n")
        spans.append((0, n if end < 0 else end, ""))
        i = 0 if end < 0 else end + 1
    mode = "code"
    return_mode = "code"
    brace_depth = 0
    stack = []
    regex_ok = True
    tmpl_resume = False

    def read_ident(j):
        while j < n and (text[j].isalnum() or text[j] in "_$"):
            j += 1
        return j

    def read_num(j):
        while j < n and (text[j].isalnum() or text[j] in "._"):
            j += 1
        return j

    def scan_string(j, quote):
        while j < n:
            c = text[j]
            if c == "\\":
                j += 2
                continue
            if c == quote:
                return j + 1
            if c == "\n":
                return j
            j += 1
        return j

    def scan_template(j):
        while j < n:
            c = text[j]
            if c == "\\":
                j += 2
                continue
            if c == "`":
                return j + 1, False
            if c == "$" and j + 1 < n and text[j + 1] == "{":
                return j + 2, True
            j += 1
        return j, False

    def scan_regex(j):
        j += 1
        in_class = False
        while j < n:
            c = text[j]
            if c == "\\":
                j += 2
                continue
            if c == "\n":
                return -1
            if c == "[":
                in_class = True
            elif c == "]":
                in_class = False
            elif c == "/" and not in_class:
                j += 1
                while j < n and text[j].isalnum():
                    j += 1
                return j
            j += 1
        return -1

    while i < n:
        if mode == "line":
            end = i
            while end < n and text[end] != "\n":
                end += 1
            spans.append((i, end, ""))
            i = end
            mode = return_mode
            continue
        if mode == "block":
            end = text.find("*/", i + 2)
            if end < 0:
                spans.append((i, n, ""))
                i = n
            else:
                spans.append((i, end + 2, ""))
                i = end + 2
            mode = return_mode
            continue
        if mode == "sq":
            i = scan_string(i, "'")
            mode = return_mode
            continue
        if mode == "dq":
            i = scan_string(i, '"')
            mode = return_mode
            continue
        if mode == "tmpl":
            start = i if tmpl_resume else i + 1
            j, enter_expr = scan_template(start)
            if enter_expr:
                stack.append((mode, brace_depth))
                mode = "interp"
                brace_depth = 1
                regex_ok = True
            else:
                if stack:
                    mode, brace_depth = stack.pop()
                else:
                    mode = "code"
                    brace_depth = 0
                regex_ok = False
            i = j
            continue
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            return_mode = mode
            mode = "line"
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            return_mode = mode
            mode = "block"
            continue
        if c == "/" and regex_ok:
            j = scan_regex(i)
            if j > 0:
                i = j
                regex_ok = False
                continue
            regex_ok = False
            i += 1
            continue
        if c == "/":
            i += 1
            regex_ok = True
            continue
        if c == "'":
            return_mode = mode
            mode = "sq"
            i += 1
            continue
        if c == '"':
            return_mode = mode
            mode = "dq"
            i += 1
            continue
        if c == "`":
            stack.append((mode, brace_depth))
            mode = "tmpl"
            tmpl_resume = False
            continue
        if mode == "interp" and c == "{":
            brace_depth += 1
            i += 1
            continue
        if mode == "interp" and c == "}":
            brace_depth -= 1
            i += 1
            if brace_depth <= 0:
                if stack:
                    mode, brace_depth = stack.pop()
                else:
                    mode = "code"
                    brace_depth = 0
                tmpl_resume = mode == "tmpl"
                regex_ok = False
            continue
        if c.isalpha() or c in "_$":
            j = read_ident(i)
            regex_ok = text[i:j] in JS_REGEX_KEYWORDS
            i = j
            continue
        if c.isdigit():
            i = read_num(i)
            regex_ok = False
            continue
        if c in JS_WHITE:
            i += 1
            continue
        if c in JS_REGEX_PRECEDING:
            regex_ok = True
        elif c in ")]":
            regex_ok = False
        elif c == "}":
            regex_ok = True
        else:
            regex_ok = False
        i += 1

    return spans
def powershell_spans(text):
    n = len(text)
    i = 0
    spans = []

    def line_end(j):
        k = text.find("\n", j)
        return n if k < 0 else k

    while i < n:
        c = text[i]
        if c == "<" and i + 1 < n and text[i + 1] == "#":
            end = text.find("#>", i + 2)
            end = n if end < 0 else end + 2
            spans.append((i, end, ""))
            i = end
            continue
        if c == "#":
            end = line_end(i)
            spans.append((i, end, ""))
            i = end
            continue
        if c == "`":
            i += 2
            continue
        if c == "@" and i + 1 < n and text[i + 1] in "'\"":
            nl = line_end(i)
            if not text[i + 2 : nl].strip():
                terminator = "'" if text[i + 1] == "'" else '"'
                marker = "\n" + terminator + "@"
                end = text.find(marker, nl)
                if end < 0:
                    i = n
                else:
                    i = end + len(marker)
                continue
        if c == "'":
            j = i + 1
            while j < n:
                if text[j] == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        j += 2
                        continue
                    j += 1
                    break
                if text[j] == "\n":
                    break
                j += 1
            i = j
            continue
        if c == '"':
            j = i + 1
            while j < n:
                ch = text[j]
                if ch == "`":
                    j += 2
                    continue
                if ch == '"':
                    if j + 1 < n and text[j + 1] == '"':
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            i = j
            continue
        i += 1
    return spans


def vbs_spans(text):
    n = len(text)
    i = 0
    spans = []
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == '"':
                    if j + 1 < n and text[j + 1] == '"':
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            i = j
            continue
        if c == "'":
            end = n
            k = text.find("\n", i)
            if k >= 0:
                end = k
            spans.append((i, end, ""))
            i = end
            continue
        if text[i : i + 3].lower() == "rem":
            before = text[i - 1] if i > 0 else "\n"
            after = text[i + 3] if i + 3 < n else "\n"
            if before in "\n\r:" or before in " \t" and _rem_at_statement_start(text, i):
                if after in " \t\r\n":
                    end = n
                    k = text.find("\n", i)
                    if k >= 0:
                        end = k
                    spans.append((i, end, ""))
                    i = end
                    continue
        i += 1
    return spans


def _rem_at_statement_start(text, i):
    j = i - 1
    while j >= 0 and text[j] in " \t":
        j -= 1
    if j < 0:
        return True
    return text[j] in "\n\r:"


def cmd_spans(text):
    out = []
    offset = 0
    lines = text.splitlines(keepends=True)
    for line in lines:
        bare = line.rstrip("\r\n")
        body = bare.lstrip()
        leading = bare[: len(bare) - len(body)]
        hit = False
        if body.startswith("::"):
            hit = True
        else:
            word = body
            if word.startswith("@"):
                word = word[1:].lstrip()
            low = word.lower()
            if low == "rem" or (low.startswith("rem") and len(low) > 3 and low[3] in " \t"):
                hit = True
        if hit:
            out.append((offset, offset + len(line), ""))
        offset += len(line)
    return out


def hashline_spans(text):
    n = len(text)
    i = 0
    spans = []
    quote = None
    while i < n:
        c = text[i]
        if quote:
            if c == "\\" and quote != "'":
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"":
            quote = c
            i += 1
            continue
        if c == "#":
            end = n
            k = text.find("\n", i)
            if k >= 0:
                end = k
            spans.append((i, end, ""))
            i = end
            continue
        i += 1
    return spans


def css_spans(text):
    n = len(text)
    i = 0
    spans = []
    while i < n:
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            spans.append((i, end, ""))
            i = end
            continue
        i += 1
    return spans


def html_spans(text):
    n = len(text)
    spans = []
    cursor = 0
    lower = text.lower()
    while True:
        start = lower.find("<script", cursor)
        if start < 0:
            break
        open_end = lower.find(">", start)
        if open_end < 0:
            break
        close = lower.find("</script>", open_end)
        close_end = n if close < 0 else close
        body_start = open_end + 1
        for a, b, repl in js_spans(text[body_start:close_end]):
            spans.append((body_start + a, body_start + b, repl))
        cursor = close_end
        if close < 0:
            break
        cursor = close + len("</script>")
    style_cursor = 0
    while True:
        start = lower.find("<style", style_cursor)
        if start < 0:
            break
        open_end = lower.find(">", start)
        if open_end < 0:
            break
        close = lower.find("</style>", open_end)
        close_end = n if close < 0 else close
        body_start = open_end + 1
        for a, b, repl in css_spans(text[body_start:close_end]):
            spans.append((body_start + a, body_start + b, repl))
        style_cursor = close_end
        if close < 0:
            break
        style_cursor = close + len("</style>")
    i = 0
    while True:
        start = text.find("<!--", i)
        if start < 0:
            break
        end = text.find("-->", start + 4)
        end = n if end < 0 else end + 3
        spans.append((start, end, ""))
        i = end
    spans.sort()
    return spans


DISPATCH = {
    "python": python_spans,
    "js": js_spans,
    "powershell": powershell_spans,
    "vbs": vbs_spans,
    "cmd": cmd_spans,
    "hashline": hashline_spans,
    "css": css_spans,
    "html": html_spans,
}


def find_spans(path, text):
    kind = CODE_EXTENSIONS[path.suffix.lower()]
    spans = DISPATCH[kind](text)
    spans = [s for s in spans if not is_directive(text, s[0])]
    return merge_spans(spans)


def is_directive(text, start):
    body = text[start:].lstrip().lower()
    return any(body.startswith(prefix) for prefix in DIRECTIVE_PREFIXES)


def merge_spans(spans):
    merged = []
    for start, end, repl in sorted(spans, key=lambda item: (item[0], item[1])):
        if merged and start < merged[-1][1]:
            prev_start, prev_end, prev_repl = merged[-1]
            if end > prev_end:
                merged[-1] = (prev_start, end, prev_repl if prev_repl else repl)
            continue
        merged.append((start, end, repl))
    return merged


def strip_spans(text, spans):
    cleaned = sorted(spans, key=lambda item: item[0])
    out = text
    for start, end, repl in reversed(cleaned):
        out = out[:start] + repl + out[end:]
    return out


def validate_python(text):
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def validate_node(path, text):
    if shutil.which("node") is None:
        return None
    tmp = Path(os.environ.get("TEMP", ".")) / ("cc_validate_" + str(os.getpid()) + path.suffix)
    tmp.write_text(text, encoding="utf-8", newline="")
    try:
        proc = subprocess.run(
            ["node", "--check", str(tmp)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode == 0
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def validate_powershell(path, text):
    exe = shutil.which("powershell") or shutil.which("powershell.exe")
    if not exe:
        return None
    tmp = Path(os.environ.get("TEMP", ".")) / ("cc_validate_" + str(os.getpid()) + ".ps1")
    tmp.write_text(text, encoding="utf-8-sig", newline="\r\n")
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$t=$null;$e=$null;"
        "[void][System.Management.Automation.Language.Parser]::ParseFile('%s',[ref]$t,[ref]$e);"
        "if($e.Count -gt 0){exit 1};exit 0" % str(tmp).replace("'", "''")
    )
    try:
        proc = subprocess.run(
            [exe, "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode == 0
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def validate(path, original, stripped):
    kind = CODE_EXTENSIONS[path.suffix.lower()]
    if kind == "python":
        if not validate_python(original):
            return None
        return validate_python(stripped)
    if kind == "js":
        if path.suffix.lower() in {".ts", ".tsx", ".jsx"}:
            return None
        if not validate_node(path, original):
            return None
        return validate_node(path, stripped)
    if kind == "powershell":
        base = validate_powershell(path, original)
        if base is None:
            return None
        if not base:
            return None
        return validate_powershell(path, stripped)
    return None


def report(path, spans, text, limit=4):
    lines = text.splitlines()
    for idx, (start, end, repl) in enumerate(sorted(spans, key=lambda item: item[0])[:limit]):
        lineno = text.count("\n", 0, start) + 1
        body = text[start:end].strip()
        if len(body) > 70:
            body = body[:70] + "..."
        print("  %s:%d  %s" % (path, lineno, body.replace("\n", " ")))
    if len(spans) > limit:
        print("  %s  (+%d more)" % (path, len(spans) - limit))


def run_code_check(root, patterns):
    bad = 0
    total_files = 0
    total_spans = 0
    for full, rel in iter_files(root, patterns):
        try:
            text = read_text(full)
        except OSError:
            continue
        try:
            spans = find_spans(full, text)
        except (SyntaxError, tokenize.TokenError, ValueError) as exc:
            print("  %s  UNPARSEABLE: %s" % (rel, exc))
            bad += 1
            continue
        if spans:
            bad += 1
            total_spans += len(spans)
            print("%s  (%d)" % (rel, len(spans)))
            report(full.relative_to(root), spans, text)
        total_files += 1
    if bad:
        print("")
        print("NO-COMMENTS FAILED: %d file(s) carry comments" % bad)
        return 1
    print("NO-COMMENTS OK: %d file(s), 0 comments" % total_files)
    return 0


def run_docs_check(root, patterns, doc_patterns):
    bad = 0
    kept = 0
    for full, rel in collect_files(root):
        if not full.name.lower().endswith(".md"):
            continue
        if matches_any(rel, patterns):
            continue
        if "/" not in rel and full.name.lower() in {"readme.md", "agents.md"}:
            kept += 1
            continue
        if matches_any(rel, doc_patterns):
            kept += 1
            continue
        bad += 1
        print("  stray doc: %s" % rel)
    if bad:
        print("")
        print("DOCS FAILED: %d stray document(s); only README.md and AGENTS.md are allowed" % bad)
        return 1
    print("DOCS OK: %d file(s)" % kept)
    return 0


def run_strip(root, patterns):
    failed = []
    changed = 0
    skipped = []
    for full, rel in iter_files(root, patterns):
        try:
            original = read_text(full)
        except OSError:
            continue
        try:
            spans = find_spans(full, original)
        except (SyntaxError, tokenize.TokenError, ValueError) as exc:
            skipped.append("%s (%s)" % (rel, exc))
            continue
        if not spans:
            continue
        cleaned = strip_spans(original, spans)
        verdict = validate(full, original, cleaned)
        if verdict is False:
            failed.append(rel)
            continue
        if cleaned != original:
            write_text(full, cleaned)
            changed += 1
    if skipped:
        print("SKIPPED (cannot parse):")
        for item in skipped:
            print("  " + item)
    if failed:
        print("STRIP ABORTED for:")
        for item in failed:
            print("  " + item)
        return 1
    print("STRIP OK: %d file(s) rewritten" % changed)
    return 0


def main(argv):
    args = [a for a in argv[1:]]
    mode = "all"
    if args and args[0] in {"check", "strip", "docs", "all"}:
        mode = args.pop(0)
    root = Path(args[0]).resolve() if args else Path.cwd().resolve()
    here = Path(__file__).resolve().parent
    patterns = load_patterns(here / "no_comments_exempt.txt")
    doc_patterns = load_patterns(here / "docs_exempt.txt")
    if mode == "strip":
        return run_strip(root, patterns)
    if mode == "check":
        return run_code_check(root, patterns)
    if mode == "docs":
        return run_docs_check(root, patterns, doc_patterns)
    code = run_code_check(root, patterns)
    docs = run_docs_check(root, patterns, doc_patterns)
    if code or docs:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
