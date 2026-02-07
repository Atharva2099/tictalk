"""Speech-to-text via Cartesia Ink STT."""

import audioop
import io
import json
import time

import httpx
import websockets

from .config import CARTESIA_API_KEY, CARTESIA_VERSION, log, log_latency


def _resample_pcm(pcm_bytes: bytes, from_rate: int, to_rate: int = 16000) -> bytes:
    if from_rate == to_rate:
        return pcm_bytes
    return audioop.ratecv(pcm_bytes, 2, 1, from_rate, to_rate)[0]


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


async def stream_transcribe(pcm_chunks: list[bytes], sample_rate: int = 16000) -> str:
    """Transcribe PCM audio using Cartesia Ink STT WebSocket."""
    if not pcm_chunks:
        return ""

    t0 = time.perf_counter()
    pcm_bytes = b"".join(pcm_chunks)
    if sample_rate != 16000:
        pcm_bytes = _resample_pcm(pcm_bytes, sample_rate, 16000)

    log(f"STT stream: sending {len(pcm_bytes)} bytes PCM 16kHz", "STT")

    url = (
        f"wss://api.cartesia.ai/stt/websocket"
        f"?model=ink-whisper"
        f"&language=en"
        f"&encoding=pcm_s16le"
        f"&sample_rate=16000"
        f"&min_volume=0.01"
        f"&max_silence_duration_secs=1.0"
        f"&cartesia_version={CARTESIA_VERSION}"
        f"&api_key={CARTESIA_API_KEY}"
    )

    final_text = ""
    chunk_size = 3200

    async with websockets.connect(url) as ws:
        for i in range(0, len(pcm_bytes), chunk_size):
            chunk = pcm_bytes[i : i + chunk_size]
            await ws.send(chunk)
        await ws.send("finalize")

        async for msg in ws:
            if isinstance(msg, str):
                data = json.loads(msg)
            else:
                continue

            if data.get("type") == "transcript":
                text = data.get("text", "")
                if text:
                    final_text = text
                    if data.get("is_final"):
                        log(f"STT final: {text!r}", "STT")
                        break
            elif data.get("type") in ("flush_done", "done"):
                break
            elif "error" in data:
                raise RuntimeError(data.get("error", "STT error"))

    log_latency("STT stream", (time.perf_counter() - t0) * 1000)
    return final_text.strip() or ""
