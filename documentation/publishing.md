# Preview and publication

**English** | [简体中文](publishing_zh.md) · [Documentation index](README.md)

The deliverable is a local source tree. No GitHub repository has been created,
no remote code has been pushed, and no hosted site has been deployed.

## Preview

Open `docs/index.html` directly. Scripts, styles, tables, and demo audio are
local files; there are no CDN dependencies. A local server is also supported:

```bash
python -m http.server 8000 --directory docs
```

Visit `http://localhost:8000`. Keep the entire `docs/assets/` directory with
the HTML. The page contains real audio and archived output excerpts; it does
not run a model or accept uploads.

## GitHub Pages

After putting these source files in your GitHub repository, either:

- In **Settings → Pages**, select **Deploy from a branch**, choose the branch
  containing the files, and select **`/docs`**. The `.nojekyll` file keeps the
  page as ordinary static content.
- Select **GitHub Actions** as the Pages source, then manually run the included
  **Publish demo page** workflow. It validates and uploads only `docs/`.
  The workflow is not triggered automatically by a push.

These steps follow [GitHub's Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
The regular **Checks** workflow runs Python tests and static-page integrity
checks. The page uses relative asset URLs, so repository subpaths work.

The code button initially links to the evaluation instructions on the page.
Once a real public repository URL exists, rebuild with `--repository-url` to
point it there. No repository or dataset download URL is guessed.

## Refresh paper tables

The page ships with its table display values. No experiment file is needed to
view or deploy it. To regenerate those values from an external summary:

```bash
python scripts/build_site.py --summary /path/to/summary_metrics.json
python scripts/check_site.py
```

`--repository-url` may be added with your actual `https://github.com/...`
address. The builder selects the 21 systems in `tagbench/paper.py`, excludes
the historical Doubao run, and embeds only the values used by the page. It
does not copy full result files. The input JSON may be the historical
`summary_metrics.json`, or an object with the same mapping under `models`.

## Refresh the three audio examples

`prepare_demos.py` is an optional maintenance helper requiring `ffmpeg`.
Provide external paper-era annotations with stable IDs, external standardized
predictions carrying those IDs, and the original WAV directory:

```bash
python scripts/prepare_demos.py \
  --annotations /path/to/annotations.paper.jsonl \
  --predictions-dir /path/to/predictions \
  --audio-root /path/to/wavs
python scripts/build_site.py --summary /path/to/summary_metrics.json
```

The helper copies no full dataset. It converts three entire recordings to
mono 32 kHz, 96 kbps MP3 without cropping or shifting timestamps. Waveforms
come from the source PCM. `demos.json` records source filenames, SHA-256
checksums, transformations, and the selected archived predictions. Ground
truths and demo scores are checked by `check_site.py`.

If needed, `export_legacy.py --source-root /path/to/TAGBench` reconstructs the
portable ID-bearing inputs in the ignored `outputs/legacy/` directory. It
separates current annotations from historical paper annotations and records
the one known GT difference. Full generated data and per-model results stay
outside the published project.

## Release metadata

The supplied materials did not identify a release license for TAG-Bench's
code or audio. No license was copied from SoulX-Transcriber. The owner can
add the intended code license and the appropriate audio/data attribution
when publishing. `CITATION.cff` identifies the paper without asserting a
license. The three demo recordings retain their original benchmark source
identity in `docs/assets/demos.json`.
