# 预览与发布

[English](publishing.md) | **简体中文** · [文档目录](README_zh.md)

当前交付为本地源代码目录，尚未创建 GitHub 仓库、推送远程代码或部署托管网站。

## 预览

可以直接打开 `docs/index.html`。脚本、样式、表格和示例音频均为本地文件，不依赖 CDN。也可以启动本地服务器：

```bash
python -m http.server 8000 --directory docs
```

访问 `http://localhost:8000`。请将完整的 `docs/assets/` 目录与 HTML 一起保留。页面展示真实音频及历史输出节选，不运行模型，也不接受上传。

## GitHub Pages

将这些源文件放入自己的 GitHub 仓库后，可以选择以下任一方式：

- 在 **Settings → Pages** 中选择 **Deploy from a branch**，指定包含源文件的分支，并选择 **`/docs`**。`.nojekyll` 文件使页面作为普通静态内容发布。
- 将 Pages 的发布来源设为 **GitHub Actions**，然后手动运行附带的 **Publish demo page** 工作流。它会先验证，再仅上传 `docs/`。该工作流不会因代码推送而自动触发。

上述步骤遵循 [GitHub Pages 工作流文档](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。常规的 **Checks** 工作流会运行 Python 测试与静态页面完整性检查。页面使用相对资源 URL，因此支持部署在仓库对应的子路径下。

页面中的代码按钮默认指向本页的评测说明。确定实际公开仓库 URL 后，可在重新构建时通过 `--repository-url` 将按钮指向该仓库。项目不会猜测仓库或数据集下载地址。

## 更新论文结果表

页面已包含表格展示数值，查看或部署时不需要实验文件。如需根据外部汇总重新生成：

```bash
python scripts/build_site.py --summary /path/to/summary_metrics.json
python scripts/check_site.py
```

可额外添加 `--repository-url`，传入实际的 `https://github.com/...` 仓库地址。构建脚本选择 `tagbench/paper.py` 中的 21 个系统，排除历史 Doubao 实验，只嵌入页面使用的数值，不复制完整结果文件。输入 JSON 可以是历史 `summary_metrics.json`，也可以是将相同映射放在 `models` 键下的对象。

## 更新三个音频示例

`prepare_demos.py` 是可选的维护工具，需要 `ffmpeg`。请提供带有稳定 ID 的外部论文版标注、带有这些 ID 的外部标准化预测文件，以及原始 WAV 目录：

```bash
python scripts/prepare_demos.py \
  --annotations /path/to/annotations.paper.jsonl \
  --predictions-dir /path/to/predictions \
  --audio-root /path/to/wavs
python scripts/build_site.py --summary /path/to/summary_metrics.json
```

该工具不复制完整数据集，只将三段完整录音转成单声道、32 kHz、96 kbps 的 MP3，不裁剪音频，也不移动时间戳。波形来自源 PCM。`demos.json` 记录源文件名、SHA-256 校验值、转换方式以及选中的历史预测。`check_site.py` 会检查真实标注和示例分数。

如有需要，可用 `export_legacy.py --source-root /path/to/TAGBench` 在被 Git 忽略的 `outputs/legacy/` 目录中重建带 ID 的可移植输入。该工具会分别保存当前标注和论文实验时的历史标注，并记录已知的一条 GT 差异。完整生成数据和逐模型结果不进入发布项目。

## 发布元数据

提供的材料没有说明 TAG-Bench 代码或音频的发布许可证，也没有从 SoulX-Transcriber 复制许可证。项目所有者可在发布时补充所选代码许可证，以及适用的音频和数据来源声明。`CITATION.cff` 用于标识论文，不声明许可证。三个示例录音在 `docs/assets/demos.json` 中保留了原始基准来源信息。

