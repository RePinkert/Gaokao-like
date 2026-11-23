import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graders.rule_engine import grade_part7_cli
from src.schema import load_exam


def main(argv):
    args = argv[1:]
    static_only = False
    filtered = []
    for a in args:
        if a == "--static-only":
            static_only = True
        else:
            filtered.append(a)
    if len(filtered) < 2:
        print("Usage: python scripts/grade_part7.py <exam.json> <submission_file> [--static-only]", file=sys.stderr)
        return 2

    exam_data = load_exam(filtered[0])
    submission = Path(filtered[1]).read_text(encoding="utf-8")
    result = grade_part7_cli(exam_data, submission, run_compiler=not static_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
