"""Notion API integration for TicTalk content workspace."""

from .agent import process as background_agent_process
from .client import get_notion_client
from .tools import (
    notion_search,
    notion_fetch,
    notion_create_page,
    notion_create_database,
    notion_create_from_template,
    notion_update_page,
    notion_move_page,
    notion_append_blocks,
    notion_query_database,
)

__all__ = [
    "get_notion_client",
    "notion_search",
    "notion_fetch",
    "notion_create_page",
    "notion_create_database",
    "notion_create_from_template",
    "notion_update_page",
    "notion_move_page",
    "notion_append_blocks",
    "notion_query_database",
    "background_agent_process",
]
