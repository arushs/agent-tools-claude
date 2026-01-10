"""Voice processing utilities for agent demos.

This module provides voice-enabled AI agent capabilities:
- Speech-to-Text (STT) using OpenAI Whisper
- Text-to-Speech (TTS) using OpenAI TTS
- VoiceAgent combining STT, Claude, and TTS for conversational AI
"""

from agent_demos.voice.agent import VoiceAgent
from agent_demos.voice.stt import SpeechToText
from agent_demos.voice.tts import TextToSpeech, Voice

__all__ = ["SpeechToText", "TextToSpeech", "Voice", "VoiceAgent"]
