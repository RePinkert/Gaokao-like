import copy
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.builder import build_exam_html
from src.graders.rule_engine import run_node_grader
from src.schema import VALID_DIMENSIONS, load_exam, validate_exam_data

EXAM_FILES = sorted((ROOT / "exams").glob("*.json"))


def _run_node_helper(exam_data, fn_name):
    grader_js = ROOT / "src" / "web" / "grader.js"
    payload = json.dumps({"graderPath": str(grader_js), "examData": exam_data}, ensure_ascii=False)
    script = (
        "const fs = require('fs');"
        "const input = JSON.parse(fs.readFileSync(0, 'utf8'));"
        "const g = require(input.graderPath);"
        f"process.stdout.write(JSON.stringify(g.{fn_name}(input.examData)));"
    )
    proc = subprocess.run(
        ["node", "-e", script],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(proc.stdout)


def test_all_exams_pass_schema_validation():
    assert len(EXAM_FILES) >= 3
    for ef in EXAM_FILES:
        data = load_exam(ef)
        errors = validate_exam_data(data)
        assert errors == [], f"{ef.name} failed schema: {errors}"


def test_invalid_exam_is_rejected():
    data = copy.deepcopy(load_exam(EXAM_FILES[0]))
    data["parts"]["part3"]["options"] = data["parts"]["part3"]["options"][:6]
    data["parts"]["part1"]["pairs"][0]["dimension"] = "invalid-dim"
    errors = validate_exam_data(data)
    assert any("part3.options" in e for e in errors)
    assert any("invalid dimension" in e for e in errors)


def test_js_syntax_check():
    for js_file in (ROOT / "src" / "web" / "grader.js", ROOT / "src" / "web" / "ui.js"):
        proc = subprocess.run(["node", "--check", str(js_file)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr


def test_golden_pass_and_negative_fail_for_all_exams():
    for ef in EXAM_FILES:
        data = load_exam(ef)
        golden = _run_node_helper(data, "buildGoldenAnswers")
        rep_ok = run_node_grader(data, golden, {"elapsedSeconds": 120})
        assert rep_ok["summary"]["earned"] == rep_ok["summary"]["maxPoints"], ef.name
        assert rep_ok["summary"]["accuracy"] == 100.0, ef.name
        assert rep_ok["weaknessMap"] == [], ef.name
        assert all(it["correct"] for it in rep_ok["items"]), ef.name
        for dim in VALID_DIMENSIONS:
            d = rep_ok["dimensions"][dim]
            assert not math.isnan(d["accuracy"])
            assert d["accuracy"] == 100.0
            assert d["itemCount"] > 0

        wrong = _run_node_helper(data, "buildWrongAnswers")
        rep_bad = run_node_grader(data, wrong, {"elapsedSeconds": 60})
        assert rep_bad["summary"]["accuracy"] < 50.0, ef.name
        assert rep_bad["part7Detail"]["passed"] is False, ef.name
        assert len(rep_bad["weaknessMap"]) > 0, ef.name
        for it in rep_bad["items"]:
            if it["part"] != "part7":
                assert it["correct"] is False, f"{ef.name} {it['id']} unexpectedly passed"


def test_receptive_productive_gap_pattern():
    data = load_exam(ROOT / "exams" / "nl-academic-english.json")
    golden = _run_node_helper(data, "buildGoldenAnswers")
    wrong = _run_node_helper(data, "buildWrongAnswers")
    mixed = copy.deepcopy(golden)
    mixed["part5"] = wrong["part5"]
    mixed["part7"] = wrong["part7"]
    rep = run_node_grader(data, mixed, {"elapsedSeconds": 300})
    assert any("Receptive-productive gap" in p for p in rep["patterns"])


def test_build_exam_html_self_contained():
    for ef in EXAM_FILES:
        out = ROOT / "artifacts" / (ef.stem + ".html")
        built = build_exam_html(ef, out)
        assert built.is_file()
        content = built.read_text(encoding="utf-8")
        assert "window.__EXAM_DATA__" in content
        assert "GaokaoGrader" in content
        assert data_id_present(ef, content)


def data_id_present(exam_file, html_text):
    data = load_exam(exam_file)
    return data["meta"]["id"] in html_text
