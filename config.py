"""
Centralized configuration.

All settings are loaded from environment variables.
Copy .env.example → .env and fill in your values.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # ─── Deepgram (STT) ───
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")

    # ─── LLM (OpenAI-compatible endpoint) ───
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model_id: str = os.getenv("LLM_MODEL_ID", "anthropic/claude-3-haiku")

    # ─── Cartesia (TTS) ───
    cartesia_api_key: str = os.getenv("CARTESIA_API_KEY", "")
    cartesia_voice_id: str = os.getenv("CARTESIA_VOICE_ID", "")

    # ─── Redis ───
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ─── Server ───
    server_host: str = os.getenv("SERVER_HOST", "localhost:8000")
    port: int = int(os.getenv("PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # ─── Agent ───
    max_conversation_history: int = 20
    llm_max_tokens: int = 150
    llm_temperature: float = 0.7
    stt_endpointing_ms: int = 500
    greeting_text: str = "Hello! Thanks for calling Acme Corp. How can I help you today?"
    max_tool_calls_per_turn: int = int(os.getenv("MAX_TOOL_CALLS_PER_TURN", "5"))
    knowledge_base_path: str = os.getenv("KNOWLEDGE_BASE_PATH", "./knowledge.json")

    # ─── Available Models (OpenAI-compatible) ───
    AVAILABLE_MODELS = {
        "haiku": "anthropic/claude-3-haiku",
        "sonnet": "anthropic/claude-3.5-sonnet",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "llama-70b": "meta-llama/llama-3.1-70b-instruct",
        "llama-8b": "meta-llama/llama-3.1-8b-instruct",
        "mistral": "mistralai/mistral-large",
    }

    def validate(self) -> list[str]:
        """Validate configuration and return list of missing keys."""
        missing = []

        if not self.deepgram_api_key:
            missing.append("DEEPGRAM_API_KEY")
        if not self.llm_base_url:
            missing.append("LLM_BASE_URL")
        if not self.llm_api_key:
            missing.append("LLM_API_KEY")
        if not self.cartesia_api_key:
            missing.append("CARTESIA_API_KEY")
        if not self.cartesia_voice_id:
            missing.append("CARTESIA_VOICE_ID")

        return missing

    def is_valid(self) -> bool:
        """Check if all required configuration is present."""
        return len(self.validate()) == 0


config = Config()