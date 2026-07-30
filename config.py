"""
Centralized configuration.

All settings are loaded from environment variables.
Copy .env.example → .env and fill in your values.
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Application configuration.

    Usage:
        from config import config
        print(config.deepgram_api_key)
    """
    # ─── Twilio ───
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # ─── Deepgram (STT) ───
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")

    # ─── AWS Bedrock (LLM) ───
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID",
        "anthropic.claude-3-haiku-20240307-v1:0",
    )

    # ─── Cartesia (TTS) ───
    cartesia_api_key: str = os.getenv("CARTESIA_API_KEY", "")
    cartesia_voice_id: str = os.getenv("CARTESIA_VOICE_ID", "")

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

    # ─── Available Bedrock Models ───
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

        if not self.twilio_account_sid:
            missing.append("TWILIO_ACCOUNT_SID")
        if not self.twilio_auth_token:
            missing.append("TWILIO_AUTH_TOKEN")
        if not self.twilio_phone_number:
            missing.append("TWILIO_PHONE_NUMBER")
        if not self.deepgram_api_key:
            missing.append("DEEPGRAM_API_KEY")
        if not self.aws_access_key_id:
            missing.append("AWS_ACCESS_KEY_ID")
        if not self.aws_secret_access_key:
            missing.append("AWS_SECRET_ACCESS_KEY")
        if not self.cartesia_api_key:
            missing.append("CARTESIA_API_KEY")
        if not self.cartesia_voice_id:
            missing.append("CARTESIA_VOICE_ID")

        return missing

    def is_valid(self) -> bool:
        """Check if all required configuration is present."""
        return len(self.validate()) == 0


# Singleton instance
config = Config()