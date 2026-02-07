"""Text-to-speech via Cartesia Sonic TTS."""

import asyncio
import json
import time

import httpx
import websockets

from .config import CARTESIA_API_KEY, CARTESIA_VERSION, DEFAULT_VOICE_ID, TTS_MODEL_ID, log, log_latency


def _format_tts_error(err: dict | str) -> str:
    """Extract user-friendly message from Cartesia error payload."""
    if isinstance(err, str):
        return err
    msg = err.get("message") if isinstance(err, dict) else None
    err_type = err.get("type") if isinstance(err, dict) else None
    if err_type == "overloaded_error":
        return "Voice service is busy. Please try again in a moment."
    if msg and "unexpected error" in msg.lower():
        return "Voice service had a temporary issue. Please try again."
    if msg:
        return msg
    return str(err) if err else "TTS error"


def _is_retryable_tts_error(err_msg: str) -> bool:
    """True if the error suggests retrying might help."""
    lower = err_msg.lower()
    return (
        "busy" in lower
        or "overloaded" in lower
        or "unexpected error" in lower
        or "temporary" in lower
    )


async def synthesize(text: str) -> bytes:
    """Synthesize speech using Cartesia Sonic TTS REST API."""
    if not text.strip():
        return b""

    t0 = time.perf_counter()
    log(f"TTS: generating for {len(text)} chars", "TTS")

    payload = {
        "model_id": TTS_MODEL_ID,
        "transcript": text,
        "voice": {"mode": "id", "id": DEFAULT_VOICE_ID},
        "language": "en",
        "output_format": {
            "container": "wav",
            "encoding": "pcm_s16le",
            "sample_rate": 44100,
        },
        "generation_config": {"emotion": "content", "speed": 1.0, "volume": 1.0},
    }

    for attempt in range(2):
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
            if resp.status_code in (429, 500, 503) and attempt == 0:
                log("TTS error (retryable), retrying in 2s...", "TTS")
                await asyncio.sleep(2)
                continue
            resp.raise_for_status()

        audio_bytes = resp.content
        log_latency("TTS batch", (time.perf_counter() - t0) * 1000)
        log(f"TTS: received {len(audio_bytes)} bytes", "TTS")
        return audio_bytes


async def _stream_synthesize_once(text: str):
    """Single attempt at streaming TTS. Yields base64-encoded PCM chunks."""
    url = (
        f"wss://api.cartesia.ai/tts/websocket"
        f"?cartesia_version={CARTESIA_VERSION}"
        f"&api_key={CARTESIA_API_KEY}"
    )
    payload = {
        "model_id": TTS_MODEL_ID,
        "transcript": text,
        "voice": {"mode": "id", "id": DEFAULT_VOICE_ID},
        "language": "en",
        "context_id": "tts-stream-1",
        "output_format": {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": 44100,
        },
        "generation_config": {"emotion": "content", "speed": 1.0, "volume": 1.0},
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
                    yield chunk_b64
            elif data.get("type") == "done":
                return
            elif data.get("type") == "error":
                err = data.get("error", "TTS error")
                raise RuntimeError(_format_tts_error(err)) from None


async def stream_synthesize(text: str):
    """Stream TTS audio chunks from Cartesia TTS WebSocket. Yields base64-encoded PCM chunks.
    Retries once on overloaded_error."""
    if not text.strip():
        return

    t0 = time.perf_counter()
    first_chunk_at: float | None = None
    chunk_count = 0
    log(f"TTS stream: generating for {len(text)} chars", "TTS")

    for attempt in range(2):
        try:
            async for chunk_b64 in _stream_synthesize_once(text):
                if first_chunk_at is None:
                    first_chunk_at = time.perf_counter()
                    log_latency("TTS stream first chunk", (first_chunk_at - t0) * 1000)
                chunk_count += 1
                yield chunk_b64
            log_latency("TTS stream total", (time.perf_counter() - t0) * 1000)
            log(f"TTS stream: {chunk_count} chunks", "TTS")
            return
        except RuntimeError as e:
            err_msg = str(e)
            if _is_retryable_tts_error(err_msg) and attempt == 0:
                log("TTS overloaded, retrying in 2s...", "TTS")
                await asyncio.sleep(2)
                continue
            raise
