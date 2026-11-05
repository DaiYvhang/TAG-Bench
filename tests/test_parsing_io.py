from pathlib import Path
import tempfile
import unittest

from tagbench.io import align_predictions, read_records
from tagbench.parsing import normalize_prediction


class ParsingTests(unittest.TestCase):
    def test_historical_formats(self):
        cases = {
            "The event is from 1.2 to 3.4 seconds.": "1.20s~3.40s",
            "[00:01 - 00:05]": "1.00s~5.00s",
            "00:05:662 - 00:06:900": "5.66s~6.90s",
            "Start time: 2.5, End time: 4.0": "2.50s~4.00s",
            "[[1, 2], [4, 5]]": "1.00s~2.00s;4.00s~5.00s",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(normalize_prediction(text), (expected, "ok"))

    def test_profiles_and_number_words(self):
        self.assertEqual(normalize_prediction("<think>8s~9s</think>2s~4s", model="moss-audio-8b-thinking")[0], "2.00s~4.00s")
        self.assertEqual(normalize_prediction("from two seconds to four seconds", model="llama-omni2-14b")[0], "2.00s~4.00s")

    def test_failures_and_strict_mode(self):
        self.assertEqual(normalize_prediction("I cannot identify the event."), ("", "failed"))
        self.assertEqual(normalize_prediction("__ERROR__ timeout"), ("", "failed"))
        self.assertEqual(normalize_prediction("0s~0s", parser="strict"), ("", "failed"))
        self.assertEqual(normalize_prediction("0.00s~0.00s", parser="strict"), ("0.00s~0.00s", "ok"))
        with self.assertRaises(ValueError):
            normalize_prediction("from 2 to 4 seconds", parser="strict")

    def test_strict_mode_preserves_subcentisecond_precision(self):
        self.assertEqual(normalize_prediction("0.12345s~0.12346s", parser="strict"), ("0.12345s~0.12346s", "ok"))
        self.assertEqual(normalize_prediction([[0.12345, 0.12346]], parser="strict"), ("0.12345s~0.12346s", "ok"))
        self.assertEqual(normalize_prediction([[0, 0]], parser="strict"), ("0.0s~0.0s", "ok"))


class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.bench = [
            {"id": "a", "audio_path": "wavs/a.wav", "timestamp": "1s~2s", "task_tag": "word", "question": "word a"},
            {"id": "b", "audio_path": "wavs/b.wav", "timestamp": "3s~4s", "task_tag": "emotion", "question": "happy"},
        ]

    def test_shuffled_ids_and_authoritative_gt(self):
        rows, audit = align_predictions([
            {"id": "b", "response": "3s~4s", "timestamp": "90s~99s"},
            {"id": "a", "response": "1s~2s"},
        ], self.bench)
        self.assertEqual([r["id"] for r in rows], ["a", "b"])
        self.assertEqual(rows[1]["gt_content"], "3s~4s")
        self.assertEqual(audit["n_matched"], 2)

    def test_missing_is_explicit(self):
        prediction = [{"id": "a", "response": "1s~2s"}]
        with self.assertRaises(ValueError):
            align_predictions(prediction, self.bench)
        rows, audit = align_predictions(prediction, self.bench, missing="empty")
        self.assertEqual(rows[1]["parse_status"], "missing")
        self.assertEqual(audit["missing_ids"], ["b"])
        rows, audit = align_predictions(prediction, self.bench, missing="skip")
        self.assertEqual(len(rows), 1)

    def test_portable_audio_matching(self):
        rows, _ = align_predictions([{"audio_path": "/old/location/a.flac", "final_prediction": "1s~2s", "query": "Query: word a"}], self.bench, missing="skip")
        self.assertEqual(rows[0]["id"], "a")

    def test_duplicates_unknown_and_missing_field_error(self):
        for predictions in [
            [{"id": "a", "response": "1s~2s"}] * 2,
            [{"id": "z", "response": "1s~2s"}],
            [{"id": "a"}],
        ]:
            with self.assertRaises(ValueError):
                align_predictions(predictions, self.bench, missing="skip")

    def test_ambiguous_basename_does_not_silently_match(self):
        duplicate = {**self.bench[0], "id": "c"}
        with self.assertRaises(ValueError):
            align_predictions([{"audio_path": "a.wav", "response": "1s~2s"}], self.bench + [duplicate], missing="skip")

    def test_concatenated_json(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "input.jsonl"
            p.write_text('{"a":1}{"a":2}\n', encoding="utf-8")
            self.assertEqual(len(read_records(p)), 2)


if __name__ == "__main__":
    unittest.main()
