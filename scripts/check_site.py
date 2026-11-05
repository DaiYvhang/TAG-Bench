#!/usr/bin/env python3
"""Check static links, paper display data, and audio example score integrity.

Uses only Python's standard library. Browser interaction checks are separate.
"""

import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tagbench.metrics import score_sample
from tagbench.paper import MODELS


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            if values["id"] in self.ids:
                raise ValueError(f"Duplicate HTML id: {values['id']}")
            self.ids.add(values["id"])
        for key in ("href", "src"):
            if values.get(key):
                self.links.append(values[key])


def main():
    root = ROOT / "docs"
    parser = PageLinks()
    parser.feed((root / "index.html").read_text(encoding="utf-8"))
    for link in parser.links:
        url = urlsplit(link)
        if url.scheme or url.netloc:
            continue
        if url.path:
            destination = (root / unquote(url.path)).resolve()
            if not destination.is_relative_to(root.resolve()) or not destination.is_file():
                raise ValueError(f"Missing or non-portable page asset: {link}")
        elif url.fragment and url.fragment not in parser.ids:
            raise ValueError(f"Missing page anchor: {link}")
    text = (root / "assets/data.js").read_text(encoding="utf-8")
    data, _ = json.JSONDecoder().raw_decode(text.split("window.TAGBENCH_DATA = ", 1)[1])
    if {m["id"] for m in data["models"]} != set(MODELS) or len(data["models"]) != 21:
        raise ValueError("The page must present exactly the 21 paper systems")
    if sum(s["n"] for s in data["subsets"]) != 1750:
        raise ValueError("Subset counts do not sum to the benchmark size")
    for model in data["models"]:
        overall, count = model["overall"], model["count"]
        if not math.isclose(overall["fail"] + overall["cvg"], 1):
            raise ValueError(f"Fail/Cvg mismatch: {model['id']}")
        if not math.isclose(count["accuracy"] + count["under"] + count["over"], 1):
            raise ValueError(f"Count partition mismatch: {model['id']}")
    demos = json.loads((root / "assets/demos.json").read_text(encoding="utf-8"))
    if demos != data["demos"]:
        raise ValueError("Demo data changed; rebuild assets/data.js")
    for example in demos:
        audio = (root / example["audio"]).resolve()
        if not audio.is_relative_to(root.resolve()) or not audio.is_file():
            raise ValueError(f"Missing or non-portable demo audio: {example['id']}")
        if hashlib.sha256(audio.read_bytes()).hexdigest() != example["provenance"]["demo_sha256"]:
            raise ValueError(f"Audio checksum mismatch: {example['id']}")
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in example["waveform"]):
            raise ValueError(f"Invalid waveform: {example['id']}")
        for prediction in example["predictions"]:
            scored = score_sample({"hyp_content": prediction["hyp_content"], "gt_content": example["ground_truth"]})
            for key in ["iou", "giou", "mae_mid", "n_hyp", "n_gt"]:
                if scored[key] is None and prediction[key] is None:
                    continue
                if not math.isclose(scored[key], prediction[key], rel_tol=0, abs_tol=1e-10):
                    raise ValueError(f"Demo metric mismatch: {example['id']} / {prediction['model']} / {key}")
    print(f"Static page OK: {len(parser.links)} links, 21 paper rows, {len(demos)} audio examples with verified scores and checksums")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"check_site: {error}", file=sys.stderr)
        raise SystemExit(1)

