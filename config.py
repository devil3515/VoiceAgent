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

    # ─── SignalWire ───
    signalwire_project_id: str = os.getenv("SIGNALWIRE_PROJECT_ID", "")
    signalwire_api_token: str = os.getenv("SIGNALWIRE_API_TOKEN", "")
    signalwire_space_url: str = os.getenv("SIGNALWIRE_SPACE_URL", "")
    signalwire_phone_number: str = os.getenv("SIGNALWIRE_PHONE_NUMBER", "")

    # Legacy alias fallback support
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "") or os.getenv("SIGNALWIRE_PROJECT_ID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "") or os.getenv("SIGNALWIRE_API_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "") or os.getenv("SIGNALWIRE_PHONE_NUMBER", "")

    # ─── Deepgram (STT) ───
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")

    # ─── Bedrock Mantle (LLM) — OpenAI-compatible ───
    bedrock_base_url: str = os.getenv("BEDROCK_BASE_URL", "")
    bedrock_api_key: str = os.getenv("BEDROCK_API_KEY", "")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID",
        "anthropic.claude-3-haiku-20240307-v1:0",
    )

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

    def get_signalwire_client(self):
        """Construct a SignalWire REST Client instance."""
        from signalwire.rest import Client as SignalWireClient
        return SignalWireClient(
            self.signalwire_project_id,
            self.signalwire_api_token,
            signalwire_space_url=self.signalwire_space_url,
        )

    def get_twilio_client(self):
        """Compatibility wrapper for SignalWire Client."""
        return self.get_signalwire_client()

    # ─── Available Models (via Bedrock Mantle) ───
    AVAILABLE_MODELS = {
        "haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "llama-70b": "meta.llama3-1-70b-instruct-v1:0",
        "llama-8b": "meta.llama3-1-8b-instruct-v1:0",
        "mistral": "mistral.mistral-large-2407-v1:0",
    }

    def validate(self) -> list[str]:
        """Validate configuration and return list of missing keys."""
        missing = []

        if not self.signalwire_project_id:
            missing.append("SIGNALWIRE_PROJECT_ID")
        if not self.signalwire_api_token:
            missing.append("SIGNALWIRE_API_TOKEN")
        if not self.signalwire_space_url:
            missing.append("SIGNALWIRE_SPACE_URL")
        if not self.signalwire_phone_number:
            missing.append("SIGNALWIRE_PHONE_NUMBER")
        if not self.deepgram_api_key:
            missing.append("DEEPGRAM_API_KEY")
        if not self.bedrock_base_url:
            missing.append("BEDROCK_BASE_URL")
        if not self.bedrock_api_key:
            missing.append("BEDROCK_API_KEY")
        if not self.cartesia_api_key:
            missing.append("CARTESIA_API_KEY")
        if not self.cartesia_voice_id:
            missing.append("CARTESIA_VOICE_ID")

        return missing

    def is_valid(self) -> bool:
        """Check if all required configuration is present."""
        return len(self.validate()) == 0


config = Config()