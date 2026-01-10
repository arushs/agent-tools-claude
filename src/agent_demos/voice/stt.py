"""Speech-to-Text wrapper using OpenAI Whisper API."""

from __future__ import annotations

import io
import os
from collections.abc import Generator
from pathlib import Path
from typing import BinaryIO

import sounddevice as sd
import soundfile as sf
from openai import OpenAI


class SpeechToText:
    """Wrapper around OpenAI's Whisper API for speech transcription.

    This client provides synchronous transcription from audio files or streams.

    Example:
        >>> stt = SpeechToText()
        >>> text = stt.transcribe("audio.wav")
        >>> print(text)
        "Hello, this is a test recording."
    """

    DEFAULT_MODEL = "whisper-1"
    DEFAULT_SAMPLE_RATE = 16000
    DEFAULT_CHANNELS = 1

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize the Speech-to-Text client.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: Whisper model to use. Defaults to whisper-1.
        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "API key required. Pass api_key or set OPENAI_API_KEY environment variable."
            )

        self._client = OpenAI(api_key=self._api_key)
        self._model = model or self.DEFAULT_MODEL

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
        prompt: str | None = None,
    ) -> str:
        """Transcribe audio from a file.

        Args:
            audio_path: Path to the audio file.
            language: Optional language code (e.g., "en", "es", "fr").
            prompt: Optional prompt to guide transcription style.

        Returns:
            Transcribed text.
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with open(path, "rb") as audio_file:
            return self._transcribe_file(audio_file, path.name, language, prompt)

    def transcribe_bytes(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
        prompt: str | None = None,
    ) -> str:
        """Transcribe audio from bytes.

        Args:
            audio_data: Raw audio data as bytes.
            filename: Filename hint for the audio format.
            language: Optional language code (e.g., "en", "es", "fr").
            prompt: Optional prompt to guide transcription style.

        Returns:
            Transcribed text.
        """
        audio_file = io.BytesIO(audio_data)
        audio_file.name = filename
        return self._transcribe_file(audio_file, filename, language, prompt)

    def _transcribe_file(
        self,
        audio_file: BinaryIO,
        filename: str,
        language: str | None,
        prompt: str | None,
    ) -> str:
        """Internal method to transcribe an audio file object.

        Args:
            audio_file: File-like object containing audio data.
            filename: Name of the file (used for format detection).
            language: Optional language code.
            prompt: Optional prompt.

        Returns:
            Transcribed text.
        """
        kwargs: dict = {"model": self._model, "file": audio_file}

        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        response = self._client.audio.transcriptions.create(**kwargs)
        return response.text

    def transcribe_stream(
        self,
        audio_stream: Generator[bytes, None, None],
        chunk_duration_seconds: float = 5.0,
    ) -> Generator[str, None, None]:
        """Transcribe audio from a streaming source.

        Collects audio chunks and transcribes them in batches.

        Args:
            audio_stream: Generator yielding audio data chunks.
            chunk_duration_seconds: Duration of audio to collect before transcribing.

        Yields:
            Transcribed text for each batch.
        """
        buffer = io.BytesIO()
        sample_rate = self.DEFAULT_SAMPLE_RATE
        samples_per_chunk = int(sample_rate * chunk_duration_seconds)
        current_samples = 0

        for chunk in audio_stream:
            buffer.write(chunk)
            # Estimate samples (assuming 16-bit mono audio)
            current_samples += len(chunk) // 2

            if current_samples >= samples_per_chunk:
                # Get accumulated audio data
                buffer.seek(0)
                audio_data = buffer.read()
                buffer = io.BytesIO()
                current_samples = 0

                # Convert to WAV format for transcription
                wav_buffer = io.BytesIO()
                sf.write(
                    wav_buffer,
                    self._bytes_to_samples(audio_data),
                    sample_rate,
                    format="WAV",
                )
                wav_buffer.seek(0)
                wav_buffer.name = "chunk.wav"

                try:
                    text = self._transcribe_file(wav_buffer, "chunk.wav", None, None)
                    if text.strip():
                        yield text
                except Exception:
                    # Skip chunks that fail to transcribe
                    continue

        # Transcribe remaining audio
        if current_samples > 0:
            buffer.seek(0)
            audio_data = buffer.read()

            wav_buffer = io.BytesIO()
            sf.write(
                wav_buffer,
                self._bytes_to_samples(audio_data),
                sample_rate,
                format="WAV",
            )
            wav_buffer.seek(0)
            wav_buffer.name = "chunk.wav"

            try:
                text = self._transcribe_file(wav_buffer, "chunk.wav", None, None)
                if text.strip():
                    yield text
            except Exception:
                pass

    def _bytes_to_samples(self, audio_bytes: bytes) -> list[float]:
        """Convert raw audio bytes to sample values.

        Assumes 16-bit signed integer audio.

        Args:
            audio_bytes: Raw audio data.

        Returns:
            List of normalized sample values.
        """
        import struct

        samples = []
        for i in range(0, len(audio_bytes), 2):
            if i + 1 < len(audio_bytes):
                sample = struct.unpack("<h", audio_bytes[i : i + 2])[0]
                samples.append(sample / 32768.0)
        return samples

    def record_and_transcribe(
        self,
        duration_seconds: float,
        sample_rate: int | None = None,
    ) -> str:
        """Record audio from the microphone and transcribe it.

        Args:
            duration_seconds: How long to record in seconds.
            sample_rate: Sample rate for recording. Defaults to 16000.

        Returns:
            Transcribed text.
        """
        rate = sample_rate or self.DEFAULT_SAMPLE_RATE

        # Record audio
        recording = sd.rec(
            int(duration_seconds * rate),
            samplerate=rate,
            channels=self.DEFAULT_CHANNELS,
            dtype="float32",
        )
        sd.wait()

        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, recording, rate, format="WAV")
        wav_buffer.seek(0)

        return self.transcribe_bytes(wav_buffer.read(), "recording.wav")
