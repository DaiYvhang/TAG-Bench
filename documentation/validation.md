# Validation record

**English** | [简体中文](validation_zh.md) · [Documentation index](README.md)

Validated locally on 2026-11-04 with Python 3.12 and headless Chromium.

| Check | Result |
| --- | --- |
| Metric, parsing, and alignment unit tests | 19 passed |
| Historical 21-system aggregate comparison | 7,371 reference scalar values matched; absolute tolerance `1e-10` |
| Paper Tables 2–9 against the supplied experiment summary | 1,974 displayed cells matched at paper precision |
| Wheel build and installation into a separate directory | Passed |
| Installed-package CLI from outside the source tree | Synthetic example produced mIoU 50.00 and MAE coverage 66.67% |
| Static page links and assets | 18 links checked; all local references resolved |
| Paper display data | Exactly 21 systems and eight subsets summing to 1,750 queries |
| Demo audio and score provenance | Three SHA-256 checksums and nine prediction score sets checked |
| Browser interaction checks | 29 passed, no JavaScript runtime errors |

Browser checks covered HTTP loading, model search, empty search state, all three
model-group filters, subset sorting, occurrence-count ranking, CSV export,
failure-rate sorting, all three audio files and their durations, selected
interval playback, automatic stopping at the interval end, and BibTeX copying.
There was no document overflow at viewport widths 320, 390, 768, and 1,440 px.
Opening `docs/index.html` directly from disk was also checked. Desktop and
mobile screenshots were inspected during development.

The historical result comparison reads external files. Full model predictions,
benchmark annotations, generated aggregate files, and validation scratch data
are not distributed in this source tree. The browser page retains only the
paper display values and three selected examples.

GitHub-hosted CI and GitHub Pages deployment have not been run: no remote
repository has been created or modified. The workflow files are included for
the repository owner to use after upload.
