import json
from pathlib import Path

VALID_DOMAINS = {"natural-language", "programming", "mathematics", "hybrid"}
VALID_DIMENSIONS = {"lexicon", "morphosyntax", "discourse", "output"}
VALID_ERROR_OPS = {"add", "delete", "replace"}
VALID_PART7_MODES = {"js-unit", "lean4", "nl-rules"}


def _check_item_common(item, path, kp_ids, errors, seen_ids, seen_dims):
    if not isinstance(item, dict):
        errors.append(f"{path}: item must be an object")
        return
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        errors.append(f"{path}: missing string id")
    elif item_id in seen_ids:
        errors.append(f"{path}: duplicate item id {item_id}")
    else:
        seen_ids.add(item_id)
    kp = item.get("kp")
    if kp not in kp_ids:
        errors.append(f"{path}: unknown kp {kp!r}")
    dim = item.get("dimension")
    if dim not in VALID_DIMENSIONS:
        errors.append(f"{path}: invalid dimension {dim!r}")
    else:
        seen_dims.add(dim)
    pts = item.get("points")
    if not isinstance(pts, (int, float)) or pts <= 0:
        errors.append(f"{path}: points must be > 0")
    exp = item.get("explanation")
    if not isinstance(exp, str) or not exp.strip():
        errors.append(f"{path}: missing explanation")


