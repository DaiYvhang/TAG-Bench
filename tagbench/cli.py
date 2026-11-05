"""The dependency-free `python -m tagbench` command line interface."""

import argparse
from pathlib import Path
import sys

from .io import align_predictions, read_records, write_json, write_jsonl
from .metrics import evaluate


def _alignment_args(parser):
    parser.add_argument("--annotations", required=True, type=Path)
    parser.add_argument("--model", default="generic", help="Legacy normalization profile, e.g. moss-audio-8b-thinking")
    parser.add_argument("--parser", choices=("legacy", "strict"), default="legacy")
    parser.add_argument("--prediction-field", help="Override automatic response field detection")
    parser.add_argument("--missing", choices=("error", "empty", "skip"), default="error")


def _align(args):
    return align_predictions(
        read_records(args.predictions), read_records(args.annotations), model=args.model,
        parser=args.parser, missing=args.missing, prediction_field=args.prediction_field,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="TAG-Bench temporal audio grounding evaluation")
    sub = parser.add_subparsers(dest="command", required=True)
    normalize = sub.add_parser("normalize", help="Align and normalize raw model responses")
    normalize.add_argument("--predictions", required=True, type=Path)
    normalize.add_argument("--output", required=True, type=Path)
    _alignment_args(normalize)
    score = sub.add_parser("evaluate", help="Score a self-contained canonical prediction file")
    score.add_argument("--predictions", required=True, type=Path)
    score.add_argument("--output-dir", required=True, type=Path)
    run = sub.add_parser("run", help="Normalize raw responses, align, and evaluate")
    run.add_argument("--predictions", required=True, type=Path)
    run.add_argument("--output-dir", required=True, type=Path)
    _alignment_args(run)
    args = parser.parse_args(argv)
    try:
        if args.command == "normalize":
            rows, audit = _align(args)
            write_jsonl(args.output, rows)
            write_json(args.output.with_suffix(".audit.json"), audit)
            print(f"Wrote {len(rows)} normalized rows to {args.output}")
            return 0
        if args.command == "run":
            rows, audit = _align(args)
        else:
            rows = read_records(args.predictions)
            audit = {"input_mode": "paired canonical rows", "coverage": "available rows only", "n_evaluated": len(rows)}
        summary, details = evaluate(rows)
        write_json(args.output_dir / "summary.json", summary)
        write_jsonl(args.output_dir / "per_sample.jsonl", details)
        write_json(args.output_dir / "audit.json", audit)
        if args.command == "run":
            write_jsonl(args.output_dir / "normalized.jsonl", rows)
        o = summary["overall"]
        print(f"n={o['n']}  mIoU={100*o['mIoU']:.2f}  R@0.5={100*o['Recall@0.5']:.2f}  "
              f"Fail={100*o['parse_failure_rate']:.2f}%  MAE coverage={100*o['MAE_Cvg']:.2f}%")
        print(f"Results: {args.output_dir}")
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"tagbench: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
