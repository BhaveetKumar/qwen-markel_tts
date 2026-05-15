"""
Deepgram STT service with SSL certificate handling for macOS.

Wraps pipecat's DeepgramSTTService to handle SSL certificate verification issues.
"""

from __future__ import annotations

import ssl
from typing import Optional

try:
    from pipecat.services.deepgram import DeepgramSTTService
except ImportError:
    from pipecat.services.deepgram.stt import DeepgramSTTService


class DeepgramSTTServiceWithSSL(DeepgramSTTService):
    """
    Deepgram STT with custom SSL context for certificate verification.
    
    Handles SSL certificate issues common on macOS by creating a proper SSL context
    with certificate verification enabled but allowing for system certificates.
    """

    def __init__(self, api_key: str, **kwargs):
        """
        Initialize Deepgram STT service with SSL context.
        
        Args:
            api_key: Deepgram API key
            **kwargs: Additional arguments passed to DeepgramSTTService
        """
        # Create SSL context with proper certificate verification
        ssl_context = self._create_ssl_context()
        
        # Store SSL context for use in connection
        self._ssl_context = ssl_context
        
        super().__init__(api_key=api_key, **kwargs)

    @staticmethod
    def _create_ssl_context() -> ssl.SSLContext:
        """
        Create SSL context with proper certificate handling.
        
        Returns:
            Configured SSL context
        """
        # Use the system's default certificate bundle
        context = ssl.create_default_context()
        
        # Load certificates from certifi
        try:
            import certifi
            context.load_verify_locations(certifi.where())
        except Exception as e:
            print(f"Warning: Could not load certifi certificates: {e}")
            # Fall back to system certificates
            try:
                context.load_default_certs()
            except Exception as e2:
                print(f"Warning: Could not load system certificates: {e2}")
        
        return context
