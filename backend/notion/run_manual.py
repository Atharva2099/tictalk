"""Manual test script for Notion API. Run: uv run python -m notion.run_manual
Requires NOTION_PARENT_ID in .env (page ID or URL to create under)."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from notion.client import get_notion_client
from notion.tools import notion_create_page

ROMAN_HISTORY_CONTENT = """
The Roman Republic was established in 509 BCE after the overthrow of the last king, Lucius Tarquinius Superbus. The legendary brothers Brutus and Collatinus became the first consuls. Rome expanded through the Italian peninsula, fought three Punic Wars against Carthage, and by 27 BCE the Republic gave way to the Roman Empire under Augustus.

The Colosseum, completed in 80 CE under Emperor Titus, could hold an estimated 50,000 spectators. Gladiatorial games were a popular form of entertainment. The famous phrase "bread and circuses" (panem et circenses) comes from the poet Juvenal, describing how the masses were pacified by free grain and public spectacles.
""".strip()


async def main():
    parent_id = os.getenv("NOTION_PARENT_ID")
    if not parent_id:
        print("Set NOTION_PARENT_ID in .env (page ID or URL to create under)")
        print("Get the ID from a Notion page URL: notion.so/PageName-abc123def456...")
        return

    client = get_notion_client()
    print("Creating page with Roman history content...")
    created = await notion_create_page(
        client,
        parent_id,
        "Roman History Notes",
        content=ROMAN_HISTORY_CONTENT,
    )
    url = created.get("url", "")
    print(f"Created: {url}")


if __name__ == "__main__":
    asyncio.run(main())
