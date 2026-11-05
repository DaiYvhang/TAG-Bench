#!/usr/bin/env python3
"""Export portable annotations and paper-track predictions from the author's workspace.

Does not copy model code, credentials, virtual environments, or full audio.
Usage: python scripts/export_legacy.py --source-root /path/to/TAGBench
"""

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tagbench.io import audio_stem, read_records, write_json, write_jsonl


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/legacy", help="Generated data destination (default: ignored outputs/legacy/)")
    args = parser.parse_args()
    source, out = args.source_root, args.output_root
    annotations_path = source / "data/TAGBench/TAGBench.jsonl"
    annotations = read_records(annotations_path)
    stems = Counter(audio_stem(row["audio_path"]) for row in annotations)
    if any(n != 1 for n in stems.values()):
        raise ValueError("This release exporter requires unique audio stems")
    portable = []
    by_stem = {}
    for i, row in enumerate(annotations, 1):
        cleaned = {
            "id": f"tagbench-{i:04d}",
            "audio_path": "wavs/" + Path(row["audio_path"]).name,
            **{key: row[key] for key in ["question", "timestamp", "task_tag", "raw_query", "multi_target"]},
        }
        portable.append(cleaned)
        by_stem[audio_stem(row["audio_path"])] = cleaned
    write_jsonl(out / "data/annotations.jsonl", portable)
    model_files = sorted((source / "model_evaluation/004_eval_results/standard_result").glob("*.jsonl"))
    manifest = {
        "paper": "https://arxiv.org/abs/2609.01542v2",
        "annotation_source": "data/TAGBench/TAGBench.jsonl",
        "annotation_source_sha256": digest(annotations_path),
        "annotations_sha256": digest(out / "data/annotations.jsonl"),
        "n_annotations": len(portable),
        "id_policy": "tagbench-NNNN: 1-based row in the author-provided benchmark",
        "excluded_models": {"doubao-seed-2-0-lite": "Present in historical workspace; not in the 21-system paper track."},
        "models": {},
    }
    archived_gt = {}
    differences = {}
    for path in model_files:
        if path.stem in manifest["excluded_models"]:
            continue
        rows, seen = [], set()
        for row in read_records(path):
            b = by_stem[audio_stem(row["audio_path"])]
            if b["id"] in seen:
                raise ValueError(f"{path.name}: duplicate {b['id']}")
            seen.add(b["id"])
            if (row["bench_tag"], row["multi_target"]) != (b["task_tag"], b["multi_target"]):
                raise ValueError(f"{path.name}: metadata mismatch for {b['id']}")
            if b["id"] in archived_gt and archived_gt[b["id"]] != row["gt_content"]:
                raise ValueError(f"{path.name}: historical ground truths disagree for {b['id']}")
            archived_gt[b["id"]] = row["gt_content"]
            if row["gt_content"] != b["timestamp"]:
                differences[b["id"]] = {
                    "id": b["id"], "audio_path": b["audio_path"],
                    "paper_timestamp": row["gt_content"], "current_timestamp": b["timestamp"],
                }
            rows.append({"id": b["id"], **{key: row[key] for key in ["hyp_content", "gt_content", "bench_tag", "multi_target"]}})
        destination = out / "results/predictions" / path.name
        write_jsonl(destination, rows)
        manifest["models"][path.stem] = {
            "n": len(rows), "source": f"model_evaluation/004_eval_results/standard_result/{path.name}",
            "source_sha256": digest(path), "export_sha256": digest(destination),
            "missing_ids": [b["id"] for b in portable if b["id"] not in seen],
        }
    paper_annotations = [{**b, "timestamp": archived_gt[b["id"]]} for b in portable]
    write_jsonl(out / "data/annotations.paper.jsonl", paper_annotations)
    write_json(out / "results/annotation_differences.json", list(differences.values()))
    manifest["paper_annotations_sha256"] = digest(out / "data/annotations.paper.jsonl")
    manifest["n_annotation_differences"] = len(differences)
    write_json(out / "results/export_manifest.json", manifest)
    print(f"Exported {len(portable)} annotations and {len(manifest['models'])} model prediction files")


if __name__ == "__main__":
    main()
