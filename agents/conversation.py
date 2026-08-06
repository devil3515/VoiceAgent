"""
Conversation history management.

Updated to support tool messages for OpenAI function calling.
"""

import json
from typing import Optional

from utils.logging import get_logger

logger = get_logger(__name__)


class ConversationManager:
    """
    Manages conversation history for a single call.
    
    Supports all OpenAI message types:
    - system: System prompt
    - user: User messages
    - assistant: Agent responses (with optional tool_calls)
    - tool: Tool execution results
    """

    def __init__(self, system_prompt: str, max_history: int = 20):
        self.system_prompt = system_prompt
        self.max_history = max_history
        self._messages: list[dict] = []

    # ─────────────────────────────────────────────
    # ADD MESSAGES
    # ─────────────────────────────────────────────

    def add_user_message(self, text: str):
        """Add a user message."""
        self._messages.append({"role": "user", "content": text})
        self._trim()
        logger.debug("conversation_user_message", text_length=len(text))

    def add_assistant_message(self, text: str):
        """Add an assistant text message."""
        self._messages.append({"role": "assistant", "content": text})
        self._trim()
        logger.debug("conversation_assistant_message", text_length=len(text))

    def add_assistant_tool_calls(self, tool_calls: list[dict]):
        """
        Add an assistant message with tool calls.
        
        Args:
            tool_calls: List of tool call dicts from LLM:
                [{"id": "call_123", "name": "lookup_pricing", "arguments": {...}}, ...]
        """
        openai_tool_calls = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"]),
                },
            }
            for tc in tool_calls
        ]

        self._messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": openai_tool_calls,
        })
        self._trim()
        logger.debug("conversation_assistant_tool_calls", num_calls=len(tool_calls))

    def add_tool_result(self, tool_call_id: str, result: str):
        """
        Add a tool execution result.
        
        Args:
            tool_call_id: The ID of the tool call this result is for
            result: The tool execution result
        """
        self._messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })
        logger.debug("conversation_tool_result", tool_call_id=tool_call_id, result_length=len(result))

    # ─────────────────────────────────────────────
    # GET MESSAGES (OpenAI format)
    # ─────────────────────────────────────────────

    def get_messages(self) -> list[dict]:
        """
        Get all messages in OpenAI format (including system prompt).
        Ready to pass directly to the LLM.
        """
        system = [{"role": "system", "content": self.system_prompt}]
        return system + self._messages

    def to_bedrock_format(self) -> tuple[list[dict], list[dict]]:
        """Convert to native Bedrock Converse API format (if needed)."""
        system = [{"text": self.system_prompt}]
        messages = []
        for msg in self._messages:
            if msg["role"] == "tool":
                continue  # Skip tool messages for Bedrock format
            messages.append({
                "role": msg["role"],
                "content": [{"text": msg.get("content", "")}],
            })
        return system, messages

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────

    def _trim(self):
        """Trim conversation history to max_history messages."""
        # Keep system prompt + max_history messages
        # Never trim tool messages that are part of a tool call pair
        if len(self._messages) > self.max_history:
            # Find a safe trim point (don't cut in the middle of a tool call sequence)
            self._messages = self._messages[-self.max_history:]
            logger.debug(
                "conversation_trimmed",
                remaining=len(self._messages),
            )

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def last_user_message(self) -> Optional[str]:
        for msg in reversed(self._messages):
            if msg["role"] == "user":
                return msg["content"]
        return None

    @property
    def last_assistant_message(self) -> Optional[str]:
        for msg in reversed(self._messages):
            if msg["role"] == "assistant" and msg.get("content"):
                return msg["content"]
        return None

    def get_transcript(self) -> str:
        """Get a formatted transcript of the conversation."""
        lines = []
        for msg in self._messages:
            if msg["role"] == "user":
                lines.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant" and msg.get("content"):
                lines.append(f"Agent: {msg['content']}")
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                tool_names = [tc["function"]["name"] for tc in msg["tool_calls"]]
                lines.append(f"Agent [called tools: {', '.join(tool_names)}]")
            elif msg["role"] == "tool":
                lines.append(f"Tool result: {msg['content'][:100]}...")
        return "\n".join(lines)

    def clear(self):
        self._messages = []