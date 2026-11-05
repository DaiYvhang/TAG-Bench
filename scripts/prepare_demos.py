#!/usr/bin/env python3
"""Build small, real audio examples from the author's local benchmark.

Requires ffmpeg only when rebuilding assets. End users need neither ffmpeg
nor the source workspace to view the bundled static page.
"""

import argparse
import array
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tagbench.io import read_records, write_json
from tagbench.metrics import parse_intervals, score_sample

EXAMPLES = [
    ("tagbench-0515", "Repeated acoustic events", "A door is opened and closed repeatedly.", "Four occurrences, one query. Compare recovering the events with predicting a single broad span."),
    ("tagbench-0005", "Word-level precision", "When is the word “WELL” spoken?", "A fraction of a second matters. Broad intervals can cover the word while still receiving a low IoU."),
    ("tagbench-0858", "Emotion in speech", "When does the speaker express disbelief and sympathy?", "Locate an emotional response in a longer spoken conversation."),
]
MODELS = [
    ("fireredaudio", "FireRedAudio"),
    ("moss-audio-8b-thinking", "MOSS-Audio-8B-Thinking"),
    ("gemini-3.1-pro", "Gemini-3.1-Pro"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audio-root", type=Path, required=True, help="Directory containing the original WAV files")
    ap.add_argument("--annotations", type=Path, required=True, help="Paper-era annotations from an external data directory")
    ap.add_argument("--predictions-dir", type=Path, required=True, help="External normalized prediction directory")
    args = ap.parse_args()
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is needed to rebuild the demo audio")
    annotations = {r["id"]: r for r in read_records(args.annotations)}
    model_rows = {model: {r["id"]: r for r in read_records(args.predictions_dir / f"{model}.jsonl")} for model, _ in MODELS}
    assets = ROOT / "docs/assets/audio"
    assets.mkdir(parents=True, exist_ok=True)
    examples = []
    for identity, title, short_query, description in EXAMPLES:
        annotation = annotations[identity]
        source = args.audio_root / Path(annotation["audio_path"]).name
        destination = assets / f"{identity}.mp3"
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-map_metadata", "-1", "-ac", "1", "-ar", "32000", "-codec:a", "libmp3lame", "-b:a", "96k", str(destination)], check=True)
        with wave.open(str(source), "rb") as stream:
            duration = stream.getnframes() / stream.getframerate()
        pcm = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(source), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], check=True, capture_output=True).stdout
        samples = array.array("h", pcm)
        if sys.byteorder != "little":
            samples.byteswap()
        bins = 240
        peaks = [max((abs(v) for v in samples[i * len(samples) // bins:(i + 1) * len(samples) // bins]), default=0) for i in range(bins)]
        maximum = max(peaks) or 1
        predictions = []
        for model, name in MODELS:
            scored = score_sample(model_rows[model][identity])
            predictions.append({
                "model": model, "name": name, "intervals": parse_intervals(scored["hyp_content"]) if not scored["parse_failed"] else [],
                **{k: scored[k] for k in ["hyp_content", "iou", "giou", "mae_mid", "n_hyp", "n_gt", "parse_failed"]},
            })
        examples.append({
            "id": identity, "title": title, "short_query": short_query, "description": description,
            "question": annotation["question"], "task_tag": annotation["task_tag"],
            "audio": f"assets/audio/{identity}.mp3", "duration": round(duration, 5),
            "ground_truth": parse_intervals(annotation["timestamp"]), "waveform": [round(p / maximum, 4) for p in peaks],
            "predictions": predictions,
            "provenance": {
                "source_audio": annotation["audio_path"], "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "demo_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "audio_transform": "Full recording, no time offset; mono MP3 at 32 kHz / 96 kbps for browser playback.",
                "prediction_source": "Archived normalized evaluation outputs; no new inference.",
            },
        })
    write_json(ROOT / "docs/assets/demos.json", examples)
    print(f"Prepared {len(examples)} audio examples, {sum((assets / (e['id'] + '.mp3')).stat().st_size for e in examples):,} bytes")


if __name__ == "__main__":
    main()
