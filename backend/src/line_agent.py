"""Cartesia Line agent for TicTalk voice chat."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from line.llm_agent import LlmAgent, LlmConfig, end_call
from line.voice_agent_app import CallRequest, PreCallResult, VoiceAgentApp

from .system_prompts import CLAUDE_SYSTEM_PROMPT

DEFAULT_VOICE_ID = os.getenv("TTS_VOICE_ID", "b56c6aac-f35f-46f7-9361-e8f078cec72e")
TTS_MODEL_ID = "sonic-3"


async def pre_call_handler(call_request: CallRequest):
    return PreCallResult(
        config={
            "tts": {
                "voice": DEFAULT_VOICE_ID,
                "model": TTS_MODEL_ID,
                "language": "en",
            }
        }
    )


async def get_agent(env, call_request: CallRequest):
    return LlmAgent(
        model="anthropic/claude-haiku-4-5-20251001",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        tools=[end_call],
        config=LlmConfig(
            system_prompt=CLAUDE_SYSTEM_PROMPT,
            introduction="Hello! How can I help you today?",
        ),
    )


app = VoiceAgentApp(get_agent=get_agent, pre_call_handler=pre_call_handler)

if __name__ == "__main__":
    app.run()
