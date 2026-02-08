"""API routes."""

import asyncio
import base64
import time
import uuid
from datetime import datetime

import httpx
from fastapi import Body, HTTPException, UploadFile, File, Form

from .claude import chat as claude_chat
from .config import CARTESIA_API_KEY, ANTHROPIC_API_KEY, CARTESIA_VERSION, log, log_latency
from .stt import transcribe as stt_transcribe
from .text_utils import strip_markdown_for_tts
from .tts import synthesize as tts_synthesize

from notion.context_store import (
    get_context,
    set_context,
    get_conversation,
    append_conversation,
)
from notion.agent import process as background_agent_process, run_with_prompt as agent_run_with_prompt


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
        session_id: str | None = Form(None),
    ):
        """Accept text or audio, return assistant text and audio."""
        if not CARTESIA_API_KEY or not ANTHROPIC_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Missing CARTESIA_API_KEY or ANTHROPIC_API_KEY",
            )

        sid = session_id or str(uuid.uuid4())
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

        append_conversation(sid, "user", user_message)
        context = get_context(sid)
        response_text = await claude_chat(user_message, extra_context=context)
        append_conversation(sid, "assistant", response_text)

        asyncio.create_task(_background_task(sid))

        audio_bytes = await tts_synthesize(strip_markdown_for_tts(response_text))

        log_latency("POST /api/chat total", (time.perf_counter() - t_request) * 1000)
        return {
            "transcript": user_message if audio else None,
            "text": response_text,
            "audio": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
        }

    @app.post("/api/calendar")
    async def create_calendar(body: dict | None = Body(None)):
        """Create a calendar under schedule via Claude. Uses Claude to search, choose template vs database, and create."""
        if not ANTHROPIC_API_KEY:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
        default_prompt = (
            "Create a calendar under schedule. Use notion_search to find the schedule page, "
            "then create a calendar (prefer notion_create_from_template for a 30-day monthly planner, "
            "fall back to notion_create_database with is_calendar=True if that fails). "
            "Return the URL of the created calendar."
        )
        prompt = (body or {}).get("prompt") if body else None
        result = await agent_run_with_prompt(prompt or default_prompt)
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Agent failed"))
        return result

    async def _background_task(session_id: str):
        """Fire-and-forget: run background agent and update context store."""
        try:
            conv = get_conversation(session_id)
            if conv:
                ctx = await background_agent_process(conv, session_id=session_id)
                if ctx:
                    set_context(session_id, ctx)
        except Exception as e:
            log(f"Background agent error: {e}", "NOTION")
