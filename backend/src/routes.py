"""API routes."""

import base64
import time
from datetime import datetime

from fastapi import HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect

from .claude import chat as claude_chat, stream_sentences as claude_stream_sentences
from .config import CARTESIA_API_KEY, ANTHROPIC_API_KEY, log, log_latency
from .stt import transcribe as stt_transcribe, stream_transcribe as stt_stream_transcribe
from .text_utils import strip_markdown_for_tts
from .tts import synthesize as tts_synthesize, stream_synthesize as tts_stream_synthesize


def register_routes(app):
    """Register routes on the FastAPI app."""

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

    @app.websocket("/api/ws/chat")
    async def ws_chat(websocket: WebSocket):
        """WebSocket for streaming voice/text chat."""
        await websocket.accept()

        if not CARTESIA_API_KEY or not ANTHROPIC_API_KEY:
            await websocket.send_json({"type": "error", "error": "Missing API keys"})
            await websocket.close()
            return

        pcm_chunks: list[bytes] = []
        sample_rate = 16000
        user_message = ""
        t_ws = time.perf_counter()

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "audio_chunk":
                    chunk_b64 = data.get("data", "")
                    if chunk_b64:
                        pcm_chunks.append(base64.b64decode(chunk_b64))
                elif msg_type == "audio_end":
                    sample_rate = data.get("sample_rate", 16000)
                    break
                elif msg_type == "text":
                    user_text = data.get("text", "").strip()
                    if user_text:
                        user_message = user_text
                        log(f"WS text: {user_message[:80]}...", "API")
                    break

            if not user_message:
                if not pcm_chunks:
                    await websocket.send_json({"type": "error", "error": "No audio or text received"})
                    await websocket.close()
                    return
                user_message = await stt_stream_transcribe(pcm_chunks, sample_rate=sample_rate)
                if not user_message:
                    await websocket.send_json({"type": "error", "error": "Could not transcribe audio"})
                    await websocket.close()
                    return
                await websocket.send_json({"type": "transcript", "text": user_message})

            full_text = ""
            async for sentence in claude_stream_sentences(user_message):
                full_text = (full_text + " " + sentence) if full_text else sentence
                await websocket.send_json({"type": "text", "text": full_text})
                if len(sentence.strip()) >= 2:
                    tts_text = strip_markdown_for_tts(sentence)
                    if tts_text.strip():
                        async for chunk_b64 in tts_stream_synthesize(tts_text):
                            await websocket.send_json({"type": "audio_chunk", "data": chunk_b64})

            await websocket.send_json({"type": "done"})
            log_latency("WebSocket /api/ws/chat total", (time.perf_counter() - t_ws) * 1000)

        except WebSocketDisconnect:
            pass
        except Exception as e:
            log(f"WS error: {e}", "API")
            try:
                await websocket.send_json({"type": "error", "error": str(e)})
            except Exception:
                pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass
