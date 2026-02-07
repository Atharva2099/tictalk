"""Text-to-speech via Cartesia Sonic TTS."""

import json
import time

import httpx
import websockets

from .config import CARTESIA_API_KEY, CARTESIA_VERSION, DEFAULT_VOICE_ID, log, log_latency


async def synthesize(text: str) -> bytes:
    """Synthesize speech using Cartesia Sonic TTS REST API."""
    if not text.strip():
        return b""

    t0 = time.perf_counter()
    log(f"TTS: generating for {len(text)} chars", "TTS")

    payload = {
        "model_id": "sonic-turbo",
        "transcript": text,
        "voice": {"mode": "id", "id": DEFAULT_VOICE_ID},
        "language": "en",
        "output_format": {
            "container": "wav",
            "encoding": "pcm_s16le",
            "sample_rate": 44100,
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.cartesia.ai/tts/bytes",
            json=payload,
            headers={
                "Authorization": f"Bearer {CARTESIA_API_KEY}",
                "Cartesia-Version": CARTESIA_VERSION,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        resp.raise_for_status()

    audio_bytes = resp.content
    log_latency("TTS batch", (time.perf_counter() - t0) * 1000)
    log(f"TTS: received {len(audio_bytes)} bytes", "TTS")
    return audio_bytes


async def stream_synthesize(text: str):
    """Stream TTS audio chunks from Cartesia TTS WebSocket. Yields base64-encoded PCM chunks."""
    if not text.strip():
        return

    t0 = time.perf_counter()
    first_chunk_at: float | None = None
    chunk_count = 0
    log(f"TTS stream: generating for {len(text)} chars", "TTS")

    url = (
        f"wss://api.cartesia.ai/tts/websocket"
        f"?cartesia_version={CARTESIA_VERSION}"
        f"&api_key={CARTESIA_API_KEY}"
    )

    payload = {
        "model_id": "sonic-turbo",
        "transcript": text,
        "voice": {"mode": "id", "id": DEFAULT_VOICE_ID},
        "language": "en",
        "context_id": "tts-stream-1",
        "output_format": {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": 44100,
        },
        "add_timestamps": False,
        "continue": False,
    }

    async with websockets.connect(url) as ws:
        await ws.send(json.dumps(payload))

        async for msg in ws:
            if isinstance(msg, str):
                data = json.loads(msg)
            else:
                continue

            if data.get("type") == "chunk":
                chunk_b64 = data.get("data", "")
                if chunk_b64:
                    if first_chunk_at is None:
                        first_chunk_at = time.perf_counter()
                        log_latency("TTS stream first chunk", (first_chunk_at - t0) * 1000)
                    chunk_count += 1
                    yield chunk_b64
            elif data.get("type") == "done":
                log_latency("TTS stream total", (time.perf_counter() - t0) * 1000)
                log(f"TTS stream: {chunk_count} chunks", "TTS")
                break
            elif data.get("type") == "error":
                raise RuntimeError(data.get("error", "TTS error"))
