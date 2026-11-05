"""Portable JSON I/O and deterministic alignment with benchmark annotations."""

from collections import defaultdict
import json
from pathlib import Path

from .metrics import parse_intervals
from .parsing import normalize_prediction


def read_records(path):
    """Read JSONL, a JSON array, or concatenated JSON objects (legacy Gemini)."""
    text = Path(path).read_text(encoding="utf-8-sig")
    decoder = json.JSONDecoder()
    rows, offset = [], 0
    try:
        while offset < len(text):
            if text[offset].isspace():
                offset += 1
                continue
            value, offset = decoder.raw_decode(text, offset)
            rows.extend(value if isinstance(value, list) else [value])
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}:{error.lineno}:{error.colno}: {error.msg}") from error
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: each record must be a JSON object")
    return rows


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def audio_stem(path):
    return Path(str(path).replace("\\", "/")).stem


def normalized_question(value):
    return " ".join(str(value).split("Query:", 1)[-1].replace("( Including start time and end time.)", "").split())


def annotation_row(row, index):
    gt = row.get("timestamp", row.get("gt_content"))
    intervals = parse_intervals(gt)
    if not intervals or any(a == b for a, b in intervals):
        raise ValueError(f"Annotation {index}: missing or zero-duration ground truth")
    multi = row.get("multi_target", len(intervals) > 1)
    if not isinstance(multi, bool) or multi != (len(intervals) > 1):
        raise ValueError(f"Annotation {index}: invalid multi_target")
    return {
        **row,
        "id": str(row.get("id", f"tagbench-{index:04d}")),
        "gt_content": gt,
        "bench_tag": row.get("task_tag", row.get("bench_tag", "unspecified")),
        "multi_target": multi,
    }


def align_predictions(predictions, annotations, model="generic", parser="legacy", missing="error", prediction_field=None):
    """Join by stable ID, then unambiguous audio/query or audio/GT identity.

    The annotation always supplies ground truth and task metadata. Duplicates,
    unknown predictions, ambiguous matches, and absent response fields error.
    Missing annotations default to an error; explicit `empty` and `skip` modes
    are recorded in the returned audit. Unique audio stem is a last fallback.
    """
    if missing not in {"error", "empty", "skip"}:
        raise ValueError("missing must be error, empty, or skip")
    bench = [annotation_row(row, i) for i, row in enumerate(annotations, 1)]
    if not bench:
        raise ValueError("Annotation file is empty")
    by_id = {}
    by_audio = defaultdict(list)
    for row in bench:
        if row["id"] in by_id:
            raise ValueError(f"Duplicate annotation id: {row['id']}")
        by_id[row["id"]] = row
        if row.get("audio_path"):
            by_audio[audio_stem(row["audio_path"])].append(row)
    matched = {}
    fields = [prediction_field] if prediction_field else ["hyp_content", "response", "final_prediction", "prediction"]
    for i, row in enumerate(predictions, 1):
        if row.get("id") is not None:
            target = by_id.get(str(row["id"]))
            candidates = [target] if target else []
        else:
            candidates = by_audio.get(audio_stem(row.get("audio_path", "")), [])
            query = normalized_question(row.get("question", row.get("query", "")))
            query_matches = [b for b in candidates if query and query in {
                normalized_question(b.get("question", "")), normalized_question(b.get("raw_query", ""))
            }]
            if query_matches:
                candidates = query_matches
            if len(candidates) > 1:
                gt = row.get("gt_content", row.get("timestamp"))
                if gt is not None:
                    candidates = [b for b in candidates if parse_intervals(b["gt_content"]) == parse_intervals(gt)]
        if len(candidates) != 1:
            raise ValueError(f"Prediction {i}: expected one annotation match, found {len(candidates)}")
        target = candidates[0]
        identity = target["id"]
        if identity in matched:
            raise ValueError(f"Duplicate prediction for {identity}")
        field = next((key for key in fields if key in row), None)
        if field is None:
            raise ValueError(f"Prediction {i}: no response field; expected one of {fields}")
        canonical, status = normalize_prediction(row[field], model=model, parser=parser)
        matched[identity] = {
            "id": identity,
            "audio_path": target.get("audio_path", ""),
            "question": target.get("question", ""),
            "hyp_content": canonical,
            "gt_content": target["gt_content"],
            "bench_tag": target["bench_tag"],
            "multi_target": target["multi_target"],
            "parse_status": status,
            "raw_prediction": row[field],
        }
    missing_ids = [b["id"] for b in bench if b["id"] not in matched]
    if missing_ids and missing == "error":
        raise ValueError(f"Missing {len(missing_ids)} predictions (first: {missing_ids[:3]}). Use --missing empty or --missing skip explicitly.")
    output = []
    for b in bench:
        if b["id"] in matched:
            output.append(matched[b["id"]])
        elif missing == "empty":
            output.append({
                "id": b["id"], "audio_path": b.get("audio_path", ""),
                "question": b.get("question", ""), "hyp_content": "",
                "gt_content": b["gt_content"], "bench_tag": b["bench_tag"],
                "multi_target": b["multi_target"], "parse_status": "missing",
            })
    return output, {
        "model": model, "parser": parser, "missing_policy": missing,
        "n_annotations": len(bench), "n_received": len(predictions),
        "n_matched": len(matched), "n_evaluated": len(output),
        "n_parse_failed": sum(r.get("parse_status") == "failed" for r in output),
        "missing_ids": missing_ids,
    }

