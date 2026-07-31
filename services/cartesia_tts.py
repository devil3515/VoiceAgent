"""
Cartesia Sonic TTS Service.

Uses Cartesia's Sonic model for ultra-low-latency text-to-speech.
First-byte latency: ~50ms

Features:
- Natural-sounding voices
- Ultra-low latency
- Streaming support (SSE)
- Multiple output formats
"""

from asyncio import base_events
import time
from typing import Optional

import httpx
from utils.logging import get_logger

logger=get_logger(__name__)


class CartesiaTTSService:
    """
    Text-to-Speech using Cartesia Sonic.

    Usage:
        tts = CartesiaTTSService(api_key="...", voice_id="...")
        audio_bytes = await tts.synthesize("Hello, world!")
    """

    # Cartesia API base URL
    BASE_URL = "https://api.cartesia.ai"

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model_id: str = "sonic-2",
        sample_rate: int = 16000,
        encoding: str = "pcm_s16le",
    ):
        """
        Initialize Cartesia TTS service.

        Args:
            api_key: Cartesia API key
            voice_id: Voice ID to use (get from Cartesia playground)
            model_id: Model ID (default: sonic-english)
            sample_rate: Output sample rate (default: 16000)
            encoding: Output encoding (default: pcm_s16le = linear16)
        """
        self.api_key=api_key
        self.voice_id=voice_id
        self.model_id=model_id
        self.sample_rate=sample_rate
        self.encoding=encoding

        logger.info(
            "tts_initialized",
            model_id=model_id,
            voice_id=voice_id,
            sample_rate=sample_rate,
            encoding=encoding,
        )

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        sample_rate: Optional[int] = None,
    ) -> bytes:
        """
        Synthesize speech from text.

        Args:
            text: Text to convert to speech
            voice_id: Override default voice ID
            sample_rate: Override default sample rate

        Returns:
            Raw audio bytes (16kHz linear16 PCM by default)

        Raises:
            httpx.HTTPStatusError: If API call fails
        """
        start=time.time()
        voice_id=voice_id or self.voice_id
        sample_rate=sample_rate or self.sample_rate

        logger.debug("tts_synthesize_start", text_length=len(text))

        url = f"{self.BASE_URL}/tts/bytes"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Cartesia-Version": "2024-06-10",
        }
        payload = {
            "model_id": self.model_id,
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": voice_id,
            },
            "output_format": {
                "container": "raw",
                "encoding": self.encoding,
                "sample_rate": sample_rate,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.is_error:
                logger.error("cartesia_http_error", status_code=response.status_code, body=response.text)
            response.raise_for_status()
            audio_data = response.content

        latency_ms = (time.time() - start) * 1000
        duration_ms = len(audio_data) / (sample_rate * 2) * 1000  # 2 bytes per sample
        logger.info(
            "tts_synthesize_complete",
            latency_ms=round(latency_ms, 1),
            audio_bytes=len(audio_data),
            audio_duration_ms=round(duration_ms, 1),
        )

        return audio_data

    async def synthesize_stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        sample_rate: Optional[int] = None,
    ):
        """
        Stream speech synthesis via SSE.

        Yields audio chunks as they're generated.
        Useful for Phase 5 optimization (lower first-byte latency).

        Args:
            Same as synthesize()

        Yields:
            Audio chunks (bytes) as they arrive
        """
        start = time.time()
        voice_id = voice_id or self.voice_id
        sample_rate = sample_rate or self.sample_rate

        url = f"{self.BASE_URL}/tts/sse"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Cartesia-Version": "2024-06-10",
        }
        payload = {
            "model_id": self.model_id,
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": voice_id,
            },
            "output_format": {
                "container": "raw",
                "encoding": self.encoding,
                "sample_rate": sample_rate,
            },
        }

        total_bytes = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        import json
                        data = json.loads(line[5:].strip())
                        if "audio" in data:
                            import base64
                            audio_chunk = base64.b64decode(data["audio"])
                            total_bytes += len(audio_chunk)
                            yield audio_chunk

        latency_ms = (time.time() - start) * 1000
        logger.info(
            "tts_stream_complete",
            latency_ms=round(latency_ms, 1),
            total_bytes=total_bytes,
        )
