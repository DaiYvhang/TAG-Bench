"""Interval-set metrics matching the archived TAG-Bench evaluation protocol.

No duration clipping or one-to-one interval assignment is performed. Adjacent
intervals are merged, as in the original implementation. All aggregation uses
unrounded per-query values, and every query has equal weight.
"""

from collections import defaultdict
import math
import re

THRESHOLDS = (0.3, 0.5, 0.7)
_RANGE = re.compile(r"\s*(\d+(?:\.\d+)?)s?\s*~\s*(\d+(?:\.\d+)?)s?\s*", re.I)


def parse_intervals(value):
    """Read canonical `Xs~Ys;...` or a list of [start, end] pairs.

    This is validation, not free-text extraction. Empty strings/lists/None are
    empty sets. The historical `0s~0s` sentinel is handled by score_sample.
    """
    if value is None or value == "":
        return []
    if isinstance(value, str):
        pairs = []
        for part in value.split(";"):
            match = _RANGE.fullmatch(part)
            if not match:
                raise ValueError(f"Invalid canonical interval: {part!r}")
            pairs.append(tuple(map(float, match.groups())))
    elif isinstance(value, (list, tuple)):
        pairs = []
        for pair in value:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError(f"Expected [start, end], got {pair!r}")
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in pair):
                raise ValueError(f"Interval endpoints must be numbers: {pair!r}")
            pairs.append(tuple(map(float, pair)))
    else:
        raise ValueError("Intervals must be a canonical string or a list of pairs")
    for a, b in pairs:
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a <= b):
            raise ValueError(f"Expected finite 0 <= start <= end, got {(a, b)!r}")
    return pairs


def merge_intervals(intervals):
    """Return sorted, non-overlapping intervals; touching endpoints also merge."""
    merged = []
    for a, b in sorted(parse_intervals(intervals)):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _overlap_and_union(h, g):
    intersection = sum(max(0.0, min(b, d) - max(a, c)) for a, b in h for c, d in g)
    union = sum(b - a for a, b in h) + sum(b - a for a, b in g) - intersection
    return intersection, union


def interval_iou(prediction, target):
    h, g = merge_intervals(prediction), merge_intervals(target)
    if not h or not g:
        return 0.0
    intersection, union = _overlap_and_union(h, g)
    # Zero-duration targets are not present in TAG-Bench and are rejected by
    # score_sample. Direct set calls define zero-measure overlap as zero.
    return intersection / union if union > 0 else 0.0


def generalized_iou(prediction, target):
    h, g = merge_intervals(prediction), merge_intervals(target)
    if not h or not g:
        return -1.0
    intersection, union = _overlap_and_union(h, g)
    enclosure = max(h[-1][1], g[-1][1]) - min(h[0][0], g[0][0])
    value = intersection / union if union > 0 else 0.0
    return value - (enclosure - union) / enclosure if enclosure > 0 else value


def midpoint_mae(prediction, target):
    """Mean distance from each merged GT midpoint to its nearest prediction."""
    h, g = merge_intervals(prediction), merge_intervals(target)
    if not h or not g:
        return None
    midpoints = [(a + b) / 2 for a, b in h]
    return sum(min(abs(p - (a + b) / 2) for p in midpoints) for a, b in g) / len(g)


def score_sample(row):
    if "gt_content" not in row or "hyp_content" not in row:
        raise ValueError("Each evaluated row requires gt_content and hyp_content")
    g = parse_intervals(row["gt_content"])
    if not g or any(a == b for a, b in g):
        raise ValueError("Ground truth must contain positive-duration intervals")
    h = parse_intervals(row["hyp_content"])
    if isinstance(row["hyp_content"], str) and row["hyp_content"].strip() == "0s~0s":
        h = []  # exact historical sentinel; 0.00s~0.00s is a valid point
    if row.get("parse_status") in {"failed", "missing"}:
        if h:
            raise ValueError("A failed/missing prediction cannot contain intervals")
    multi = row.get("multi_target", len(g) > 1)
    if not isinstance(multi, bool):
        raise ValueError("multi_target must be a JSON boolean, not a string or null")
    if multi != (len(g) > 1):
        raise ValueError("multi_target disagrees with the annotated target interval count")
    tag = row.get("bench_tag", row.get("task_tag", "unspecified"))
    if not isinstance(tag, str) or not tag.strip():
        raise ValueError("bench_tag/task_tag must be a non-empty string")
    return {
        **row,
        "bench_tag": tag,
        "multi_target": multi,
        "iou": interval_iou(h, g),
        "giou": generalized_iou(h, g),
        "mae_mid": midpoint_mae(h, g),
        "n_hyp": len(merge_intervals(h)),
        "n_gt": len(merge_intervals(g)),
        "parse_failed": not bool(h),
    }


def aggregate(samples):
    if not samples:
        return {}
    n = len(samples)
    mean = lambda key: sum(s[key] for s in samples) / n
    maes = [s["mae_mid"] for s in samples if s["mae_mid"] is not None]
    result = {
        "n": n,
        "mIoU": mean("iou"),
        **{f"Recall@{t}": sum(s["iou"] >= t for s in samples) / n for t in THRESHOLDS},
        "count_acc": sum(s["n_hyp"] == s["n_gt"] for s in samples) / n,
        "count_under": sum(s["n_hyp"] < s["n_gt"] for s in samples) / n,
        "count_over": sum(s["n_hyp"] > s["n_gt"] for s in samples) / n,
        "avg_hyp_count": mean("n_hyp"),
        "avg_gt_count": mean("n_gt"),
        "mgIoU": mean("giou"),
        "MAE_mid": sum(maes) / len(maes) if maes else None,
        "MAE_Cvg": len(maes) / n,
        "parse_failure_rate": sum(s["parse_failed"] for s in samples) / n,
        "n_parse_failed": sum(s["parse_failed"] for s in samples),
    }
    return result


def evaluate(rows):
    """Return (grouped summary, per-sample details), without rounding scores."""
    details = []
    seen = set()
    for index, row in enumerate(rows, 1):
        if row.get("id") is not None:
            key = str(row["id"])
            if key in seen:
                raise ValueError(f"Duplicate prediction id: {key}")
            seen.add(key)
        try:
            details.append(score_sample(row))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Sample {row.get('id', index)!r}: {error}") from error
    if not details:
        raise ValueError("Cannot evaluate an empty prediction file")
    by_tag = defaultdict(list)
    for sample in details:
        by_tag[sample["bench_tag"]].append(sample)
    summary = {
        "overall": aggregate(details),
        "by_task_tag": {tag: aggregate(v) for tag, v in sorted(by_tag.items())},
        "by_multi_target": {
            "single": aggregate([s for s in details if not s["multi_target"]]),
            "multi": aggregate([s for s in details if s["multi_target"]]),
        },
        "single_by_tag": {tag: aggregate([s for s in v if not s["multi_target"]]) for tag, v in sorted(by_tag.items())},
        "multi_by_tag": {tag: aggregate([s for s in v if s["multi_target"]]) for tag, v in sorted(by_tag.items())},
    }
    return summary, details