def validate_exam_data(data):
    errors = []
    if not isinstance(data, dict):
        return ["root must be a JSON object"]

    meta = data.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta must be an object")
    else:
        for field in ("id", "title", "scale"):
            if not isinstance(meta.get(field), str) or not meta[field].strip():
                errors.append(f"meta.{field} must be a non-empty string")
        if meta.get("domain") not in VALID_DOMAINS:
            errors.append(f"meta.domain must be one of {sorted(VALID_DOMAINS)}")
        dur = meta.get("durationMinutes")
        if not isinstance(dur, int) or dur <= 0:
            errors.append("meta.durationMinutes must be a positive integer")

    kps = data.get("knowledgePoints")
    kp_ids = set()
    if not isinstance(kps, list) or not (5 <= len(kps) <= 12):
        errors.append("knowledgePoints must be a list of 5 to 12 entries")
    else:
        for idx, kp in enumerate(kps):
            p = f"knowledgePoints[{idx}]"
            if not isinstance(kp, dict):
                errors.append(f"{p}: must be an object")
                continue
            kid = kp.get("id")
            if not isinstance(kid, str) or not kid.strip():
                errors.append(f"{p}: missing id")
            elif kid in kp_ids:
                errors.append(f"{p}: duplicate kp id {kid}")
            else:
                kp_ids.add(kid)
            if not isinstance(kp.get("name"), str) or not kp["name"].strip():
                errors.append(f"{p}: missing name")
            if kp.get("dimension") not in VALID_DIMENSIONS:
                errors.append(f"{p}: invalid dimension {kp.get('dimension')!r}")
            if not isinstance(kp.get("remediation"), str) or not kp["remediation"].strip():
                errors.append(f"{p}: missing remediation")

    parts = data.get("parts")
    if not isinstance(parts, dict):
        errors.append("parts must be an object")
        return errors

    required_parts = ("part1", "part2", "part3", "part4", "part5", "part6", "part7")
    for name in required_parts:
        if not isinstance(parts.get(name), dict):
            errors.append(f"parts.{name} must be an object")

    seen_ids = set()
    seen_dims = set()

    p1 = parts.get("part1")
    if isinstance(p1, dict):
        pairs = p1.get("pairs")
        if not isinstance(pairs, list) or len(pairs) < 4:
            errors.append("parts.part1.pairs must contain at least 4 pairs")
        else:
            right_ids = set()
            for idx, item in enumerate(pairs):
                _check_item_common(item, f"part1.pairs[{idx}]", kp_ids, errors, seen_ids, seen_dims)
                if isinstance(item, dict):
                    for fld in ("left", "right", "rightId"):
                        if not isinstance(item.get(fld), str) or not item[fld].strip():
                            errors.append(f"part1.pairs[{idx}].{fld} must be a non-empty string")
                    rid = item.get("rightId")
                    if rid in right_ids:
                        errors.append(f"part1.pairs[{idx}]: duplicate rightId {rid}")
                    elif isinstance(rid, str):
                        right_ids.add(rid)

    p2 = parts.get("part2")
    if isinstance(p2, dict):
        passages = p2.get("passages")
        if not isinstance(passages, list) or not passages:
            errors.append("parts.part2.passages must be a non-empty list")
        else:
            for pidx, psg in enumerate(passages):
                pp = f"part2.passages[{pidx}]"
                if not isinstance(psg, dict):
                    errors.append(f"{pp}: must be an object")
                    continue
                for fld in ("id", "title", "body"):
                    if not isinstance(psg.get(fld), str) or not psg[fld].strip():
                        errors.append(f"{pp}.{fld} must be a non-empty string")
                items = psg.get("items")
                if not isinstance(items, list) or not items:
                    errors.append(f"{pp}.items must be a non-empty list")
                else:
                    for iidx, item in enumerate(items):
                        ip = f"{pp}.items[{iidx}]"
                        _check_item_common(item, ip, kp_ids, errors, seen_ids, seen_dims)
                        if isinstance(item, dict):
                            if not isinstance(item.get("stem"), str) or not item["stem"].strip():
                                errors.append(f"{ip}.stem must be a non-empty string")
                            opts = item.get("options")
                            if not isinstance(opts, dict) or len(opts) < 4:
                                errors.append(f"{ip}.options must have at least 4 entries")
                            elif item.get("answer") not in opts:
                                errors.append(f"{ip}.answer must be a key in options")

    p3 = parts.get("part3")
    if isinstance(p3, dict):
        if not isinstance(p3.get("passage"), str) or not p3["passage"].strip():
            errors.append("part3.passage must be a non-empty string")
        opts = p3.get("options")
        opt_ids = set()
        if not isinstance(opts, list) or len(opts) != 7:
            errors.append("part3.options must have exactly 7 options")
        else:
            for idx, opt in enumerate(opts):
                if not isinstance(opt, dict):
                    errors.append(f"part3.options[{idx}]: must be an object")
                    continue
                oid = opt.get("id")
                if not isinstance(oid, str) or not oid.strip():
                    errors.append(f"part3.options[{idx}]: missing id")
                elif oid in opt_ids:
                    errors.append(f"part3.options[{idx}]: duplicate option id {oid}")
                else:
                    opt_ids.add(oid)
                if not isinstance(opt.get("text"), str) or not opt["text"].strip():
                    errors.append(f"part3.options[{idx}]: missing text")
        items = p3.get("items")
        used_answers = set()
        if not isinstance(items, list) or len(items) != 5:
            errors.append("part3.items must have exactly 5 blanks")
        else:
            for idx, item in enumerate(items):
                ip = f"part3.items[{idx}]"
                _check_item_common(item, ip, kp_ids, errors, seen_ids, seen_dims)
                if isinstance(item, dict):
                    ans = item.get("answer")
                    if ans not in opt_ids:
                        errors.append(f"{ip}.answer {ans!r} not in part3.options")
                    elif ans in used_answers:
                        errors.append(f"{ip}.answer {ans!r} reused across blanks")
                    else:
                        used_answers.add(ans)
        distractors = opt_ids - used_answers
        dist_exp = p3.get("distractorExplanations")
        if len(distractors) != 2:
            errors.append("part3 must leave exactly 2 distractor options")
        elif not isinstance(dist_exp, dict):
            errors.append("part3.distractorExplanations must be an object")
        else:
            for d in sorted(distractors):
                if not isinstance(dist_exp.get(d), str) or not dist_exp[d].strip():
                    errors.append(f"part3.distractorExplanations missing explanation for {d}")

    p4 = parts.get("part4")
    if isinstance(p4, dict):
        if not isinstance(p4.get("passage"), str) or not p4["passage"].strip():
            errors.append("part4.passage must be a non-empty string")
        items = p4.get("items")
        if not isinstance(items, list) or len(items) < 5:
            errors.append("part4.items must contain at least 5 cloze blanks")
        else:
            for idx, item in enumerate(items):
                ip = f"part4.items[{idx}]"
                _check_item_common(item, ip, kp_ids, errors, seen_ids, seen_dims)
                if isinstance(item, dict):
                    opts = item.get("options")
                    if not isinstance(opts, dict) or len(opts) != 4:
                        errors.append(f"{ip}.options must have exactly 4 choices")
                    elif item.get("answer") not in opts:
                        errors.append(f"{ip}.answer must be a key in options")

    p5 = parts.get("part5")
    if isinstance(p5, dict):
        if not isinstance(p5.get("passage"), str) or not p5["passage"].strip():
            errors.append("part5.passage must be a non-empty string")
        items = p5.get("items")
        if not isinstance(items, list) or len(items) < 4:
            errors.append("part5.items must contain at least 4 fill-in blanks")
        else:
            for idx, item in enumerate(items):
                ip = f"part5.items[{idx}]"
                _check_item_common(item, ip, kp_ids, errors, seen_ids, seen_dims)
                if isinstance(item, dict):
                    acc = item.get("accepted")
                    if not isinstance(acc, list) or not acc or not all(isinstance(x, str) and x.strip() for x in acc):
                        errors.append(f"{ip}.accepted must be a non-empty list of strings")

    p6 = parts.get("part6")
    if isinstance(p6, dict):
        lines = p6.get("lines")
        line_nums = set()
        if not isinstance(lines, list) or not lines:
            errors.append("part6.lines must be a non-empty list")
        else:
            for idx, ln in enumerate(lines):
                if not isinstance(ln, dict) or not isinstance(ln.get("line"), int) or not isinstance(ln.get("text"), str):
                    errors.append(f"part6.lines[{idx}] must have integer line and string text")
                else:
                    line_nums.add(ln["line"])
        items = p6.get("items")
        if not isinstance(items, list) or len(items) < 4:
            errors.append("part6.items must contain at least 4 error-correction items")
        else:
            for idx, item in enumerate(items):
                ip = f"part6.items[{idx}]"
                _check_item_common(item, ip, kp_ids, errors, seen_ids, seen_dims)
                if isinstance(item, dict):
                    if item.get("line") not in line_nums:
                        errors.append(f"{ip}.line {item.get('line')!r} not in part6.lines")
                    if item.get("op") not in VALID_ERROR_OPS:
                        errors.append(f"{ip}.op must be one of {sorted(VALID_ERROR_OPS)}")
                    if not isinstance(item.get("target"), str) or not item["target"].strip():
                        errors.append(f"{ip}.target must be a non-empty string")
                    if not isinstance(item.get("fix"), str):
                        errors.append(f"{ip}.fix must be a string")

    p7 = parts.get("part7")
    if isinstance(p7, dict):
        _check_item_common(p7, "part7", kp_ids, errors, seen_ids, seen_dims)
        mode = p7.get("mode")
        if mode not in VALID_PART7_MODES:
            errors.append(f"part7.mode must be one of {sorted(VALID_PART7_MODES)}")
        for fld in ("prompt", "referenceSolution", "negativeSolution"):
            if not isinstance(p7.get(fld), str) or not p7[fld].strip():
                errors.append(f"part7.{fld} must be a non-empty string")
        if not isinstance(p7.get("starterCode"), str):
            errors.append("part7.starterCode must be a string")
        if mode == "js-unit":
            if not isinstance(p7.get("functionName"), str) or not p7["functionName"].strip():
                errors.append("part7.functionName must be a non-empty string")
            cases = p7.get("cases")
            if not isinstance(cases, list) or len(cases) < 3:
                errors.append("part7.cases must have at least 3 unit test cases")
        elif mode == "lean4":
            for fld in ("theoremName", "signature"):
                if not isinstance(p7.get(fld), str) or not p7[fld].strip():
                    errors.append(f"part7.{fld} must be a non-empty string")
        elif mode == "nl-rules":
            anchors = p7.get("requiredAnchors")
            if not isinstance(anchors, list) or len(anchors) < 2:
                errors.append("part7.requiredAnchors must have at least 2 regex anchors")
            min_w = p7.get("minWords")
            max_w = p7.get("maxWords")
            if not isinstance(min_w, int) or not isinstance(max_w, int) or min_w <= 0 or max_w < min_w:
                errors.append("part7.minWords and part7.maxWords must form a valid positive range")

    missing_dims = VALID_DIMENSIONS - seen_dims
    if missing_dims:
        errors.append(f"exam must cover all 4 linguistic dimensions; missing: {sorted(missing_dims)}")

    return errors


def load_exam(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
