"""Claude LLM integration."""

import time

from anthropic import AsyncAnthropic

from .config import ANTHROPIC_API_KEY, log, log_latency
from .system_prompts import CLAUDE_SYSTEM_PROMPT


async def chat(user_message: str) -> str:
    """Get full response from Claude (non-streaming, for batch /api/chat)."""
    t0 = time.perf_counter()
    log(f"Claude input: {user_message[:80]}...", "CLAUDE")

    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    msg = await client.messages.create(
        model="claude-haiku-4-5",
        system=CLAUDE_SYSTEM_PROMPT,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_message}],
    )

    text = msg.content[0].text if msg.content else ""
    log_latency("Claude", (time.perf_counter() - t0) * 1000)
    log(f"Claude output: {text[:80]}...", "CLAUDE")
    return text
