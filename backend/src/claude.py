"""Claude LLM integration."""

import time

from anthropic import AsyncAnthropic

from .config import ANTHROPIC_API_KEY, log, log_latency
from .text_utils import extract_sentences


async def chat(user_message: str) -> str:
    """Get full response from Claude (non-streaming, for batch /api/chat)."""
    t0 = time.perf_counter()
    log(f"Claude input: {user_message[:80]}...", "CLAUDE")

    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    msg = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": user_message}],
    )

    text = msg.content[0].text if msg.content else ""
    log_latency("Claude", (time.perf_counter() - t0) * 1000)
    log(f"Claude output: {text[:80]}...", "CLAUDE")
    return text


async def stream_sentences(user_message: str):
    """Stream Claude response, yielding complete sentences as they're assembled."""
    t0 = time.perf_counter()
    log(f"Claude stream input: {user_message[:80]}...", "CLAUDE")

    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    buf = ""

    async with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for event in stream:
            if event.type == "content_block_delta":
                delta = getattr(event, "delta", None)
                text = getattr(delta, "text", "") if delta else ""
                if text:
                    buf += text
                    sentences, buf = extract_sentences(buf)
                    for s in sentences:
                        yield s

    if buf.strip():
        yield buf.strip()
    log_latency("Claude stream", (time.perf_counter() - t0) * 1000)
