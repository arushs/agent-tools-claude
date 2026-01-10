"""Claude API client wrapper with tool execution support."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, TypedDict

import anthropic
from anthropic.types import (
    ContentBlock,
    Message,
    TextBlock,
    ToolResultBlockParam,
    ToolUseBlock,
)


class ToolDefinition(TypedDict):
    """Tool definition for Claude API."""

    name: str
    description: str
    input_schema: dict[str, Any]


class MessageParam(TypedDict, total=False):
    """Message parameter for Claude API."""

    role: str
    content: str | list[ContentBlock | ToolResultBlockParam]


class ClaudeClient:
    """Wrapper around the Anthropic Claude API with tool execution support.

    This client provides a simplified interface for interacting with Claude,
    including automatic handling of tool use patterns and execution loops.

    Example:
        >>> client = ClaudeClient()
        >>> tools = [{
        ...     "name": "get_weather",
        ...     "description": "Get the current weather",
        ...     "input_schema": {"type": "object", "properties": {"location": {"type": "string"}}}
        ... }]
        >>> def execute_tool(name: str, input: dict) -> str:
        ...     if name == "get_weather":
        ...         return f"Weather in {input['location']}: Sunny, 72F"
        ...     return "Unknown tool"
        >>> response = client.process_with_tools(
        ...     messages=[{"role": "user", "content": "What's the weather in NYC?"}],
        ...     tools=tools,
        ...     tool_executor=execute_tool
        ... )
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 4096
    MAX_TOOL_ITERATIONS = 10

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> None:
        """Initialize the Claude client.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            model: Model to use. Defaults to claude-sonnet-4-20250514.
            max_tokens: Maximum tokens in response. Defaults to 4096.
        """
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "API key required. Pass api_key or set ANTHROPIC_API_KEY environment variable."
            )

        self._client = anthropic.Anthropic(api_key=self._api_key)
        self._async_client: anthropic.AsyncAnthropic | None = None
        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS

    @property
    def async_client(self) -> anthropic.AsyncAnthropic:
        """Lazy-initialize async client."""
        if self._async_client is None:
            self._async_client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._async_client

    def create_message(
        self,
        messages: list[MessageParam],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        **kwargs: Any,
    ) -> Message:
        """Create a single message with Claude.

        Args:
            messages: Conversation messages.
            system: System prompt.
            tools: Tool definitions.
            **kwargs: Additional arguments passed to the API.

        Returns:
            Claude's response message.
        """
        request_kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
            **kwargs,
        }

        if system:
            request_kwargs["system"] = system

        if tools:
            request_kwargs["tools"] = tools

        return self._client.messages.create(**request_kwargs)

    async def create_message_async(
        self,
        messages: list[MessageParam],
        system: str | None = None,
        tools: list[ToolDefinition] | None = None,
        **kwargs: Any,
    ) -> Message:
        """Create a single message with Claude (async).

        Args:
            messages: Conversation messages.
            system: System prompt.
            tools: Tool definitions.
            **kwargs: Additional arguments passed to the API.

        Returns:
            Claude's response message.
        """
        request_kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
            **kwargs,
        }

        if system:
            request_kwargs["system"] = system

        if tools:
            request_kwargs["tools"] = tools

        return await self.async_client.messages.create(**request_kwargs)

    def _extract_tool_uses(self, message: Message) -> list[ToolUseBlock]:
        """Extract tool use blocks from a message.

        Args:
            message: Claude's response message.

        Returns:
            List of tool use blocks.
        """
        return [block for block in message.content if isinstance(block, ToolUseBlock)]

    def _extract_text(self, message: Message) -> str:
        """Extract text content from a message.

        Args:
            message: Claude's response message.

        Returns:
            Concatenated text content.
        """
        text_blocks = [block for block in message.content if isinstance(block, TextBlock)]
        return "".join(block.text for block in text_blocks)

    def _build_tool_results(
        self,
        tool_uses: list[ToolUseBlock],
        tool_executor: Callable[[str, dict[str, Any]], str],
    ) -> list[ToolResultBlockParam]:
        """Execute tools and build result blocks.

        Args:
            tool_uses: List of tool use blocks from Claude.
            tool_executor: Function that executes tools and returns results.

        Returns:
            List of tool result blocks.
        """
        results: list[ToolResultBlockParam] = []
        for tool_use in tool_uses:
            try:
                result = tool_executor(tool_use.name, dict(tool_use.input))
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": f"Error executing tool: {e}",
                        "is_error": True,
                    }
                )
        return results

    async def _build_tool_results_async(
        self,
        tool_uses: list[ToolUseBlock],
        tool_executor: Callable[[str, dict[str, Any]], Any],
    ) -> list[ToolResultBlockParam]:
        """Execute tools and build result blocks (async).

        Args:
            tool_uses: List of tool use blocks from Claude.
            tool_executor: Async function that executes tools and returns results.

        Returns:
            List of tool result blocks.
        """
        import asyncio

        results: list[ToolResultBlockParam] = []
        for tool_use in tool_uses:
            try:
                result = tool_executor(tool_use.name, dict(tool_use.input))
                if asyncio.iscoroutine(result):
                    result = await result
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": str(result),
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": f"Error executing tool: {e}",
                        "is_error": True,
                    }
                )
        return results

    def process_with_tools(
        self,
        messages: list[MessageParam],
        tools: list[ToolDefinition],
        tool_executor: Callable[[str, dict[str, Any]], str],
        system: str | None = None,
        max_iterations: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, list[MessageParam]]:
        """Process a conversation with tool execution loop.

        This method handles the complete tool use pattern:
        1. Send messages to Claude
        2. If Claude requests tool use, execute the tools
        3. Send tool results back to Claude
        4. Repeat until Claude responds with text only

        Args:
            messages: Initial conversation messages.
            tools: Tool definitions.
            tool_executor: Function to execute tools. Takes (tool_name, tool_input) and returns result string.
            system: System prompt.
            max_iterations: Maximum tool use iterations. Defaults to MAX_TOOL_ITERATIONS.
            **kwargs: Additional arguments passed to the API.

        Returns:
            Tuple of (final_text_response, full_conversation_history).

        Raises:
            RuntimeError: If max iterations exceeded.
        """
        max_iter = max_iterations or self.MAX_TOOL_ITERATIONS
        conversation: list[MessageParam] = list(messages)

        for _ in range(max_iter):
            response = self.create_message(
                messages=conversation,
                system=system,
                tools=tools,
                **kwargs,
            )

            # Add assistant response to conversation
            conversation.append({"role": "assistant", "content": response.content})

            # Check if we need to execute tools
            tool_uses = self._extract_tool_uses(response)

            if not tool_uses:
                # No more tool calls, return the final text
                return self._extract_text(response), conversation

            # Execute tools and add results to conversation
            tool_results = self._build_tool_results(tool_uses, tool_executor)
            conversation.append({"role": "user", "content": tool_results})

        raise RuntimeError(f"Tool execution exceeded maximum iterations ({max_iter})")

    async def process_with_tools_async(
        self,
        messages: list[MessageParam],
        tools: list[ToolDefinition],
        tool_executor: Callable[[str, dict[str, Any]], Any],
        system: str | None = None,
        max_iterations: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, list[MessageParam]]:
        """Process a conversation with tool execution loop (async).

        This method handles the complete tool use pattern asynchronously:
        1. Send messages to Claude
        2. If Claude requests tool use, execute the tools
        3. Send tool results back to Claude
        4. Repeat until Claude responds with text only

        Args:
            messages: Initial conversation messages.
            tools: Tool definitions.
            tool_executor: Function to execute tools. Can be sync or async.
            system: System prompt.
            max_iterations: Maximum tool use iterations. Defaults to MAX_TOOL_ITERATIONS.
            **kwargs: Additional arguments passed to the API.

        Returns:
            Tuple of (final_text_response, full_conversation_history).

        Raises:
            RuntimeError: If max iterations exceeded.
        """
        max_iter = max_iterations or self.MAX_TOOL_ITERATIONS
        conversation: list[MessageParam] = list(messages)

        for _ in range(max_iter):
            response = await self.create_message_async(
                messages=conversation,
                system=system,
                tools=tools,
                **kwargs,
            )

            # Add assistant response to conversation
            conversation.append({"role": "assistant", "content": response.content})

            # Check if we need to execute tools
            tool_uses = self._extract_tool_uses(response)

            if not tool_uses:
                # No more tool calls, return the final text
                return self._extract_text(response), conversation

            # Execute tools and add results to conversation
            tool_results = await self._build_tool_results_async(tool_uses, tool_executor)
            conversation.append({"role": "user", "content": tool_results})

        raise RuntimeError(f"Tool execution exceeded maximum iterations ({max_iter})")

    def simple_chat(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Simple single-turn chat without tools.

        Args:
            prompt: User prompt.
            system: System prompt.
            **kwargs: Additional arguments passed to the API.

        Returns:
            Claude's text response.
        """
        response = self.create_message(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            **kwargs,
        )
        return self._extract_text(response)

    async def simple_chat_async(
        self,
        prompt: str,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Simple single-turn chat without tools (async).

        Args:
            prompt: User prompt.
            system: System prompt.
            **kwargs: Additional arguments passed to the API.

        Returns:
            Claude's text response.
        """
        response = await self.create_message_async(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            **kwargs,
        )
        return self._extract_text(response)
