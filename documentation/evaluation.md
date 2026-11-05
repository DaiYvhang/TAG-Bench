# Evaluation protocol

**English** | [简体中文](evaluation_zh.md) · [Documentation index](README.md)

The implementation follows [TAG-Bench arXiv v2, Section 4](https://arxiv.org/html/2609.01542v2#S4) and the author-provided `compute_miou.py`. It reproduces the original aggregates on positive-duration benchmark targets. Code paths contain no workstation-specific directories.

## Interval sets

Canonical timestamps are seconds: `1.20s~3.40s;8.00s~9.50s`. The metric layer also accepts `[[1.2, 3.4], [8.0, 9.5]]`. Endpoints must be finite and nonnegative, with start ≤ end. Ground-truth intervals must have positive duration. Predictions may be points.

Overlapping **and touching** intervals are merged on each side before scoring, counting, and computing midpoint error. Predictions are not clipped to the recording duration. The archived free-text parser rejects individual ranges reaching 12 hours; direct canonical inputs have no such parser cap.

For merged prediction set H and target set G:

- `IoU = duration(H ∩ G) / duration(H ∪ G)`.
- `gIoU = IoU − (duration(C) − duration(H ∪ G)) / duration(C)`, where C is the smallest single enclosing interval.
- Per-query midpoint MAE: for each merged target midpoint, take the distance to the closest predicted midpoint, then average over targets. One prediction may serve multiple targets; no bipartite assignment is performed.
- Count accuracy compares the number of merged prediction intervals with the number of merged target intervals. Under/over use `<` and `>` respectively.

The paper's count formula writes the annotated GT count. Its benchmark targets have no count-changing overlaps; the historical code merges both sides. This release follows the executable implementation.

## Aggregation and empty predictions

All metrics give each query equal weight. They are not weighted by duration or the number of target intervals. Overall mIoU is not the unweighted mean of the eight subset scores. Recall thresholds are inclusive: `IoU >= threshold`.

| Empty-prediction behavior | Value |
| --- | --- |
| IoU | 0 |
| Recall at 0.3, 0.5, 0.7 | Miss |
| gIoU | −1 |
| Number of predicted intervals | 0 |
| Midpoint MAE | `null`; excluded from its mean |

`MAE_Cvg` is the fraction entering the midpoint MAE mean. `parse_failure_rate = 1 − MAE_Cvg` for this benchmark. Explicitly missing records inserted by `--missing empty` contribute to this empty-prediction rate too; `audit.json` distinguishes absent records from received but unparseable answers.

All reported JSON scores use fractions (gIoU can be negative), MAE uses seconds, and counts use plain numbers. Multiply overlap, recall, coverage and count rates by 100 for paper-style display. Values are never rounded before aggregation.

## Historical parser compatibility

`legacy_parser.py` retains the author-provided deterministic cascade. It understands interval separators, start/end descriptions, bracketed arrays, clocks, isolated time points, and optional English number words. `parsing.py` applies the original thinking/conclusion/number-word profiles for the corresponding model IDs.

The legacy cascade is intentionally permissive: it can pair bare numbers, reverse two isolated times, or fall back to the full response if a stripped conclusion contains no ranges. These rules may recover unrelated numbers in unconstrained prose. They are retained to reproduce historical processing, not presented as semantic verification. For controlled new outputs, use canonical interval strings or arrays with `--parser strict`.

Legacy normalization rounds recovered endpoints to two decimal places, as in the original parser. Strict mode validates supplied canonical intervals without that quantization.

Only the literal standardized string **`0s~0s`** is the historical failure sentinel (outer whitespace is ignored). **`0.00s~0.00s` is an actual point prediction.** It receives zero IoU on positive-duration GT but contributes one interval and a midpoint. The distinction affects gIoU, MAE, coverage, and count metrics. Empty strings, empty lists, and `null` explicitly represent empty predictions in the new API.

`normalize` and `run` parse raw responses; `evaluate` reads canonical intervals directly. Reproduction should score archived standardized files with `evaluate` or `reproduce_paper.py`, without running them through the free-text parser again.

## Coverage

`run` checks predictions against the supplied annotation set. Missing records error by default. `--missing empty` evaluates the full annotation set; `--missing skip` evaluates only matched records and logs missing IDs. Unknown or duplicate predictions are always errors.

`evaluate` accepts self-contained paired prediction/GT rows and evaluates exactly those rows. It cannot infer absent benchmark records. The paper reproduction script intentionally uses this mode: Gemini has 1,749 archived rows; filling the missing item changes the historical scores.

Both the regression tests and external comparisons are described in [paper provenance](paper-provenance.md).
