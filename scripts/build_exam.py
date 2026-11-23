import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.builder import build_exam_html


def main(argv):
    args = argv[1:]
    if not args:
        exam_files = sorted((ROOT / "exams").glob("*.json"))
        if not exam_files:
            print("No exam JSON files found in exams/", file=sys.stderr)
            return 1
        for ef in exam_files:
            out = ROOT / "artifacts" / (ef.stem + ".html")
            build_exam_html(ef, out)
            print(f"Built {out}")
        return 0

    exam_path = Path(args[0])
    out_path = Path(args[1]) if len(args) > 1 else ROOT / "artifacts" / (exam_path.stem + ".html")
    build_exam_html(exam_path, out_path)
    print(f"Built {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
