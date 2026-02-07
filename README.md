# TicTalk - Voice Chat with Cartesia Line + Claude

Voice chat: React + shadcn frontend, FastAPI backend. Cartesia Line SDK for real-time voice (STT, LLM, TTS) and POST /api/chat for text fallback.

## Setup

### Backend

Python 3.11 or 3.12 required. Uses [uv](https://docs.astral.sh/uv/) for package management.

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env: CARTESIA_API_KEY, ANTHROPIC_API_KEY
```

### Deploy Cartesia Line Agent (for voice)

The frontend connects to Cartesia's Calls API for voice. Deploy to get an agent ID:

```bash
cd backend
cartesia init   # Create new agent, name it
cartesia deploy # Entry: main_line.py or uv run python main_line.py
cartesia env set ANTHROPIC_API_KEY=your-key
```

Get the agent ID from the deploy output or [Cartesia Console](https://play.cartesia.ai/agents).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env: VITE_API_URL=http://localhost:8000, VITE_CARTESIA_AGENT_ID=your-agent-id
```

## Run

From project root:

```bash
# Terminal 1 - backend (port 8000)
./run-backend.sh

# Terminal 2 - frontend (port 5173)
cd frontend && npm run dev
```

Open http://localhost:5173

## Usage

- **Type** and Send: uses POST /api/chat (Claude + Cartesia TTS)
- **Hold mic** to talk, release to send: uses Cartesia Line Calls API

## Troubleshooting

- **VITE_CARTESIA_AGENT_ID not configured**: Deploy with `cartesia deploy`, set agent ID in frontend .env
- **python-multipart required**: Run backend via `./run-backend.sh` or `cd backend && uv run uvicorn src.main:app --reload`
