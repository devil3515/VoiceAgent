"""
Conversation history management.

Handles:
- Storing conversation messages
- Trimming to keep context window manageable
- Converting between different LLM formats
- Extracting conversation metadata
"""

from typing import Optional

from utils.logging import get_logger

logger=get_logger(__name__)


class ConversationManager:
    """
    Manages conversation history for a single call.

    Usage:
        conv = ConversationManager(system_prompt="...")
        conv.add_user_message("Hello!")
        conv.add_assistant_message("Hi there!")
        system, messages = conv.to_bedrock_format()
    """

    def __init__(self, system_prompt: str, max_history: int=20,):
        """
        Initialize conversation manager.

        Args:
            system_prompt: The system prompt for the agent
            max_history: Maximum number of conversation turns to keep
        """
        self.system_prompt=system_prompt
        self.max_history=max_history
        self._messages: list[dict] = []

    # ─────────────────────────────────────────────
    # ADD MESSAGES
    # ─────────────────────────────────────────────

    def add_user_message(self, text: str):
        """Add a user message to the conversation."""
        self._messages.append({"role": "user", "content": text})
        self._trim()
        logger.debug("conversation_user_message", text_length=len(text))

    def add_assistant_message(self, text: str):
        """Add an assistant message to the conversation."""
        self._messages.append({"role": "assistant", "content": text})
        self._trim()
        logger.debug("conversation_assistant_message", text_length=len(text))

    # ─────────────────────────────────────────────
    # FORMATS
    # ─────────────────────────────────────────────

    def to_bedrock_format(self) -> tuple[list[dict], list[dict]]:
        """
        Convert conversation to Bedrock Converse API format.

        Returns:
            Tuple of (system, messages)
            system: [{"text": "system prompt"}]
            messages: [{"role": "user/assistant", "content": [{"text": "..."}]}]
        """
        system = [{"text": self.system_prompt}]

        messages = []
        for msg in self._messages:
            messages.append({
                "role": msg["role"],
                "content": [{"text": msg["content"]}],
            })

        return system, messages

    def to_openai_format(self) -> list[dict]:
        """
        Convert conversation to OpenAI Chat API format.

        Returns:
            List of messages including system prompt
            [{"role": "system", "content": "..."}, ...]
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        for msg in self._messages:
            messages.append(msg)
        return messages

    def get_messages(self) -> list[dict]:
        """Get all messages in OpenAI format (including system prompt)."""
        return self.to_openai_format()


    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────

    def _trim(self):
        """Trim conversation history to max_history messages."""
        if len(self._messages) > self.max_history:
            self._messages = self._messages[-self.max_history:]
            logger.debug(
                "conversation_trimmed",
                remaining=len(self._messages),
                max=self.max_history,
            )

    @property
    def message_count(self) -> int:
        """Number of messages in conversation (excluding system prompt)."""
        return len(self._messages)

    @property
    def last_user_message(self) -> Optional[str]:
        """Get the last user message, or None."""
        for msg in reversed(self._messages):
            if msg["role"] == "user":
                return msg["content"]
        return None

    @property
    def last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message, or None."""
        for msg in reversed(self._messages):
            if msg["role"] == "assistant":
                return msg["content"]
        return None

    def get_transcript(self) -> str:
        """Get a formatted transcript of the conversation."""
        lines = []
        for msg in self._messages:
            role = "User" if msg["role"] == "user" else "Agent"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def clear(self):
        """Clear all messages (keep system prompt)."""
        self._messages = []