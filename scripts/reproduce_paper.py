#!/usr/bin/env python3
"""Recompute the 21-system paper track from an EXTERNAL prediction directory."""

import argparse
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tagbench.io import read_records, write_json, write_jsonl
from tagbench.metrics import evaluate
from tagbench.paper import MODELS, PAPER_URL


def compare(actual, expected, path=""):
    """Compare every reference value; return the number of scalar checks."""
    checked = 0
    for key, value in expected.items():
        location = f"{path}/{key}"
        if key not in actual:
            raise ValueError(f"Missing metric: {location}")
        result = actual[key]
        if isinstance(value, dict):
            checked += compare(result, value, location)
        else:
            checked += 1
            matches = (isinstance(result, (int, float)) and math.isclose(result, value, rel_tol=0, abs_tol=1e-10)) if isinstance(value, (int, float)) else result == value
            if not matches:
                raise ValueError(f"Metric mismatch {location}: computed {result!r}, reference {value!r}")
    return checked


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--predictions-dir", required=True, type=Path)
    ap.add_argument("--reference", type=Path, help="Optional external summary_metrics.json; mismatch exits nonzero")
    ap.add_argument("--output-dir", type=Path, default=ROOT / "outputs/paper")
    ap.add_argument("--per-sample", action="store_true", help="Also save per-query details in the output directory")
    args = ap.parse_args(argv)
    try:
        import json
        expected = json.loads(args.reference.read_text()) if args.reference else None
        if expected is not None and "models" in expected:
            expected = expected["models"]
        results, checks = {}, 0
        for model, (name, _) in MODELS.items():
            results[model], details = evaluate(read_records(args.predictions_dir / f"{model}.jsonl"))
            if expected is not None:
                checks += compare(results[model], expected[model], model)
            if args.per_sample:
                write_jsonl(args.output_dir / model / "per_sample.jsonl", details)
            o = results[model]["overall"]
            print(f"{name:27s} n={o['n']:4d}  mIoU={100*o['mIoU']:5.2f}")
        write_json(args.output_dir / "summary_metrics.json", results)
        write_json(args.output_dir / "verification.json", {
            "paper": PAPER_URL, "model_count": len(results), "scalar_checks": checks,
            "reference_checked": expected is not None, "all_reference_values_match": True if expected is not None else None,
            "n_by_model": {key: value["overall"]["n"] for key, value in results.items()},
            "coverage_policy": "Use archived available rows; Gemini has 1,749. No missing-row padding.",
        })
        print(f"Saved to {args.output_dir}" + (f"; {checks:,} reference values matched" if expected is not None else ""))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"reproduce_paper: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

