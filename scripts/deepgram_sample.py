import os
import threading
import httpx

from deepgram import DeepgramClient
from deepgram.core.events import EventType

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
STREAM_URL = "https://collectibles-wrapped-studied-hazards.trycloudflare.com"

if not DEEPGRAM_API_KEY:
    raise RuntimeError("Set DEEPGRAM_API_KEY in your environment.")

client = DeepgramClient(api_key=DEEPGRAM_API_KEY)

with client.listen.v1.connect(
    model="nova-3",
    language="en",
) as connection:
    ready = threading.Event()

    def on_open(_):
        print("[open] connected to Deepgram")
        ready.set()

    def on_message(result):
        channel = getattr(result, "channel", None)
        if channel and hasattr(channel, "alternatives"):
            transcript = channel.alternatives[0].transcript
            is_final = getattr(result, "is_final", True)
            if transcript:
                prefix = "FINAL" if is_final else "INTERIM"
                print(f"[{prefix}] {transcript}")

    def on_error(err):
        print(f"[error] {err}")

    connection.on(EventType.OPEN, on_open)
    connection.on(EventType.MESSAGE, on_message)
    connection.on(EventType.ERROR, on_error)

    def stream():
        ready.wait()
        with httpx.stream("GET", STREAM_URL, follow_redirects=True, timeout=30.0) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes(chunk_size=4096):
                if chunk:
                    connection.send_media(chunk)

    threading.Thread(target=stream, daemon=True).start()
    print(f"Transcribing {STREAM_URL}...")
    connection.start_listening()