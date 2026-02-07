# TicTalk Backend - Cartesia + Claude Voice API

FastAPI backend using Cartesia Ink (batch STT), Claude, and Cartesia Sonic TTS.

## Setup

Python 3.11 or 3.12 required.

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env with CARTESIA_API_KEY and ANTHROPIC_API_KEY
```

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
