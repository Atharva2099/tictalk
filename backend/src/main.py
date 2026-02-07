"""FastAPI backend for Cartesia + Claude voice chat."""

import asyncio
import base64
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import httpx
from anthropic import Anthropic
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

app = FastAPI(title="TicTalk Voice API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CARTESIA_VERSION = "2025-04-16"

# Default voice ID (Katie - good for voice agents)
DEFAULT_VOICE_ID = "f786b574-daa5-4673-aa0c-cbe3e8534c02"


def _log(msg: str, prefix: str = "API") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{prefix}] {msg}")


async def stt_transcribe(audio_bytes: bytes, content_type: str = "audio/webm") -> str:
    """Transcribe audio using Cartesia Ink STT Batch API (ink-whisper model)."""
    try:
        _log(f"STT: sending {len(audio_bytes)} bytes ({content_type})", "STT")

        # Infer file extension for batch API
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
        _log(f"STT final: {text!r}", "STT")
        return text

    except Exception as e:
        _log(f"STT error: {e}", "STT")
        raise


async def tts_synthesize(text: str) -> bytes:
    """Synthesize speech using Cartesia Sonic TTS REST API."""
    if not text.strip():
        return b""

    _log(f"TTS: generating for {len(text)} chars", "TTS")

    payload = {
        "model_id": "sonic-3",
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
    _log(f"TTS: received {len(audio_bytes)} bytes", "TTS")
    return audio_bytes


async def claude_chat(user_message: str) -> str:
    """Get response from Claude."""
    _log(f"Claude input: {user_message[:80]}...", "CLAUDE")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": user_message}],
    )

    text = msg.content[0].text if msg.content else ""
    _log(f"Claude output: {text[:80]}...", "CLAUDE")
    return text


@app.get("/api/health")
async def health():
    return {"ok": True, "timestamp": datetime.now().isoformat()}


@app.post("/api/chat")
async def chat(
    text: str | None = Form(None),
    audio: UploadFile | None = File(None),
):
    """Accept text or audio, return assistant text and audio."""
    if not CARTESIA_API_KEY or not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Missing CARTESIA_API_KEY or ANTHROPIC_API_KEY",
        )

    user_message = ""
    if audio:
        _log("Received audio upload", "API")
        content_type = audio.content_type or "audio/webm"
        audio_bytes = await audio.read()
        user_message = await stt_transcribe(audio_bytes, content_type)
        if not user_message:
            raise HTTPException(status_code=400, detail="Could not transcribe audio")
    elif text and text.strip():
        user_message = text.strip()
        _log(f"Received text: {user_message[:80]}...", "API")
    else:
        raise HTTPException(status_code=400, detail="Provide text or audio")

    response_text = await claude_chat(user_message)
    audio_bytes = await tts_synthesize(response_text)

    return {
        "transcript": user_message if audio else None,
        "text": response_text,
        "audio": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
    }
