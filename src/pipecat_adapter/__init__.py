"""
pipecat_adapter sub-package: Pipecat TTSService backed by the megakernel server.
"""

from .tts import QwenMegakernelTTSService

__all__ = ["QwenMegakernelTTSService"]
