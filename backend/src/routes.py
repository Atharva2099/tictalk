"""API routes."""

import base64
import time
from datetime import datetime

import httpx
from fastapi import HTTPException, UploadFile, File, Form

from .claude import chat as claude_chat
from .config import CARTESIA_API_KEY, ANTHROPIC_API_KEY, CARTESIA_VERSION, log, log_latency
from .stt import transcribe as stt_transcribe
from .text_utils import strip_markdown_for_tts
from .tts import synthesize as tts_synthesize


def register_routes(app):
    """Register routes on the FastAPI app."""

    @app.get("/api/health")
    async def health():
        return {"ok": True, "timestamp": datetime.now().isoformat()}

    @app.post("/api/access-token")
    async def access_token():
        """Return a short-lived Cartesia access token for the Calls API."""
        if not CARTESIA_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Missing CARTESIA_API_KEY",
            )
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.cartesia.ai/access-token",
                headers={
                    "Authorization": f"Bearer {CARTESIA_API_KEY}",
                    "Cartesia-Version": CARTESIA_VERSION,
                    "Content-Type": "application/json",
                },
                json={
                    "grants": {"agent": True},
                    "expires_in": 300,
                },
                timeout=10.0,
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Token request failed: {resp.text}",
            )
        data = resp.json()
        return {"token": data.get("token", "")}

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

        t_request = time.perf_counter()
        user_message = ""
        if audio:
            log("Received audio upload", "API")
            content_type = audio.content_type or "audio/webm"
            audio_bytes = await audio.read()
            user_message = await stt_transcribe(audio_bytes, content_type)
            if not user_message:
                raise HTTPException(status_code=400, detail="Could not transcribe audio")
        elif text and text.strip():
            user_message = text.strip()
            log(f"Received text: {user_message[:80]}...", "API")
        else:
            raise HTTPException(status_code=400, detail="Provide text or audio")

        response_text = await claude_chat(user_message)
        audio_bytes = await tts_synthesize(strip_markdown_for_tts(response_text))

        log_latency("POST /api/chat total", (time.perf_counter() - t_request) * 1000)
        return {
            "transcript": user_message if audio else None,
            "text": response_text,
            "audio": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
        }
