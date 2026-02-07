#!/usr/bin/env bash
# Run the backend from project root. Uses backend's uv environment (has all deps).
cd "$(dirname "$0")/backend" && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
