import html
import json
from pathlib import Path

from src.schema import load_exam, validate_exam_data

WEB_DIR = Path(__file__).resolve().parent / "web"


def _safe_json_for_script(data):
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    return raw.replace("</script", r"<\/script")


def build_exam_html(exam_path, output_path):
    exam_data = load_exam(exam_path)
    errors = validate_exam_data(exam_data)
    if errors:
        raise ValueError("Invalid exam data: " + "; ".join(errors))

    template = (WEB_DIR / "template.html").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")
    grader_js = (WEB_DIR / "grader.js").read_text(encoding="utf-8")
    ui_js = (WEB_DIR / "ui.js").read_text(encoding="utf-8")

    rendered = (
        template.replace("__EXAM_TITLE__", html.escape(exam_data["meta"]["title"]))
        .replace("__STYLES_CSS__", styles)
        .replace("__EXAM_JSON__", _safe_json_for_script(exam_data))
        .replace("__GRADER_JS__", grader_js)
        .replace("__UI_JS__", ui_js)
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8", newline="\n")
    return out
