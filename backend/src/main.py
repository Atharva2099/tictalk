"""FastAPI backend for Cartesia + Claude voice chat."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import register_routes

app = FastAPI(title="TicTalk Voice API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routes(app)
