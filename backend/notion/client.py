"""Notion API client setup."""

import os
from pathlib import Path

from dotenv import load_dotenv
from notion_client import AsyncClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2025-09-03"


def get_notion_client() -> AsyncClient:
    """Return configured Notion async client."""
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEY not set in .env")
    return AsyncClient(auth=NOTION_API_KEY)
