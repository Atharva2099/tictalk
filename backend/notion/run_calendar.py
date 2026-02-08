"""Create a calendar under schedule via the API (Claude builds it).
Run: uv run python -m notion.run_calendar

Requires the backend server to be running (uv run uvicorn src.main:app).
Calls POST /api/calendar which uses Claude to search, choose template vs database, and create.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import httpx


async def main():
    base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    prompt = os.getenv("CALENDAR_PROMPT")  # Optional override

    print("Calling /api/calendar (Claude will build it)...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/api/calendar",
                json={"prompt": prompt} if prompt else {},
            )
        resp.raise_for_status()
        data = resp.json()
    except httpx.ConnectError:
        print("Could not connect. Is the backend running? Start with: uv run uvicorn src.main:app")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"API error: {e.response.status_code} - {e.response.text}")
        sys.exit(1)

    if data.get("url"):
        print(f"Created: {data['url']}")
    print(data.get("message", "Done."))


if __name__ == "__main__":
    asyncio.run(main())
