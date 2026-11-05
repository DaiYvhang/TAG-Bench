"""TAG-Bench evaluation. Scores use fractions; midpoint error uses seconds."""

from .metrics import evaluate, generalized_iou, interval_iou, midpoint_mae

__version__ = "0.1.0"
__all__ = ["evaluate", "generalized_iou", "interval_iou", "midpoint_mae"]

