# Paper provenance and reproduction notes

**English** | [简体中文](paper-provenance_zh.md) · [Documentation index](README.md)

Verified on 2026-11-04 against [arXiv v2](https://arxiv.org/abs/2609.01542v2), [the full v2 paper](https://arxiv.org/html/2609.01542v2), the author-provided `v3.1_arxiv_upload/Template.tex`, and the historical `metric_analysis/summary_metrics.json`.

The paper is **TAG-Bench: Benchmarking Temporal Audio Grounding in Large Audio Language Models**, by Yuhang Dai, Xin Shu, Zengxi Li, Lei Xie, Xiangang Li, and Jianwei Yu (Alibaba Token Foundry). Yuhang Dai and Xin Shu contributed equally. Version 1 was submitted on 2026-09-01; version 2 was submitted on 2026-09-02. Comparing all normalized HTML text in [v1](https://arxiv.org/html/2609.01542v1) and v2 found only the version/date change and removal of Jianwei Yu's corresponding-author marker and note. Experimental text and numbers were unchanged. The supplied local LaTeX retains the old author marker.

## Data and table checks

The benchmark has 1,750 query-recording pairs, eight subsets, 149.5 audio hours, 1,363 single-target queries, and 387 multi-target queries. In paper order, subset sizes are: word 279; acoustic event 301; acoustic description 260; semantic 180; rough semantic 161; emotion 129; long semantic 180; long acoustic description 260. The corresponding multi-target counts are 4, 126, 86, 8, 26, 45, 6, and 86.

The historical summary contains 22 models. The paper evaluates 21: exclude only `doubao-seed-2-0-lite`. The paper groups comprise 17 general-purpose audio LLMs, two omni-modal systems, and two temporal-awareness expert models. Group membership follows the paper; LLaMA-Omni2-14B belongs to the first group.

| Paper table | Historical summary fields |
| --- | --- |
| 1: composition | Benchmark counts and rounded duration statistics |
| 2: main results | `overall`, `by_multi_target`, and derived `Fail` |
| 3: subset mIoU | `by_task_tag.*.mIoU` |
| 4: gIoU, MAE, coverage | `overall` and `by_multi_target`: `mgIoU`, `MAE_mid`, `MAE_Cvg` |
| 5: interval counts | `by_multi_target`: `count_acc`, `count_under`, `count_over`, `avg_hyp_count` |
| 6–9: complete subset results | `by_task_tag`, with each consecutive table covering two subsets in paper order |

All **1,974 displayed metric cells** in local LaTeX Tables 2–9 were checked against the original summary at the paper's precision: 1,973 numerical values and one undefined MAE, with no differences. Online Tables 1–5 and metric definitions were cross-checked. Full historical per-model result files are kept outside this GitHub project; the website uses the displayed paper table values.

## Metric conventions

IoU uses the union of intervals, after overlapping intervals on each side are merged. Recall is the fraction of queries whose IoU reaches 0.3, 0.5, or 0.7. Count diagnostics compare merged prediction counts with ground-truth interval counts. Overall metrics give each evaluated query equal weight; they are not duration-weighted or equal-weight means of eight subsets.

Stored rates and mIoU use a 0–1 scale, `mgIoU` uses −1 to 1, `MAE_mid` uses seconds, and interval counts remain counts. Multiply rates and gIoU by 100 for the paper display. Undefined MAE remains `null`, displayed as a dash.

Parsing failure is derivable from every historical aggregate: `Fail = 1 - MAE_Cvg`; the count is `round(n * Fail)`, using that aggregate's actual `n`. This reproduces the paper's failure columns. FireRedAudio has 265/1,750 overall failures (15.1%) and 54/260 long-description failures (20.8%). Failure includes any response without a recovered timestamp, such as a refusal or no-event statement; these categories cannot be distinguished from the aggregate alone. Failed outputs score IoU 0, misses at every recall threshold, gIoU −1, and zero predicted intervals; they are excluded from midpoint MAE.

## Historical differences to preserve

- **One absent Gemini item:** `gemini-3.1-pro` has `overall.n = 1749`, single-target `n = 1363`, and multi-target `n = 386`. The missing item is `Istanbul_9000_9600.wav`, row 395 of the supplied benchmark (`tagbench-0395` in the export helper). Its acoustic-event subset has 300 items, including 125 multi-target items, compared with the benchmark's 301 and 126. The published rounded scores match these historical denominators. Exact reproduction must report this missing item and preserve the original coverage; filling it with an artificial failed prediction changes the result.
- **Literal empty sentinel:** the historical implementation recognizes the raw standardized string `0s~0s` as the empty-prediction sentinel. The differently formatted `0.00s~0.00s` is retained as a zero-time point prediction and participates in count/MAE statistics. Collapsing all zero-length strings into the sentinel changes coverage and MAE, even when mIoU is unchanged.
- **One changed ground truth:** item `semantic_000268_e19db90eee_15to20min` (line 1442 of the current local annotations) has `1187.20s~1190.10s`; historical standardized evaluation rows use `1190.20s~1193.10s`. Preserve the historical ground truth when reproducing paper scores and keep the current annotation as a separately identified input.
- **Old duration probe:** Figure 4's caption says its audio-duration panel used 1,471 available non-word recordings. That is the historical plotting probe, not the benchmark size. The current local audio inventory was checked separately and contains 1,750 regular audio files.

The eight subsets differ in source, query category, duration, and recurrence. Their score differences describe this benchmark mixture and do not isolate the causal effect of duration or query abstraction.

Historical source checksums (SHA-256):

- `summary_metrics.json`: `3cb8e6313e63b186c5139005eea770cd771ba640d3f526d4906309aa9f814538`
- `v3.1_arxiv_upload/Template.tex`: `a72505b561cd874ee0e53dfac90113041a2da540880832943a5d3e229c1f1b91`
