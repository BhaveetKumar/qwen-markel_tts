"""
qwen3_tts sub-package: model loading, talker decoder, audio synthesis.
"""

from .loader import TalkerWeights, load_talker_weights
from .decoder import TalkerDecoder
from .vocoder import tokens_to_pcm, AudioConfig

__all__ = [
    "TalkerWeights",
    "load_talker_weights",
    "TalkerDecoder",
    "tokens_to_pcm",
    "AudioConfig",
]
