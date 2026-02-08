# TicTalk Backend

FastAPI backend: token endpoint for Cartesia Line, POST /api/chat for text fallback.

## Notion Integration

Set `NOTION_API_KEY` and `NOTION_PARENT_ID` in `.env`. `NOTION_PARENT_ID` is the tictalk root page (links to schedule, content, memories, agent). Share all relevant pages with the integration.

- **Phase 1 (manual):** `uv run python -m notion.run_manual` to test search
- **Phase 2:** Background agent fetches memories, writes scripts, updates context
- **Phase 3:** Voice agent receives Notion context via `session_id`

Calendar creation: `uv run python -m notion.run_calendar` (with backend running) calls `POST /api/calendar`, which uses Claude to build the calendar. Claude searches for schedule, chooses template vs database, and creates it. Optional `CALENDAR_PROMPT` env var to override the default prompt.

Create in Notion: `content/`, `schedule/`, `memories/`, `agent/` as documented in the plan.

See project root [README](../README.md) for full setup.
