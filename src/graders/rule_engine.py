import json
import subprocess
from pathlib import Path

from src.graders.lean4 import grade_lean4_submission

ROOT = Path(__file__).resolve().parents[2]
GRADER_JS = ROOT / "src" / "web" / "grader.js"


def run_node_grader(exam_data, answers, options=None):
    payload = json.dumps(
        {
            "graderPath": str(GRADER_JS),
            "examData": exam_data,
            "answers": answers,
            "options": options or {},
        },
        ensure_ascii=False,
    )
    script = (
        "const fs = require('fs');"
        "const input = JSON.parse(fs.readFileSync(0, 'utf8'));"
        "const g = require(input.graderPath);"
        "const out = g.gradeExam(input.examData, input.answers, input.options);"
        "process.stdout.write(JSON.stringify(out));"
    )
    proc = subprocess.run(
        ["node", "-e", script],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node grader failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def grade_part7_cli(exam_data, submission_text, lean_bin=None, run_compiler=True):
    part7 = exam_data["parts"]["part7"]
    mode = part7["mode"]
    if mode == "lean4":
        return grade_lean4_submission(
            part7,
            submission_text,
            lean_bin=lean_bin,
            run_compiler=run_compiler,
        )
    report = run_node_grader(exam_data, {"part7": submission_text})
    detail = report["part7Detail"]
    detail["mode"] = mode
    return detail
