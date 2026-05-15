"""
Megakernel adapter layer.

Wraps AlpinDale's qwen_megakernel for use with Qwen3-TTS talker decoder.
Provides a ModelConfig for different Qwen3 architecture sizes and a
KernelDecoder that delegates to the CUDA op when available, or falls back
to a pure-PyTorch path for testing without a GPU.
"""

from .adapter import KernelDecoder, ModelConfig, QWEN3_0_6B_CONFIG, QWEN3_TTS_TALKER_CONFIG

__all__ = ["KernelDecoder", "ModelConfig", "QWEN3_0_6B_CONFIG", "QWEN3_TTS_TALKER_CONFIG"]
