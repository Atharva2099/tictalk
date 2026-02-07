# TicTalk - Voice Chat with Cartesia + Claude

Simple voice chat pipeline: React + shadcn frontend, FastAPI backend. Uses Cartesia Ink for STT, Claude for responses, Cartesia Sonic for TTS.

## Setup

### Backend

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env with CARTESIA_API_KEY and ANTHROPIC_API_KEY
```

Requires **ffmpeg** for audio conversion (webm -> PCM). Install via:

- macOS: `brew install ffmpeg`
- Ubuntu: `apt install ffmpeg`

### Frontend

```bash
cd frontend
npm install
```

### Run

```bash
# Terminal 1 - backend
cd backend && uv run uvicorn src.main:app --reload

# Terminal 2 - frontend
cd frontend && npm run dev
```

Open http://localhost:5173

## Usage

- **Type** a message and press Enter or click Send
- **Hold** the mic button to record, release to send (push-to-talk)

API calls and errors are logged to the backend terminal.
