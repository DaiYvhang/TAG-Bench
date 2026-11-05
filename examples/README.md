These three records are **synthetic format examples**, not model outputs or
benchmark results. Audio files are not required to calculate the metrics.

From the repository root:

```bash
python -m tagbench run --annotations examples/annotations.jsonl \
  --predictions examples/predictions.jsonl --output-dir outputs/example
```

Expected mIoU: **50.0** on the 0–100 display scale. Two of three examples enter
MAE (coverage **66.67%**). The failed response remains in the denominator.

