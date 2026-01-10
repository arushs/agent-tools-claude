"""Voice processing utilities for agent demos.

This module provides voice-enabled AI agent capabilities:
- Speech-to-Text (STT) using OpenAI Whisper
- Text-to-Speech (TTS) using OpenAI TTS
- VoiceAgent combining STT, Claude, and TTS for conversational AI
- WebSTT/WebTTS for WebSocket-based voice interactions
"""

from agent_demos.voice.agent import VoiceAgent
from agent_demos.voice.stt import SpeechToText
from agent_demos.voice.tts import TextToSpeech, Voice
from agent_demos.voice.web_adapter import WebSTT, WebTTS

__all__ = [
    "SpeechToText",
    "TextToSpeech",
    "Voice",
    "VoiceAgent",
    "WebSTT",
    "WebTTS",
]
