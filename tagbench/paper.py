"""Names and display metadata for the fixed 21-system arXiv v2 comparison.

This module contains no model predictions or experiment scores.
"""

PAPER_URL = "https://arxiv.org/abs/2609.01542v2"
PAPER_TITLE = "TAG-Bench: Benchmarking Temporal Audio Grounding in Large Audio Language Models"
AUTHORS = ["Yuhang Dai", "Xin Shu", "Zengxi Li", "Lei Xie", "Xiangang Li", "Jianwei Yu"]

MODELS = {
    "audio-flamingo-2": ("Audio Flamingo 2", "General-purpose"),
    "audio-flamingo-2-SoundCoT": ("AF2 Sound-CoT", "General-purpose"),
    "audio-flamingo-3": ("Audio Flamingo 3", "General-purpose"),
    "fireredaudio": ("FireRedAudio", "General-purpose"),
    "glm-4-voice-9b": ("GLM-4-Voice-9B", "General-purpose"),
    "kimi-audio-7b": ("Kimi-Audio-7B", "General-purpose"),
    "midashenglm-7b": ("MiDashengLM-7B", "General-purpose"),
    "mimo-audio-7b-instruct": ("MiMo-Audio-7B-Instruct", "General-purpose"),
    "moss-audio-4b-instruct": ("MOSS-Audio-4B-Instruct", "General-purpose"),
    "moss-audio-4b-thinking": ("MOSS-Audio-4B-Thinking", "General-purpose"),
    "moss-audio-8b-instruct": ("MOSS-Audio-8B-Instruct", "General-purpose"),
    "moss-audio-8b-thinking": ("MOSS-Audio-8B-Thinking", "General-purpose"),
    "step-audio-2-mini": ("Step-Audio-2-mini", "General-purpose"),
    "step-audio-2-mini-base": ("Step-Audio-2-mini-Base", "General-purpose"),
    "step-audio-2-mini-think": ("Step-Audio-2-mini-Think", "General-purpose"),
    "step-audio-r1": ("Step-Audio-R1", "General-purpose"),
    "timeaudio": ("TimeAudio", "Temporal expert"),
    "lat-audio": ("LAT-Audio", "Temporal expert"),
    "llama-3.1-8b-omni": ("LLaMA-3.1-8B-Omni", "Omni-modal"),
    "llama-omni2-14b": ("LLaMA-Omni2-14B", "General-purpose"),
    "gemini-3.1-pro": ("Gemini-3.1-Pro", "Omni-modal"),
}

SUBSETS = [
    ("word", "Word", 279, "A specific spoken word", "MOST"),
    ("acoustic event", "Acoustic event", 301, "A recognizable sound event", "A door opens and closes"),
    ("acoustic description", "Acoustic description", 260, "A sound described in natural language", "A sequence of metallic clinks"),
    ("semantic", "Semantic", 180, "The meaning of spoken content", "An opinion about ocean health"),
    ("rough semantic", "Rough semantic", 161, "An abstract or underspecified meaning", "A discussion of an important decision"),
    ("emotion", "Emotion", 129, "An emotion expressed in speech", "Disbelief and sympathy"),
    ("long - semantic", "Long · semantic", 180, "Semantic grounding in long recordings", "Find a statement in a long conversation"),
    ("long - acoustic description", "Long · description", 260, "Acoustic grounding in long recordings", "Find a recurring sound in long audio"),
]
