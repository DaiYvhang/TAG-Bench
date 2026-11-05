# Data formats and alignment

**English** | [简体中文](data-format_zh.md) · [Documentation index](README.md)

All files are UTF-8 JSONL. The reader also accepts a JSON array and adjacent JSON objects, as found in some older Gemini exports. It never evaluates Python expressions.

## Annotations

```json
{
  "id": "sample-1",
  "audio_path": "wavs/sample-1.wav",
  "question": "When does the bell ring?",
  "timestamp": "1s~3s;5s~7s",
  "task_tag": "acoustic event",
  "multi_target": true
}
```

`timestamp` is required (`gt_content` is accepted as an alias). `multi_target` is a JSON boolean; when absent, it is derived from the number of annotated intervals. Inconsistent or non-boolean values are rejected. `task_tag` accepts any non-empty string; the paper uses the eight keys in `tagbench/paper.py`. `audio_path` and `question` are optional when matching by ID. Audio is not read during metric calculation.

If annotations have no `id`, their 1-based file row supplies `tagbench-0001`, `tagbench-0002`, and so on. These IDs are stable only while annotation order is unchanged.

## Predictions

```json
{"id":"sample-1","response":"1s~3s;5s~7s"}
```

Recognized response fields, in precedence order: `hyp_content`, `response`, `final_prediction`, `prediction`. `--prediction-field` selects another key. An absent response field is a schema error; an explicit empty string or `null` is a failed response.

For strict structured input:

```json
{"id":"sample-1","response":[[1,3],[5,7]]}
```

Run with `--parser strict`. Strict canonical strings must consist entirely of `Xs~Ys` segments separated by semicolons. Free-form model prose belongs to the `legacy` parser.

## Matching legacy files

1. A provided prediction ID must match an annotation ID. An unknown ID is an error; it never silently falls back to a filename.
2. Without an ID, matching uses the audio filename stem, ignoring directory and extension. This tolerates old absolute paths and `.flac` → `.wav` conversions.
3. If possible, narrow candidates using the normalized `question`/`query` against the annotation's `question`/`raw_query`. The legacy timing parenthesis and a `Query:` prefix are removed.
4. Ambiguous candidates may be narrowed using identical GT intervals. A unique audio stem is the final fallback. More than one remaining candidate is an error.

The supplied annotation is always the authority for GT, subset, and multiplicity; model-provided ground truth never overwrites it. Repeated model outputs for an item are errors. Deduplicate retries deliberately before evaluation.

## Canonical paired rows

```json
{"id":"sample-1","hyp_content":"1s~3s","gt_content":"1s~3s;5s~7s","bench_tag":"acoustic event","multi_target":true}
```

These rows can be scored directly with `python -m tagbench evaluate`. `id` is optional in this mode, but duplicate supplied IDs are rejected. `bench_tag` falls back to `task_tag`, or `unspecified` if neither is present.

## Outputs

| File | Contents |
| --- | --- |
| `summary.json` | `overall`, `by_task_tag`, `by_multi_target`, `single_by_tag`, `multi_by_tag` |
| `per_sample.jsonl` | Canonical inputs plus IoU, gIoU, midpoint MAE, interval counts and failure status |
| `normalized.jsonl` | Aligned responses with original text and explicit parse status (`run` only) |
| `audit.json` | Coverage, normalization settings, missing IDs, and input counts |

`normalize --output normalized.jsonl` writes `normalized.audit.json` beside it. Empty subgroups are `{}`; an aggregate with no valid MAE samples has `MAE_mid: null`, not NaN.
