"""Background writer agent: Claude with Notion tools for content and memory."""

import json
import os
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

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

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

AGENT_SYSTEM_PROMPT = """
You are a background writer agent for a voice-based content assistant. Your job is to:

1. Use the Notion workspace as memory and context. The tictalk root page links to:
   - memories/ - User profile, writing style, dos/don'ts, channels, follower count
   - content/ - Content ideas, drafts, published scripts
   - schedule/ - Calendar and posting schedule
   - agent/ - Temporary memory and skills (internal use)

   Use notion_search to find these pages by name; do not assume NOTION_PARENT_ID is schedule.

2. Based on conversation history, fetch relevant context from memories/ to understand who the user is and how they write.

3. Write or update scripts in content/drafts/ or content/ when the conversation suggests new content ideas.

4. Summarize relevant context for the voice agent in a CONEXT_FOR_VOICE block at the end of your final response. Format:
   <CONTEXT_FOR_VOICE>
   Brief summary: user preferences, writing style hints, schedule notes, etc. for the next voice turn.
   </CONTEXT_FOR_VOICE>

5. Use notion_search to find pages, notion_fetch to read content, notion_create_page to create pages, notion_create_database and notion_create_from_template for calendars, notion_update_page and notion_append_blocks to update, notion_move_page to reorganize.

6. When asked to create a calendar under schedule, prefer notion_create_from_template to create a 30-day monthly planner (Simple Monthly Planner template). Find the schedule page via notion_search, then call notion_create_from_template with parent_id=schedule page ID, title e.g. "Monthly Planner". If template fails, fall back to notion_create_database with is_calendar=True. The template must be duplicated to the user's workspace and shared with the integration first.

7. When you learn something about the user from conversation that is NOT already in memories/user_info, append it to memories/nuances using notion_append_blocks. Use a dated bullet, e.g. "[2025-02-07] Prefers morning posts". Do not duplicate information from user_info.

Use tools as needed. Keep the context summary concise (2-4 sentences) for the voice agent.
""".strip()

NOTION_TOOLS = [
    {
        "name": "notion_search",
        "description": "Search the Notion workspace for pages and databases. Use to find memories, content, schedule, or agent folders. Returns matching pages with titles and IDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'memories', 'content ideas')"},
                "filter_type": {"type": "string", "description": "Optional: 'page' or 'database' to filter results"},
                "page_size": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
            "required": [],
        },
    },
    {
        "name": "notion_fetch",
        "description": "Fetch a page by ID or URL. Returns page metadata and block content. Use to read memories, writing style, content drafts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Page ID or full Notion URL"},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "notion_create_page",
        "description": "Create a new page under a parent page. Use for new content ideas, drafts, or moving content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_id": {"type": "string", "description": "Parent page ID or URL"},
                "title": {"type": "string", "description": "Page title"},
                "content": {"type": "string", "description": "Optional initial paragraph content"},
            },
            "required": ["parent_id", "title"],
        },
    },
    {
        "name": "notion_update_page",
        "description": "Update page properties (title, archived).",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Page ID or URL"},
                "title": {"type": "string", "description": "New title"},
                "archived": {"type": "boolean", "description": "Archive the page"},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "notion_move_page",
        "description": "Move a page to a new parent (e.g. from content/ideas to content/drafts).",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Page ID or URL to move"},
                "new_parent_id": {"type": "string", "description": "New parent page ID or URL"},
            },
            "required": ["page_id", "new_parent_id"],
        },
    },
    {
        "name": "notion_append_blocks",
        "description": "Append a paragraph block to a page. Use to add content to existing pages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Page ID or URL"},
                "text": {"type": "string", "description": "Text to append"},
            },
            "required": ["page_id", "text"],
        },
    },
    {
        "name": "notion_query_database",
        "description": "Query a Notion database. Use for schedule, content calendar, or any database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "Database ID or URL"},
                "page_size": {"type": "integer", "description": "Max results (default 100)", "default": 100},
            },
            "required": ["database_id"],
        },
    },
    {
        "name": "notion_create_database",
        "description": "Create a database under a parent page. Use for content calendars, schedules, or any structured data. Set is_calendar=True for a calendar-style database (Date, Status) that the user can view as calendar in Notion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_id": {"type": "string", "description": "Parent page ID or URL (e.g. schedule page)"},
                "title": {"type": "string", "description": "Database title (e.g. Content Calendar)"},
                "is_calendar": {"type": "boolean", "description": "If true, adds Date and Status for calendar view", "default": True},
            },
            "required": ["parent_id", "title"],
        },
    },
    {
        "name": "notion_create_from_template",
        "description": "Create a page from a template (e.g. 30-day Simple Monthly Planner). Use for actual monthly calendars with 30 days. Template must be in the workspace and shared with the integration. Prefer this over notion_create_database when user wants a real monthly planner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "parent_id": {"type": "string", "description": "Parent page ID or URL (e.g. schedule page)"},
                "title": {"type": "string", "description": "Page title (e.g. Monthly Planner)"},
                "template_id": {"type": "string", "description": "Optional: template page ID. Defaults to Simple Monthly Planner if not set."},
            },
            "required": ["parent_id", "title"],
        },
    },
]


