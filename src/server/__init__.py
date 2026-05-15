"""
server sub-package: FastAPI streaming TTS inference server.
"""

from .app import create_app

__all__ = ["create_app"]
