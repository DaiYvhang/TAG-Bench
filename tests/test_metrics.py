import unittest

from tagbench.metrics import evaluate, generalized_iou, interval_iou, merge_intervals, midpoint_mae


def row(hyp, gt="1s~3s", **extra):
    return {"hyp_content": hyp, "gt_content": gt, **extra}


class MetricTests(unittest.TestCase):
    def test_union_merging_and_missing_occurrence(self):
        self.assertEqual(merge_intervals([(1, 3), (2, 4), (4, 5)]), [(1, 5)])
        self.assertAlmostEqual(interval_iou([(1, 3)], [(1, 3), (5, 7)]), 0.5)

    def test_generalized_iou_disjoint(self):
        self.assertAlmostEqual(generalized_iou([(1, 2)], [(4, 5)]), -0.5)

    def test_nearest_midpoint_not_bipartite_assignment(self):
        self.assertEqual(midpoint_mae([(4, 6)], [(0, 2), (8, 10)]), 4)

    def test_failure_stays_in_denominator(self):
        summary, _ = evaluate([row("1s~3s"), row("0s~0s")])
        o = summary["overall"]
        self.assertEqual(o["mIoU"], 0.5)
        self.assertEqual(o["Recall@0.5"], 0.5)
        self.assertEqual(o["MAE_mid"], 0)
        self.assertEqual(o["MAE_Cvg"], 0.5)
        self.assertEqual(o["parse_failure_rate"], 0.5)
        self.assertEqual(o["mgIoU"], 0)
        self.assertEqual(o["count_under"], 0.5)

    def test_zero_point_is_distinct_from_failure_sentinel(self):
        summary, details = evaluate([row("0.00s~0.00s"), row("0s~0s")])
        self.assertEqual(details[0]["n_hyp"], 1)
        self.assertEqual(details[0]["mae_mid"], 2)
        self.assertEqual(details[1]["n_hyp"], 0)
        self.assertIsNone(details[1]["mae_mid"])
        self.assertEqual(summary["overall"]["MAE_Cvg"], 0.5)

    def test_no_duration_clipping(self):
        o, _ = evaluate([row("1s~101s")])
        self.assertAlmostEqual(o["overall"]["mIoU"], 0.02)

    def test_query_weighting_and_count_partition(self):
        s, _ = evaluate([row("1s~3s"), row("", "1s~3s;5s~7s", multi_target=True)])
        self.assertEqual(s["overall"]["mIoU"], 0.5)
        self.assertEqual(s["by_multi_target"]["multi"]["count_under"], 1)
        self.assertEqual(sum(s["overall"][key] for key in ["count_acc", "count_under", "count_over"]), 1)

    def test_invalid_ground_truth_and_metadata(self):
        for sample in [row("1s~3s", "0s~0s"), row("1s~3s", multi_target="false"), row("-1s~3s"), row("1s~3s", multi_target=True)]:
            with self.assertRaises(ValueError):
                evaluate([sample])

    def test_empty_and_duplicate_files_are_rejected(self):
        for rows in [[], [row("1s~3s", id="a"), row("1s~3s", id="a")]]:
            with self.assertRaises(ValueError):
                evaluate(rows)


if __name__ == "__main__":
    unittest.main()

