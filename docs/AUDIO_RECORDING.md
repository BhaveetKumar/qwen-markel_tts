# Audio Response Recording

The Qwen3-TTS Pipecat voice pipeline now supports automatic audio recording of all TTS responses.

## Features

✅ **Automatic Recording** - Each LLM response is automatically recorded to a separate WAV file  
✅ **Timestamped Files** - Files are named with timestamp and sequence number for easy organization  
✅ **Metadata** - Console output shows file size and duration for each recording  
✅ **24 kHz Audio** - Records at the native Qwen3-TTS output sample rate  
✅ **Lossless Format** - 16-bit WAV for high-quality audio preservation  

## Usage

### With Audio Recording (to folder)

```bash
python3 -u scripts/demo.py \
  --tts-url "https://collectibles-wrapped-studied-hazards.trycloudflare.com" \
  --deepgram-key "$DEEPGRAM_API_KEY" \
  --openai-key "$OPENAI_API_KEY" \
  --audio-output-dir "./responses"
```

The `--audio-output-dir` parameter specifies where to save response audio files. The directory will be created automatically if it doesn't exist.

### Without Audio Recording (default)

```bash
python3 -u scripts/demo.py \
  --tts-url "https://collectibles-wrapped-studied-hazards.trycloudflare.com" \
  --deepgram-key "$DEEPGRAM_API_KEY" \
  --openai-key "$OPENAI_API_KEY"
```

Omit the `--audio-output-dir` parameter to run without saving audio.

## Output Files

Audio files are saved in the format: `response_NNNN_YYYYMMdd_HHMMSS_mmm.wav`

Example:
```
response_0001_20260515_143022_150.wav  (2.3KB, 0.05s)
response_0002_20260515_143045_275.wav  (4.7KB, 0.11s)
response_0003_20260515_143108_890.wav  (8.2KB, 0.19s)
```

Where:
- `NNNN` = sequential response number (auto-incremented)
- `YYYYMMdd` = date (year-month-day)
- `HHMMSS` = time (hour-minute-second)
- `mmm` = milliseconds

## Pipeline Integration

The audio recording is implemented as a Pipecat `FrameProcessor` that:

1. **Detects response start** - Triggers when the first `TextFrame` (LLM response) arrives
2. **Captures audio frames** - Records each `TTSAudioRawFrame` from the TTS service
3. **Detects response end** - Stops recording on `EndFrame`
4. **Saves to disk** - Writes buffered audio to a WAV file with proper format

The recorder is inserted in the pipeline between the TTS service and the audio output transport:

```
Input → STT → LLM → TTS → [AudioRecorder] → Output → Speaker
```

This ensures all TTS output is captured regardless of how audio is being played back.

## Implementation Details

### AudioRecorderProcessor class (`src/pipecat_adapter/audio_recorder.py`)

- **Extends**: `pipecat.processors.frame_processor.FrameProcessor`
- **Methods**:
  - `start_new_response()` - Begins recording for a new response
  - `write_frame(audio_bytes)` - Buffers audio data
  - `finish_response()` - Completes recording and saves to disk
  - `process_frame(frame, direction)` - Pipecat frame handler

- **Parameters**:
  - `output_dir` - Where to save WAV files
  - `sample_rate` - Audio sample rate (default: 24000 Hz)
  - `num_channels` - Audio channels (default: 1, mono)

## Examples

### Example 1: Basic recording

```bash
python3 -u scripts/demo.py \
  --tts-url "https://collectibles-wrapped-studied-hazards.trycloudflare.com" \
  --deepgram-key "..." \
  --openai-key "..." \
  --audio-output-dir "./audio_responses"
```

Output:
```
[5/5] Building pipeline...
  • Audio recording enabled: ./audio_responses
  ✓ Pipeline assembled

Speak into your microphone (Ctrl+C to stop)

  🔴 Recording response to: response_0001_20260515_143022_150.wav
  ✓ Saved: response_0001_20260515_143022_150.wav (2.3KB, 0.05s)
```

### Example 2: Using shell script

```bash
chmod +x scripts/run_with_recording.sh
./scripts/run_with_recording.sh
```

## Troubleshooting

**Issue**: Audio files not being created

- Check that the output directory path is writable
- Verify the pipeline initialized successfully (watch for "Audio recording enabled" message)
- Check console output for any error messages starting with "✗"

**Issue**: Audio files are empty or very small

- This is normal for short responses
- Verify the TTS server is responding (should hear audio output from speaker)
- Check that the LLM is generating responses (look for transcription messages)

**Issue**: Directory doesn't exist

- The processor creates the directory automatically with `mkdir -p`
- If creation fails, you'll see an error message

## File Organization

Recommended practice: Create a `responses` subdirectory:

```bash
mkdir -p responses
python3 -u scripts/demo.py ... --audio-output-dir "./responses"
```

Then you can easily organize by date:

```bash
mv responses/response_*_20260515_*.wav responses/2026-05-15/
mv responses/response_*_20260516_*.wav responses/2026-05-16/
```

## Listening to Recordings

### macOS

```bash
# Play a single file
afplay responses/response_0001_*.wav

# Play all files in order
for f in responses/response_*.wav; do afplay "$f"; done
```

### Linux

```bash
# Play a single file
aplay responses/response_0001_*.wav

# Play all files in order
for f in responses/response_*.wav; do aplay "$f"; done
```

### Python

```python
import wave
import pyaudio

filename = "responses/response_0001_20260515_143022_150.wav"
with wave.open(filename, 'rb') as wav_file:
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(wav_file.getsampwidth()),
                    channels=wav_file.getnchannels(),
                    rate=wav_file.getframerate(),
                    output=True)
    stream.write(wav_file.readframes(wav_file.getnframes()))
    stream.stop_stream()
    stream.close()
    p.terminate()
```

## Performance Impact

- **Minimal CPU overhead** - Audio buffering and WAV writing are fast
- **Storage**: ~4KB per second of audio at 24kHz 16-bit mono
  - 1 minute of audio ≈ 240KB
  - 1 hour of audio ≈ 14MB

## Future Enhancements

Possible improvements:
- Support for different audio formats (MP3, FLAC, etc.)
- Real-time audio streaming to network sockets
- Audio filtering/normalization before saving
- Automatic compression of old recordings
- Integration with cloud storage (S3, GCS, etc.)
