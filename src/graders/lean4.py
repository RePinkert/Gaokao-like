import os
import re
import shutil
import subprocess
from pathlib import Path

DEFAULT_FORBIDDEN = ("sorry", "admit", "axiom", "unsafe", "implemented_by", "extern")


def strip_lean_comments(code):
    out = []
    i = 0
    n = len(code)
    while i < n:
        if code[i : i + 2] == "/-":
            depth = 1
            i += 2
            while i < n and depth > 0:
                if code[i : i + 2] == "/-":
                    depth += 1
                    i += 2
                elif code[i : i + 2] == "-/":
                    depth -= 1
                    i += 2
                else:
                    i += 1
            out.append(" ")
            continue
        if code[i : i + 2] == "--":
            while i < n and code[i] != "\n":
                i += 1
            continue
        out.append(code[i])
        i += 1
    return "".join(out)


def check_lean_static(part7, code):
    cleaned = strip_lean_comments(str(code or ""))
    checks = []
    forbidden = part7.get("forbiddenTokens") or list(DEFAULT_FORBIDDEN)
    for tok in forbidden:
        hit = re.search(r"\b" + re.escape(tok) + r"\b", cleaned) is not None
        checks.append(
            {
                "name": f"Forbid token: {tok}",
                "passed": not hit,
                "detail": "Clean" if not hit else f"Detected forbidden token {tok}",
            }
        )
    norm_code = re.sub(r"\s+", " ", cleaned).strip()
    norm_sig = re.sub(r"\s+", " ", str(part7.get("signature", ""))).strip()
    sig_ok = bool(norm_sig) and norm_sig in norm_code
    checks.append(
        {
            "name": "Exact theorem signature",
            "passed": sig_ok,
            "detail": "Signature matched" if sig_ok else f"Missing exact signature: {norm_sig}",
        }
    )
    has_body = False
    if sig_ok:
        idx = norm_code.index(norm_sig)
        tail = norm_code[idx + len(norm_sig) :].strip()
        has_body = len(tail) >= 2
    checks.append(
        {
            "name": "Non-empty proof body",
            "passed": has_body,
            "detail": "Proof body present" if has_body else "Proof body is empty",
        }
    )
    return checks


def grade_lean4_submission(part7, code, lean_bin=None, run_compiler=True, work_dir=None):
    static_checks = check_lean_static(part7, code)
    static_ok = all(c["passed"] for c in static_checks)
    report = {
        "mode": "lean4",
        "theoremName": part7["theoremName"],
        "passed": False,
        "compilerRan": False,
        "message": "",
        "checks": list(static_checks),
    }
    if not static_ok:
        report["message"] = "Static anti-cheat or theorem signature check failed."
        return report

    if not run_compiler:
        report["passed"] = True
        report["message"] = "Static anti-cheat and signature checks passed (compiler skipped)."
        return report

    exe = lean_bin or shutil.which("lean")
    if not exe:
        report["passed"] = False
        report["message"] = "Lean 4 executable not found on PATH; run with --static-only or install Lean 4."
        return report

    base = Path(work_dir) if work_dir else Path(__file__).resolve().parents[2] / "artifacts"
    base.mkdir(parents=True, exist_ok=True)
    tmp_file = base / f"part7_check_{os.getpid()}.lean"
    tmp_file.write_text(str(code), encoding="utf-8", newline="\n")
    try:
        proc = subprocess.run(
            [exe, str(tmp_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        report["passed"] = False
        report["message"] = f"Lean 4 invocation failed: {exc}"
        return report
    finally:
        try:
            tmp_file.unlink()
        except OSError:
            pass

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    has_sorry_warn = "declaration uses 'sorry'" in combined or "uses 'sorry'" in combined
    ok = proc.returncode == 0 and not has_sorry_warn
    report["compilerRan"] = True
    report["passed"] = ok
    report["checks"].append(
        {
            "name": "Lean 4 kernel typecheck",
            "passed": ok,
            "detail": "Exit 0 with zero sorry warnings" if ok else combined.strip()[:300],
        }
    )
    report["message"] = "Lean 4 kernel verification passed." if ok else "Lean 4 kernel verification failed."
    return report
