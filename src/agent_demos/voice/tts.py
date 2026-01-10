"""Text-to-Speech wrapper using OpenAI TTS API."""

from __future__ import annotations

import io
import os
from collections.abc import Generator
from typing import Literal

import sounddevice as sd
import soundfile as sf
from openai import OpenAI

Voice = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
ResponseFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]


class TextToSpeech:
    """Wrapper around OpenAI's TTS API for speech synthesis.

    This client provides synchronous text-to-speech conversion with
    support for multiple voices and output formats.

    Example:
        >>> tts = TextToSpeech()
        >>> audio_bytes = tts.synthesize("Hello, world!")
        >>> tts.play(audio_bytes)
    """

    DEFAULT_MODEL = "tts-1"
    DEFAULT_VOICE: Voice = "alloy"
    DEFAULT_FORMAT: ResponseFormat = "wav"
    DEFAULT_SAMPLE_RATE = 24000

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        voice: Voice | None = None,
    ) -> None:
        """Initialize the Text-to-Speech client.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: TTS model to use. Defaults to tts-1.
            voice: Voice to use. Defaults to alloy.
        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "API key required. Pass api_key or set OPENAI_API_KEY environment variable."
            )

        self._client = OpenAI(api_key=self._api_key)
        self._model = model or self.DEFAULT_MODEL
        self._voice = voice or self.DEFAULT_VOICE

    def synthesize(
        self,
        text: str,
        voice: Voice | None = None,
        response_format: ResponseFormat | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize speech from text.

        Args:
            text: Text to convert to speech.
            voice: Voice to use. Overrides default voice.
            response_format: Audio format. Defaults to wav.
            speed: Playback speed (0.25 to 4.0). Defaults to 1.0.

        Returns:
            Audio data as bytes.
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        response = self._client.audio.speech.create(
            model=self._model,
            voice=voice or self._voice,
            input=text,
            response_format=response_format or self.DEFAULT_FORMAT,
            speed=speed,
        )

        return response.content

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: Voice | None = None,
        response_format: ResponseFormat | None = None,
        speed: float = 1.0,
    ) -> None:
        """Synthesize speech and save to a file.

        Args:
            text: Text to convert to speech.
            output_path: Path to save the audio file.
            voice: Voice to use. Overrides default voice.
            response_format: Audio format. Defaults to wav.
            speed: Playback speed (0.25 to 4.0). Defaults to 1.0.
        """
        audio_data = self.synthesize(
            text,
            voice=voice,
            response_format=response_format,
            speed=speed,
        )

        with open(output_path, "wb") as f:
            f.write(audio_data)

    def synthesize_stream(
        self,
        text: str,
        voice: Voice | None = None,
        speed: float = 1.0,
    ) -> Generator[bytes, None, None]:
        """Synthesize speech with streaming response.

        Args:
            text: Text to convert to speech.
            voice: Voice to use. Overrides default voice.
            speed: Playback speed (0.25 to 4.0). Defaults to 1.0.

        Yields:
            Audio data chunks as bytes.
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        with self._client.audio.speech.with_streaming_response.create(
            model=self._model,
            voice=voice or self._voice,
            input=text,
            response_format="pcm",
            speed=speed,
        ) as response:
            for chunk in response.iter_bytes(chunk_size=4096):
                yield chunk

    def play(
        self,
        audio_data: bytes,
        sample_rate: int | None = None,
    ) -> None:
        """Play audio data through the default audio device.

        Args:
            audio_data: Audio data as bytes (WAV format expected).
            sample_rate: Sample rate. Auto-detected from WAV header if not provided.
        """
        # Load audio data
        audio_buffer = io.BytesIO(audio_data)
        data, rate = sf.read(audio_buffer)

        # Use provided sample rate or detected rate
        playback_rate = sample_rate or rate

        # Play audio
        sd.play(data, samplerate=int(playback_rate))
        sd.wait()

    def play_stream(
        self,
        audio_stream: Generator[bytes, None, None],
        sample_rate: int | None = None,
    ) -> None:
        """Play streaming audio data.

        Args:
            audio_stream: Generator yielding PCM audio chunks.
            sample_rate: Sample rate. Defaults to 24000.
        """
        import struct

        rate = sample_rate or self.DEFAULT_SAMPLE_RATE

        # Collect all chunks first (streaming playback requires more complex handling)
        audio_buffer = io.BytesIO()
        for chunk in audio_stream:
            audio_buffer.write(chunk)

        audio_buffer.seek(0)
        raw_data = audio_buffer.read()

        # Convert PCM to float samples (16-bit signed integers)
        samples = []
        for i in range(0, len(raw_data), 2):
            if i + 1 < len(raw_data):
                sample = struct.unpack("<h", raw_data[i : i + 2])[0]
                samples.append(sample / 32768.0)

        if samples:
            import numpy as np

            data = np.array(samples, dtype=np.float32)
            sd.play(data, samplerate=rate)
            sd.wait()

    def speak(self, text: str, voice: Voice | None = None, speed: float = 1.0) -> None:
        """Synthesize and immediately play speech.

        Convenience method that combines synthesize() and play().

        Args:
            text: Text to speak.
            voice: Voice to use. Overrides default voice.
            speed: Playback speed (0.25 to 4.0). Defaults to 1.0.
        """
        audio_data = self.synthesize(text, voice=voice, speed=speed)
        self.play(audio_data)

    @property
    def available_voices(self) -> list[Voice]:
        """List of available voice options.

        Returns:
            List of voice names.
        """
        return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
