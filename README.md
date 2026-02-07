# TicTalk - Voice Chat with Cartesia Line + Claude

Voice chat app: React + shadcn frontend, FastAPI backend. Uses Cartesia Line SDK for real-time voice (STT, LLM, TTS) and POST /api/chat for text fallback.

## Setup

### Backend

Python 3.11 or 3.12 required.

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env with CARTESIA_API_KEY and ANTHROPIC_API_KEY
```

### Deploy Cartesia Line Agent (for voice)

The frontend connects to Cartesia's Calls API for voice. Deploy your agent to get an agent ID:

```bash
cd backend
cartesia init   # Choose "Create new" and name your agent
# Point entry to main_line.py if prompted, or run: uv run python main_line.py
cartesia deploy
```

Set env vars for the deployed agent:

```bash
cartesia env set ANTHROPIC_API_KEY=your-key
```

Get the agent ID from the deploy output or Cartesia Console. You will need it for the frontend.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env: VITE_API_URL=http://localhost:8000, VITE_CARTESIA_AGENT_ID=your-agent-id
```

### Run

```bash
# Terminal 1 - backend (from project root)
./run-backend.sh

# Terminal 2 - frontend
cd frontend && npm run dev
```

Open http://localhost:5173

## Usage

- **Type** a message and press Enter or click Send (uses POST /api/chat)
- **Hold** the mic button to talk, release to send (uses Cartesia Line Calls API)

The backend provides the token endpoint for secure client access to Cartesia.

## Troubleshooting

- **VITE_CARTESIA_AGENT_ID not configured**: Deploy the Line agent with `cartesia deploy` and set the agent ID in frontend .env
- **python-multipart required**: Use `./run-backend.sh` or `cd backend && uv run uvicorn src.main:app --reload` so that uv run uses the backend environment
