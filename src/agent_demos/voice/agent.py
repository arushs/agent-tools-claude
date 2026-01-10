"""Voice-enabled agent using Claude with STT and TTS capabilities."""

from __future__ import annotations

import io
from collections.abc import Callable
from typing import Any

import sounddevice as sd
import soundfile as sf

from agent_demos.core.claude_client import ClaudeClient, MessageParam, ToolDefinition
from agent_demos.voice.stt import SpeechToText
from agent_demos.voice.tts import TextToSpeech, Voice


class VoiceAgent:
    """Voice-enabled agent that combines STT, Claude, and TTS for conversational AI.

    This agent provides a complete voice interface:
    - Listen: Record audio from microphone and transcribe using Whisper
    - Process: Send text to Claude with optional tool support
    - Speak: Synthesize Claude's response using TTS and play it

    Example:
        >>> agent = VoiceAgent()
        >>> # Single interaction
        >>> user_text = agent.listen(duration=5.0)
        >>> response = agent.process(user_text)
        >>> agent.speak(response)

        >>> # Or use the conversation loop
        >>> tools = [{"name": "get_time", "description": "Get current time", "input_schema": {...}}]
        >>> agent.run_conversation(tools=tools, tool_executor=my_executor)
    """

    DEFAULT_LISTEN_DURATION = 5.0
    DEFAULT_SAMPLE_RATE = 16000

    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        voice: Voice = "alloy",
        system_prompt: str | None = None,
    ) -> None:
        """Initialize the VoiceAgent.

        Args:
            openai_api_key: OpenAI API key for STT/TTS. Uses OPENAI_API_KEY env var if not provided.
            anthropic_api_key: Anthropic API key for Claude. Uses ANTHROPIC_API_KEY env var if not provided.
            voice: TTS voice to use. Defaults to "alloy".
            system_prompt: System prompt for Claude. Optional.
        """
        self._stt = SpeechToText(api_key=openai_api_key)
        self._tts = TextToSpeech(api_key=openai_api_key, voice=voice)
        self._claude = ClaudeClient(api_key=anthropic_api_key)
        self._system_prompt = system_prompt
        self._conversation: list[MessageParam] = []

    def listen(
        self,
        duration: float | None = None,
        sample_rate: int | None = None,
    ) -> str:
        """Record audio from the microphone and transcribe it.

        Args:
            duration: Recording duration in seconds. Defaults to 5.0.
            sample_rate: Sample rate for recording. Defaults to 16000.

        Returns:
            Transcribed text from the recording.
        """
        dur = duration or self.DEFAULT_LISTEN_DURATION
        rate = sample_rate or self.DEFAULT_SAMPLE_RATE

        # Record audio
        recording = sd.rec(
            int(dur * rate),
            samplerate=rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, recording, rate, format="WAV")
        wav_buffer.seek(0)

        # Transcribe
        return self._stt.transcribe_bytes(wav_buffer.read(), "recording.wav")

    def listen_until_silence(
        self,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
        sample_rate: int | None = None,
    ) -> str:
        """Record audio until silence is detected.

        Args:
            silence_threshold: RMS threshold below which audio is considered silence.
            silence_duration: Seconds of silence before stopping recording.
            max_duration: Maximum recording duration in seconds.
            sample_rate: Sample rate for recording. Defaults to 16000.

        Returns:
            Transcribed text from the recording.
        """
        import numpy as np

        rate = sample_rate or self.DEFAULT_SAMPLE_RATE
        chunk_duration = 0.1  # 100ms chunks
        chunk_samples = int(rate * chunk_duration)
        silence_chunks_needed = int(silence_duration / chunk_duration)
        max_chunks = int(max_duration / chunk_duration)

        audio_chunks: list = []
        silence_count = 0
        has_speech = False

        for _ in range(max_chunks):
            chunk = sd.rec(chunk_samples, samplerate=rate, channels=1, dtype="float32")
            sd.wait()
            audio_chunks.append(chunk)

            # Calculate RMS
            rms = float(np.sqrt(np.mean(chunk**2)))

            if rms > silence_threshold:
                has_speech = True
                silence_count = 0
            elif has_speech:
                silence_count += 1
                if silence_count >= silence_chunks_needed:
                    break

        if not audio_chunks:
            return ""

        # Combine chunks
        full_audio = np.concatenate(audio_chunks)

        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, full_audio, rate, format="WAV")
        wav_buffer.seek(0)

        return self._stt.transcribe_bytes(wav_buffer.read(), "recording.wav")

    def speak(self, text: str, voice: Voice | None = None) -> None:
        """Synthesize text to speech and play it.

        Args:
            text: Text to speak.
            voice: Voice to use. Uses agent's default voice if not provided.
        """
        if not text.strip():
            return

        self._tts.speak(text, voice=voice)

    def process(
        self,
        text: str,
        tools: list[ToolDefinition] | None = None,
        tool_executor: Callable[[str, dict[str, Any]], str] | None = None,
    ) -> str:
        """Process user text with Claude and return the response.

        Args:
            text: User's text input.
            tools: Optional list of tool definitions.
            tool_executor: Function to execute tools. Required if tools are provided.

        Returns:
            Claude's text response.
        """
        self._conversation.append({"role": "user", "content": text})

        if tools and tool_executor:
            response, self._conversation = self._claude.process_with_tools(
                messages=self._conversation,
                tools=tools,
                tool_executor=tool_executor,
                system=self._system_prompt,
            )
        else:
            response_msg = self._claude.create_message(
                messages=self._conversation,
                system=self._system_prompt,
            )
            response = self._claude._extract_text(response_msg)
            self._conversation.append({"role": "assistant", "content": response})

        return response

    async def process_async(
        self,
        text: str,
        tools: list[ToolDefinition] | None = None,
        tool_executor: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> str:
        """Process user text with Claude asynchronously.

        Args:
            text: User's text input.
            tools: Optional list of tool definitions.
            tool_executor: Function to execute tools. Can be sync or async.

        Returns:
            Claude's text response.
        """
        self._conversation.append({"role": "user", "content": text})

        if tools and tool_executor:
            response, self._conversation = await self._claude.process_with_tools_async(
                messages=self._conversation,
                tools=tools,
                tool_executor=tool_executor,
                system=self._system_prompt,
            )
        else:
            response_msg = await self._claude.create_message_async(
                messages=self._conversation,
                system=self._system_prompt,
            )
            response = self._claude._extract_text(response_msg)
            self._conversation.append({"role": "assistant", "content": response})

        return response

    def run_conversation(
        self,
        tools: list[ToolDefinition] | None = None,
        tool_executor: Callable[[str, dict[str, Any]], str] | None = None,
        listen_duration: float | None = None,
        exit_phrases: list[str] | None = None,
        greeting: str | None = None,
    ) -> None:
        """Run an interactive voice conversation loop.

        Continuously listens for user input, processes it with Claude,
        and speaks the response until an exit phrase is detected.

        Args:
            tools: Optional list of tool definitions.
            tool_executor: Function to execute tools.
            listen_duration: Duration for each listen. Defaults to 5.0 seconds.
            exit_phrases: Phrases that end the conversation. Defaults to ["goodbye", "bye", "exit", "quit"].
            greeting: Optional greeting to speak at the start.
        """
        exit_words = exit_phrases or ["goodbye", "bye", "exit", "quit"]
        duration = listen_duration or self.DEFAULT_LISTEN_DURATION

        if greeting:
            self.speak(greeting)

        while True:
            # Listen for user input
            try:
                user_text = self.listen(duration=duration)
            except Exception as e:
                print(f"Error recording audio: {e}")
                continue

            if not user_text.strip():
                continue

            print(f"You: {user_text}")

            # Check for exit phrases
            if any(phrase in user_text.lower() for phrase in exit_words):
                farewell = "Goodbye! It was nice talking with you."
                print(f"Assistant: {farewell}")
                self.speak(farewell)
                break

            # Process with Claude
            try:
                response = self.process(user_text, tools=tools, tool_executor=tool_executor)
            except Exception as e:
                response = f"I'm sorry, I encountered an error: {e}"

            print(f"Assistant: {response}")

            # Speak the response
            try:
                self.speak(response)
            except Exception as e:
                print(f"Error speaking response: {e}")

    def run_conversation_vad(
        self,
        tools: list[ToolDefinition] | None = None,
        tool_executor: Callable[[str, dict[str, Any]], str] | None = None,
        exit_phrases: list[str] | None = None,
        greeting: str | None = None,
    ) -> None:
        """Run an interactive voice conversation with voice activity detection.

        Uses silence detection instead of fixed duration for more natural conversation.

        Args:
            tools: Optional list of tool definitions.
            tool_executor: Function to execute tools.
            exit_phrases: Phrases that end the conversation.
            greeting: Optional greeting to speak at the start.
        """
        exit_words = exit_phrases or ["goodbye", "bye", "exit", "quit"]

        if greeting:
            self.speak(greeting)

        while True:
            # Listen until silence
            try:
                user_text = self.listen_until_silence()
            except Exception as e:
                print(f"Error recording audio: {e}")
                continue

            if not user_text.strip():
                continue

            print(f"You: {user_text}")

            # Check for exit phrases
            if any(phrase in user_text.lower() for phrase in exit_words):
                farewell = "Goodbye! It was nice talking with you."
                print(f"Assistant: {farewell}")
                self.speak(farewell)
                break

            # Process with Claude
            try:
                response = self.process(user_text, tools=tools, tool_executor=tool_executor)
            except Exception as e:
                response = f"I'm sorry, I encountered an error: {e}"

            print(f"Assistant: {response}")

            # Speak the response
            try:
                self.speak(response)
            except Exception as e:
                print(f"Error speaking response: {e}")

    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self._conversation = []

    @property
    def conversation_history(self) -> list[MessageParam]:
        """Get the current conversation history.

        Returns:
            List of conversation messages.
        """
        return list(self._conversation)
