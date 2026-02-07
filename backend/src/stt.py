"""Speech-to-text via Cartesia Ink STT."""

import io
import time

import httpx

from .config import CARTESIA_API_KEY, CARTESIA_VERSION, log, log_latency


async def transcribe(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """Transcribe audio using Cartesia Ink STT Batch API (ink-whisper model)."""
    t0 = time.perf_counter()
    try:
        log(f"STT: sending {len(audio_bytes)} bytes ({content_type})", "STT")

        ext = "webm"
        if "wav" in content_type.lower():
            ext = "wav"
        elif "mp3" in content_type.lower():
            ext = "mp3"
        elif "ogg" in content_type.lower():
            ext = "ogg"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.cartesia.ai/stt",
                files={"file": (f"audio.{ext}", io.BytesIO(audio_bytes), content_type)},
                data={"model": "ink-whisper", "language": "en"},
                headers={
                    "Authorization": f"Bearer {CARTESIA_API_KEY}",
                    "Cartesia-Version": CARTESIA_VERSION,
                },
                timeout=30.0,
            )
            resp.raise_for_status()

        data = resp.json()
        text = data.get("text", "").strip()
        log_latency("STT batch", (time.perf_counter() - t0) * 1000)
        log(f"STT final: {text!r}", "STT")
        return text

    except Exception as e:
        log(f"STT error: {e}", "STT")
        raise