async def _run_tool(name: str, input_data: dict[str, Any]) -> str:
    """Execute a Notion tool and return result as string."""
    client = get_notion_client()
    try:
        if name == "notion_search":
            result = await notion_search(
                client,
                query=input_data.get("query", ""),
                filter_type=input_data.get("filter_type"),
                page_size=input_data.get("page_size", 20),
            )
        elif name == "notion_fetch":
            result = await notion_fetch(client, input_data["page_id"])
        elif name == "notion_create_page":
            result = await notion_create_page(
                client,
                parent_id=input_data["parent_id"],
                title=input_data["title"],
                content=input_data.get("content"),
            )
        elif name == "notion_update_page":
            result = await notion_update_page(
                client,
                page_id=input_data["page_id"],
                title=input_data.get("title"),
                archived=input_data.get("archived"),
            )
        elif name == "notion_move_page":
            result = await notion_move_page(
                client,
                page_id=input_data["page_id"],
                new_parent_id=input_data["new_parent_id"],
            )
        elif name == "notion_append_blocks":
            result = await notion_append_blocks(
                client,
                page_id=input_data["page_id"],
                text=input_data["text"],
            )
        elif name == "notion_query_database":
            result = await notion_query_database(
                client,
                database_id=input_data["database_id"],
                page_size=input_data.get("page_size", 100),
            )
        elif name == "notion_create_database":
            result = await notion_create_database(
                client,
                parent_id=input_data["parent_id"],
                title=input_data["title"],
                is_calendar=input_data.get("is_calendar", True),
            )
        elif name == "notion_create_from_template":
            result = await notion_create_from_template(
                client,
                parent_id=input_data["parent_id"],
                title=input_data["title"],
                template_id=input_data.get("template_id"),
            )
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
        return json.dumps(result, default=str, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _extract_context_for_voice(text: str) -> str:
    """Extract content from <CONTEXT_FOR_VOICE>...</CONTEXT_FOR_VOICE> block."""
    start = text.find("<CONTEXT_FOR_VOICE>")
    end = text.find("</CONTEXT_FOR_VOICE>")
    if start != -1 and end != -1 and end > start:
        return text[start + len("<CONTEXT_FOR_VOICE>") : end].strip()
    return ""


async def process(
    conversation: list[dict[str, Any]],
    session_id: str | None = None,
) -> str:
    """
    Run the background writer agent on conversation history.
    Returns the context string for the voice agent (from CONTEXT_FOR_VOICE block).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    notion_key = os.getenv("NOTION_API_KEY")
    if not notion_key:
        return ""

    client = AsyncAnthropic(api_key=api_key)

    messages: list[dict[str, Any]] = []
    for m in conversation:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, str):
            messages.append({"role": role, "content": content})
        else:
            messages.append({"role": role, "content": content})

    if not messages:
        return ""

    messages.append({
        "role": "user",
        "content": "Based on the conversation above, fetch relevant context from memories/ and update content/ as needed. End with a <CONTEXT_FOR_VOICE> block summarizing what the voice agent should know for the next turn.",
    })

    tool_map = {t["name"]: t for t in NOTION_TOOLS}
    max_iterations = 10
    final_text = ""

    for _ in range(max_iterations):
        response = await client.messages.create(
            model="claude-haiku-4-5",
            system=AGENT_SYSTEM_PROMPT,
            max_tokens=1024,
            tools=NOTION_TOOLS,
            messages=messages,
        )

        tool_results: list[dict[str, Any]] = []
        for block in response.content:
            btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if btype == "text":
                final_text = getattr(block, "text", "") or (block.get("text", "") if isinstance(block, dict) else "")
            elif btype == "tool_use":
                tool_id = getattr(block, "id", "") or (block.get("id", "") if isinstance(block, dict) else "")
                tool_name = getattr(block, "name", "") or (block.get("name", "") if isinstance(block, dict) else "")
                tool_input = getattr(block, "input", {}) or (block.get("input", {}) if isinstance(block, dict) else {})
                result = await _run_tool(tool_name, tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                })

        if response.stop_reason == "end_turn" and not tool_results:
            break

        if tool_results:
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return _extract_context_for_voice(final_text)


async def run_with_prompt(prompt: str) -> dict[str, Any]:
    """
    Run the agent with a single prompt (no conversation, no appended message).
    Returns {"status": "ok", "message": "...", "url": "..."} or {"status": "error", "message": "..."}.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"status": "error", "message": "ANTHROPIC_API_KEY not set"}

    notion_key = os.getenv("NOTION_API_KEY")
    if not notion_key:
        return {"status": "error", "message": "NOTION_API_KEY not set"}

    client = AsyncAnthropic(api_key=api_key)
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    max_iterations = 10
    final_text = ""
    created_url: str | None = None

    for _ in range(max_iterations):
        response = await client.messages.create(
            model="claude-haiku-4-5",
            system=AGENT_SYSTEM_PROMPT,
            max_tokens=1024,
            tools=NOTION_TOOLS,
            messages=messages,
        )

        tool_results: list[dict[str, Any]] = []
        for block in response.content:
            btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if btype == "text":
                final_text = getattr(block, "text", "") or (block.get("text", "") if isinstance(block, dict) else "")
            elif btype == "tool_use":
                tool_id = getattr(block, "id", "") or (block.get("id", "") if isinstance(block, dict) else "")
                tool_name = getattr(block, "name", "") or (block.get("name", "") if isinstance(block, dict) else "")
                tool_input = getattr(block, "input", {}) or (block.get("input", {}) if isinstance(block, dict) else {})
                result = await _run_tool(tool_name, tool_input)
                # Extract URL from create responses
                if tool_name in ("notion_create_database", "notion_create_from_template"):
                    try:
                        data = json.loads(result) if isinstance(result, str) else result
                        url = data.get("url") or (data.get("id") and f"https://notion.so/{data['id'].replace('-', '')}")
                        if url:
                            created_url = url
                    except Exception:
                        pass
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                })

        if response.stop_reason == "end_turn" and not tool_results:
            break

        if tool_results:
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    out: dict[str, Any] = {"status": "ok", "message": final_text or "Done."}
    if created_url:
        out["url"] = created_url
    return out
