"""Web adapters for STT and TTS to work over WebSocket.

Provides base64 encoding/decoding for audio transport and async interfaces
suitable for web applications.
"""

from __future__ import annotations

import base64
import io
from typing import Literal

import soundfile as sf

from agent_demos.voice.stt import SpeechToText
from agent_demos.voice.tts import TextToSpeech, Voice


class WebSTT:
    """Web-friendly Speech-to-Text adapter.

    Handles base64-encoded audio from web clients and provides async transcription.

    Example:
        >>> stt = WebSTT()
        >>> text = await stt.transcribe_base64(audio_base64, "audio/webm")
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the web STT adapter.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: Whisper model to use. Defaults to whisper-1.
        """
        self._stt = SpeechToText(api_key=api_key, model=model)

    def transcribe_base64(
        self,
        audio_base64: str,
        mime_type: str = "audio/webm",
        language: str | None = None,
    ) -> str:
        """Transcribe base64-encoded audio.

        Args:
            audio_base64: Base64-encoded audio data.
            mime_type: MIME type of the audio (e.g., "audio/webm", "audio/wav").
            language: Optional language code (e.g., "en", "es").

        Returns:
            Transcribed text.
        """
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(audio_base64)

        # Determine file extension from mime type
        ext_map = {
            "audio/webm": "webm",
            "audio/wav": "wav",
            "audio/wave": "wav",
            "audio/mp3": "mp3",
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg",
            "audio/flac": "flac",
            "audio/m4a": "m4a",
            "audio/mp4": "m4a",
        }
        ext = ext_map.get(mime_type, "webm")
        filename = f"audio.{ext}"

        return self._stt.transcribe_bytes(audio_bytes, filename=filename, language=language)

    async def transcribe_base64_async(
        self,
        audio_base64: str,
        mime_type: str = "audio/webm",
        language: str | None = None,
    ) -> str:
        """Async version of transcribe_base64.

        Uses thread pool executor for blocking OpenAI API call.

        Args:
            audio_base64: Base64-encoded audio data.
            mime_type: MIME type of the audio.
            language: Optional language code.

        Returns:
            Transcribed text.
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.transcribe_base64(audio_base64, mime_type, language),
        )


class WebTTS:
    """Web-friendly Text-to-Speech adapter.

    Synthesizes audio and returns it as base64-encoded data suitable for web playback.

    Example:
        >>> tts = WebTTS()
        >>> audio_base64, mime_type = await tts.synthesize_base64("Hello, world!")
    """

    # Web-compatible output format
    DEFAULT_WEB_FORMAT: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = "mp3"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        voice: Voice = "alloy",
    ) -> None:
        """Initialize the web TTS adapter.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: TTS model to use. Defaults to tts-1.
            voice: Default voice to use.
        """
        self._tts = TextToSpeech(api_key=api_key, model=model, voice=voice)

    def synthesize_base64(
        self,
        text: str,
        voice: Voice | None = None,
        response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] | None = None,
        speed: float = 1.0,
    ) -> tuple[str, str]:
        """Synthesize speech and return as base64.

        Args:
            text: Text to synthesize.
            voice: Voice to use. Overrides default.
            response_format: Audio format. Defaults to mp3 for web compatibility.
            speed: Playback speed (0.25 to 4.0).

        Returns:
            Tuple of (base64-encoded audio, MIME type).
        """
        fmt = response_format or self.DEFAULT_WEB_FORMAT
        audio_bytes = self._tts.synthesize(
            text,
            voice=voice,
            response_format=fmt,
            speed=speed,
        )

        # Encode to base64
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Get MIME type
        mime_map = {
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "pcm": "audio/pcm",
        }
        mime_type = mime_map.get(fmt, "audio/mpeg")

        return audio_base64, mime_type

    async def synthesize_base64_async(
        self,
        text: str,
        voice: Voice | None = None,
        response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] | None = None,
        speed: float = 1.0,
    ) -> tuple[str, str]:
        """Async version of synthesize_base64.

        Uses thread pool executor for blocking OpenAI API call.

        Args:
            text: Text to synthesize.
            voice: Voice to use.
            response_format: Audio format.
            speed: Playback speed.

        Returns:
            Tuple of (base64-encoded audio, MIME type).
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.synthesize_base64(text, voice, response_format, speed),
        )

    @property
    def available_voices(self) -> list[Voice]:
        """List of available voice options."""
        return self._tts.available_voices


def convert_webm_to_wav(webm_bytes: bytes) -> bytes:
    """Convert WebM audio to WAV format.

    Some processing pipelines require WAV format. This utility converts
    WebM (commonly used by browsers) to WAV.

    Args:
        webm_bytes: Raw WebM audio bytes.

    Returns:
        WAV audio bytes.
    """
    # Read WebM using soundfile (via libsndfile)
    input_buffer = io.BytesIO(webm_bytes)
    try:
        data, sample_rate = sf.read(input_buffer)
    except Exception:
        # If soundfile can't read it directly, it might need ffmpeg
        # For now, return as-is and let the API handle it
        return webm_bytes

    # Write as WAV
    output_buffer = io.BytesIO()
    sf.write(output_buffer, data, sample_rate, format="WAV")
    output_buffer.seek(0)
    return output_buffer.read()
