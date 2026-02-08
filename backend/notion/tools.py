"""Notion API tools (search, fetch, create, update, move, etc.)."""

import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from notion_client import AsyncClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _extract_id(url_or_id: str) -> str:
    """Extract page/database ID from URL or plain ID. Handles full URLs and IDs with/without dashes."""
    s = url_or_id.strip()
    # UUID with dashes
    match = re.search(
        r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
        s,
        re.I,
    )
    if match:
        return match.group(1)
    # 32 hex chars without dashes (e.g. from notion.so/Page-abc123...)
    match = re.search(r"([a-f0-9]{32})", s, re.I)
    if match:
        u = match.group(1)
        return f"{u[:8]}-{u[8:12]}-{u[12:16]}-{u[16:20]}-{u[20:32]}"
    return s


async def notion_search(
    client: AsyncClient,
    query: str = "",
    filter_type: str | None = None,
    page_size: int = 20,
) -> dict[str, Any]:
    """Search pages and databases in the workspace."""
    body: dict[str, Any] = {"page_size": page_size}
    if query:
        body["query"] = query
    if filter_type:
        body["filter"] = {"property": "object", "value": filter_type}
    return await client.search(**body)


async def notion_fetch(client: AsyncClient, page_id: str) -> dict[str, Any]:
    """Fetch page metadata and its block children."""
    pid = _extract_id(page_id)
    page = await client.pages.retrieve(page_id=pid)
    blocks = await client.blocks.children.list(block_id=pid)
    return {"page": page, "blocks": blocks}


async def notion_create_page(
    client: AsyncClient,
    parent_id: str,
    title: str,
    content: str | None = None,
) -> dict[str, Any]:
    """Create a page under a parent."""
    pid = _extract_id(parent_id)
    parent: dict[str, str] = {"page_id": pid}
    children: list[dict[str, Any]] = []
    if content:
        children.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                },
            }
        )
    body: dict[str, Any] = {
        "parent": parent,
        "properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}},
    }
    if children:
        body["children"] = children
    return await client.pages.create(**body)


async def notion_update_page(
    client: AsyncClient,
    page_id: str,
    title: str | None = None,
    archived: bool | None = None,
) -> dict[str, Any]:
    """Update page properties."""
    pid = _extract_id(page_id)
    props: dict[str, Any] = {}
    if title is not None:
        props["title"] = {"title": [{"type": "text", "text": {"content": title}}]}
    if archived is not None:
        props["archived"] = archived
    if not props:
        return await client.pages.retrieve(page_id=pid)
    return await client.pages.update(page_id=pid, properties=props)


async def notion_move_page(
    client: AsyncClient,
    page_id: str,
    new_parent_id: str,
) -> dict[str, Any]:
    """Move a page to a new parent."""
    pid = _extract_id(page_id)
    parent_id = _extract_id(new_parent_id)
    return await client.pages.move(page_id=pid, parent={"page_id": parent_id})


async def notion_append_blocks(
    client: AsyncClient,
    page_id: str,
    text: str,
) -> dict[str, Any]:
    """Append a paragraph block to a page."""
    pid = _extract_id(page_id)
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
        }
    ]
    return await client.blocks.children.append(block_id=pid, children=children)


async def notion_query_database(
    client: AsyncClient,
    database_id: str,
    page_size: int = 100,
) -> dict[str, Any]:
    """Query a database."""
    did = _extract_id(database_id)
    return await client.data_sources.query(data_source_id=did, page_size=page_size)


async def notion_create_database(
    client: AsyncClient,
    parent_id: str,
    title: str,
    is_calendar: bool = False,
) -> dict[str, Any]:
    """Create a database under a parent page. If is_calendar=True, adds Date and Status for calendar view."""
    pid = _extract_id(parent_id)
    parent = {"type": "page_id", "page_id": pid}
    title_block = [{"type": "text", "text": {"content": title}}]

    # Calendar-style: Name (title), Date, Status
    if is_calendar:
        initial_data_source = {
            "properties": {
                "Name": {"title": {}},
                "Date": {"date": {}},
                "Status": {
                    "select": {
                        "options": [
                            {"name": "Idea"},
                            {"name": "Draft"},
                            {"name": "Scheduled"},
                            {"name": "Published"},
                        ]
                    }
                },
            }
        }
    else:
        initial_data_source = {"properties": {"Name": {"title": {}}}}

    return await client.databases.create(
        parent=parent,
        title=title_block,
        initial_data_source=initial_data_source,
    )


# Simple Monthly Planner template: https://elemental-accordion-08e.notion.site/The-2026-Simple-Monthly-Planner-2f0edf44cfc580dfbe7ac823fbee8be6
# Must be duplicated to your workspace and shared with the integration for API access.
DEFAULT_CALENDAR_TEMPLATE_ID = "2f0edf44-cfc5-80df-be7a-c823fbee8be6"


async def notion_create_from_template(
    client: AsyncClient,
    parent_id: str,
    title: str,
    template_id: str | None = None,
) -> dict[str, Any]:
    """Create a page from a template (e.g. 30-day monthly planner). Template must be in your workspace and shared with the integration."""
    pid = _extract_id(parent_id)
    tid = (
        _extract_id(template_id)
        if template_id
        else (_extract_id(os.getenv("NOTION_CALENDAR_TEMPLATE_ID", "")) or DEFAULT_CALENDAR_TEMPLATE_ID)
    )
    parent = {"type": "page_id", "page_id": pid}
    return await client.pages.create(
        parent=parent,
        properties={"title": {"title": [{"type": "text", "text": {"content": title}}]}},
        template={"type": "template_id", "template_id": tid},
    )
