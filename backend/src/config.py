"""Configuration and logging."""

import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CARTESIA_VERSION = "2025-04-16"
DEFAULT_VOICE_ID = os.getenv("TTS_VOICE_ID", "b56c6aac-f35f-46f7-9361-e8f078cec72e")  # Tabitha
TTS_MODEL_ID = "sonic-3"


def log(msg: str, prefix: str = "API") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{prefix}] {msg}")


def log_latency(stage: str, elapsed_ms: float) -> None:
    log(f"{stage} latency: {elapsed_ms:.0f}ms", "LATENCY")
