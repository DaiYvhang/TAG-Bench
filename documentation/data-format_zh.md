# 数据格式与样本对齐

[English](data-format.md) | **简体中文** · [文档目录](README_zh.md)

所有文件均采用 UTF-8 编码的 JSONL 格式。读取器也支持 JSON 数组，以及部分旧版 Gemini 导出文件中连续拼接的 JSON 对象。读取过程不会执行 Python 表达式。

## 标注

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

`timestamp` 为必填字段，也支持别名 `gt_content`。`multi_target` 必须是 JSON 布尔值；未提供时，工具会根据标注区间数推导。与区间数不一致或非布尔类型的值会被拒绝。`task_tag` 接受任意非空字符串，论文使用的八个键名见 `tagbench/paper.py`。通过 ID 匹配时，`audio_path` 和 `question` 可以省略。计算指标时不读取音频。

如果标注没有 `id`，则按文件中从 1 开始的记录序号生成 `tagbench-0001`、`tagbench-0002` 等 ID。只有标注顺序保持不变，这些 ID 才保持稳定。

## 预测

```json
{"id":"sample-1","response":"1s~3s;5s~7s"}
```

工具按以下优先级识别回答字段：`hyp_content`、`response`、`final_prediction`、`prediction`。可使用 `--prediction-field` 指定其他字段。缺少回答字段属于数据格式错误；显式的空字符串或 `null` 则按失败回答处理。

严格模式下的结构化输入示例：

```json
{"id":"sample-1","response":[[1,3],[5,7]]}
```

运行时添加 `--parser strict`。严格模式下，标准区间字符串必须完全由 `Xs~Ys` 形式的片段组成，多个片段用分号分隔。自由文本形式的模型回答应使用 `legacy` 解析器。

## 旧格式文件的匹配规则

1. 如果预测提供了 ID，该 ID 必须匹配某条标注。未知 ID 会报错，不会自动退回到文件名匹配。
2. 如果没有 ID，则使用去掉扩展名的音频文件名进行匹配，忽略目录和扩展名。这样可以兼容旧绝对路径以及 `.flac` → `.wav` 转换。
3. 如果有可用的问题文本，则将规范化后的 `question`/`query` 与标注中的 `question`/`raw_query` 比较，进一步缩小候选范围。规范化会移除旧问题模板中的时间要求括注和 `Query:` 前缀。
4. 如果候选仍有歧义，可通过相同的真实标注区间进一步筛选。唯一的音频文件名是最后的匹配依据；如果仍剩多个候选，则报错。

真实标注（GT）、子集和目标数量始终以提供的标注文件为准，模型结果中的 GT 不会覆盖它。同一样本出现多条模型输出会报错，因此应在评测前明确处理重试产生的重复记录。

## 标准化的预测与标注配对记录

```json
{"id":"sample-1","hyp_content":"1s~3s","gt_content":"1s~3s;5s~7s","bench_tag":"acoustic event","multi_target":true}
```

这些记录可以直接通过 `python -m tagbench evaluate` 计分。在该模式下，`id` 可以省略；如果提供了 ID，则不允许重复。`bench_tag` 未提供时使用 `task_tag`，两者均未提供时使用 `unspecified`。

## 输出文件

| 文件 | 内容 |
| --- | --- |
| `summary.json` | `overall`、`by_task_tag`、`by_multi_target`、`single_by_tag`、`multi_by_tag` 分组汇总 |
| `per_sample.jsonl` | 标准化输入，以及 IoU、gIoU、中点 MAE、区间数和失败状态 |
| `normalized.jsonl` | 对齐后的回答，保留原始文本和显式解析状态；仅由 `run` 生成 |
| `audit.json` | 覆盖情况、规范化设置、缺失 ID 和输入数量 |

`normalize --output normalized.jsonl` 会在同一目录写入 `normalized.audit.json`。空子组使用 `{}`；如果某个分组没有有效的 MAE 样本，其 `MAE_mid` 为 `null`，而不是 NaN。

