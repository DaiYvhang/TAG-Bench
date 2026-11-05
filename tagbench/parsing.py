"""Model profiles and an explicit failure state around the historical parser."""

from decimal import Decimal

from . import legacy_parser
from .metrics import parse_intervals

THINK_MODELS = {
    "moss-audio-4b-thinking", "moss-audio-8b-thinking", "step-audio-2-mini-base",
    "step-audio-2-mini-think", "step-audio-r1", "lat-audio",
}
NUMBER_WORD_MODELS = {"llama-3.1-8b-omni", "llama-omni2-14b"}


def format_intervals(intervals, round_to_centiseconds=True):
    if round_to_centiseconds:
        return ";".join(f"{a:.2f}s~{b:.2f}s" for a, b in intervals)
    # Fixed notation preserves supplied precision and avoids the literal
    # historical sentinel for a structured [0, 0] point (0.0s~0.0s).
    return ";".join(f"{Decimal(str(a)):f}s~{Decimal(str(b)):f}s" for a, b in intervals)


def normalize_prediction(value, model="generic", parser="legacy"):
    """Return (canonical text, status), with status `ok` or `failed`.

    Legacy mode uses the original model-specific cascade, including its
    full-text fallback after an unparseable conclusion. Strict mode accepts
    only canonical strings or interval arrays. Neither mode clips to audio
    duration. A missing field is a schema error; an explicit empty value fails.
    """
    if parser not in {"legacy", "strict"}:
        raise ValueError(f"Unknown parser: {parser}")
    if value is None or value == "" or value == []:
        return "", "failed"
    if isinstance(value, list):
        parsed = parse_intervals(value)
        canonical = format_intervals(parsed, round_to_centiseconds=parser == "legacy")
    elif not isinstance(value, str):
        raise ValueError("Prediction must be text, an interval array, or null")
    elif parser == "strict":
        if value.strip() == "0s~0s":
            return "", "failed"
        parse_intervals(value)
        canonical = value.strip()
    else:
        preprocess = ()
        if model in THINK_MODELS:
            preprocess = (legacy_parser.strip_think,)
        elif model.lower() == "audio-flamingo-2-soundcot":
            preprocess = (legacy_parser.take_conclusion,)
        canonical = legacy_parser.parse_hyp(
            value, preprocess=preprocess, number_words=model in NUMBER_WORD_MODELS
        )
    if not canonical:
        return "", "failed"
    return canonical, "ok"
