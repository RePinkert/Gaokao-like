import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graders.lean4 import check_lean_static, grade_lean4_submission, strip_lean_comments
from src.graders.rule_engine import run_node_grader
from src.schema import load_exam


def test_lean4_strip_comments_handles_line_and_nested_block():
    code = "theorem t : True := by -- sorry\n /- outer /- inner sorry -/ admit -/ trivial"
    cleaned = strip_lean_comments(code)
    assert "sorry" not in cleaned
    assert "admit" not in cleaned
    assert "trivial" in cleaned


def test_lean4_anti_cheat_rejects_sorry_admit_axiom_and_wrong_signature():
    exam = load_exam(ROOT / "exams" / "math-logic-lean4.json")
    p7 = exam["parts"]["part7"]

    ok_res = grade_lean4_submission(p7, p7["referenceSolution"], run_compiler=False)
    assert ok_res["passed"] is True

    for bad_code in (
        p7["signature"] + "\n  by sorry",
        p7["signature"] + "\n  by admit",
        "axiom cheat : False\n" + p7["referenceSolution"],
        "theorem de_morgan_or (P Q : Prop) : True := by trivial",
        p7["signature"] + "\n",
    ):
        res = grade_lean4_submission(p7, bad_code, run_compiler=False)
        assert res["passed"] is False, f"Should reject: {bad_code}"

    commented = "-- sorry is only in a comment\n" + p7["referenceSolution"]
    checks = check_lean_static(p7, commented)
    assert all(c["passed"] for c in checks)


def test_lean4_external_report_integration():
    exam = load_exam(ROOT / "exams" / "math-logic-lean4.json")
    p7 = exam["parts"]["part7"]
    answers = {"part7": {"code": p7["referenceSolution"], "quickChecks": {}}}

    ext_pass = {
        "mode": "lean4",
        "theoremName": p7["theoremName"],
        "passed": True,
        "message": "Lean 4 kernel verification passed.",
        "checks": [{"name": "Lean 4 kernel typecheck", "passed": True, "detail": "Exit 0"}],
    }
    rep_ok = run_node_grader(exam, answers, {"externalPart7": ext_pass})
    assert rep_ok["part7Detail"]["passed"] is True
    assert rep_ok["part7Detail"]["earned"] == p7["points"]

    ext_fail = {
        "mode": "lean4",
        "theoremName": p7["theoremName"],
        "passed": False,
        "message": "Type mismatch",
        "checks": [],
    }
    rep_bad = run_node_grader(exam, answers, {"externalPart7": ext_fail})
    assert rep_bad["part7Detail"]["passed"] is False
    assert rep_bad["part7Detail"]["earned"] == 0


def test_part7_cli_script_pass_and_fail():
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    cases = [
        ("math-logic-lean4.json", ["--static-only"]),
        ("prog-js-closures.json", []),
        ("nl-academic-english.json", []),
    ]
    for filename, extra in cases:
        exam_path = ROOT / "exams" / filename
        exam = load_exam(exam_path)
        p7 = exam["parts"]["part7"]

        good_file = artifacts / f"tmp_good_{exam_path.stem}.txt"
        bad_file = artifacts / f"tmp_bad_{exam_path.stem}.txt"
        good_file.write_text(p7["referenceSolution"], encoding="utf-8")
        bad_file.write_text(p7["negativeSolution"], encoding="utf-8")
        try:
            proc_good = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grade_part7.py"), str(exam_path), str(good_file)] + extra,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            assert proc_good.returncode == 0, proc_good.stdout + proc_good.stderr
            assert json.loads(proc_good.stdout)["passed"] is True

            proc_bad = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "grade_part7.py"), str(exam_path), str(bad_file)] + extra,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            assert proc_bad.returncode == 1
            assert json.loads(proc_bad.stdout)["passed"] is False
        finally:
            good_file.unlink(missing_ok=True)
            bad_file.unlink(missing_ok=True)
