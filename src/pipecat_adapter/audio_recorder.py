"""
Audio recorder processor for Pipecat pipeline.

Records TTSAudioRawFrame frames to timestamped WAV files.
"""

from __future__ import annotations

import wave
from datetime import datetime
from pathlib import Path
from typing import Optional

from pipecat.frames.frames import EndFrame, StartFrame, TextFrame, TTSAudioRawFrame
from pipecat.processors.frame_processor import FrameProcessor


class AudioRecorderProcessor(FrameProcessor):
    """Records TTS audio frames to WAV files."""

    def __init__(
        self,
        output_dir: str,
        sample_rate: int = 24000,
        num_channels: int = 1,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.current_file: Optional[str] = None
        self.frames_buffer = bytearray()
        self.response_count = 0
        self.recording = False

    def start_new_response(self):
        """Start recording a new response."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self.response_count += 1
        filename = self.output_dir / f"response_{self.response_count:04d}_{timestamp}.wav"
        self.current_file = str(filename)
        self.frames_buffer = bytearray()
        self.recording = True
        print(f"  🔴 Recording response to: {filename.name}", flush=True)

    def write_frame(self, audio_bytes: bytes):
        """Buffer audio frame data."""
        if self.recording:
            self.frames_buffer.extend(audio_bytes)

    def finish_response(self):
        """Finish recording and save to WAV file."""
        if not self.current_file or len(self.frames_buffer) == 0:
            self.recording = False
            return

        try:
            with wave.open(self.current_file, "wb") as wav_file:
                wav_file.setnchannels(self.num_channels)
                wav_file.setsampwidth(2)  # 16-bit audio
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(bytes(self.frames_buffer))

            file_size_kb = len(self.frames_buffer) / 1024
            duration_sec = len(self.frames_buffer) / (
                self.sample_rate * self.num_channels * 2
            )
            print(
                f"  ✓ Saved: {Path(self.current_file).name} ({file_size_kb:.1f}KB, {duration_sec:.2f}s)",
                flush=True,
            )
        except Exception as e:
            print(f"  ✗ Error saving audio: {e}", flush=True)
        finally:
            self.current_file = None
            self.frames_buffer = bytearray()
            self.recording = False

    async def process_frame(self, frame, direction="input"):
        """Process frames and record audio."""
        # StartFrame must be passed through to properly initialize
        if isinstance(frame, StartFrame):
            await self.push_frame(frame, direction)
            return
        
        # Start recording on first TextFrame (LLM response)
        if isinstance(frame, TextFrame) and not self.recording:
            self.start_new_response()

        # Record audio frames
        elif isinstance(frame, TTSAudioRawFrame) and self.recording:
            self.write_frame(frame.audio)

        # Stop recording on end frame
        elif isinstance(frame, EndFrame) and self.recording:
            self.finish_response()

        # Always pass frame through to next processor
        await self.push_frame(frame, direction)
