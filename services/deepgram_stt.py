"""
Deepgram Streaming Speech-to-Text Service.

Uses Deepgram's Nova-2 model for real-time transcription
via WebSocket connection.

Features:
- Real-time streaming transcription
- Interim results (partial transcripts while speaking)
- Endpointing detection (knows when user stops speaking)
- Smart formatting (auto-punctuation, capitalization)
"""

import asyncio
from typing import Optional,Callable
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
from utils.logging import get_logger

logger=get_logger(__name__)

class DeepgramSTTService:
    """
    Streaming Speech-to-Text using Deepgram.

    Usage:
        stt = DeepgramSTTService(api_key="...")
        await stt.connect(on_transcript=my_handler)
        await stt.send_audio(audio_bytes)
        await stt.disconnect()
    """
    def __init__(self, api_key: str, model: str = "nova-2", language: str="en"):
        """
        Initialize Deepgram STT service.

        Args:
            api_key: Deepgram API key
            model: Model name (default: nova-2)
            language: Language code (default: en)
        """
        self.api_key = api_key
        self.model = model
        self.language = language
        self.dg_client = DeepgramClient(api_key=api_key)
        self.dg_connection = None
        self._on_transcript_callback = None
        self._is_connected = False
        self._connection = None
        # Cached VAD state — used by the "are you there?" check-in to know
        # whether speech has actually arrived (vs. an empty transport).
        self.speech_started_at: Optional[float] = None
        self.last_speech_event: Optional[str] = None

    # ─────────────────────────────────────────────
    # CONNECTION LIFECYCLE
    # ─────────────────────────────────────────────

    async def connect(
         self,
        on_transcript: Callable,
        on_error: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        endpointing_ms: int = 500,
        sample_rate: int = 16000,
    ) -> bool:
        """
        Open a streaming connection to Deepgram.

        Args:
            on_transcript: Callback for transcript results.
                           Signature: async def on_transcript(result, **kwargs)
            on_error: Callback for errors
            on_close: Callback when connection closes
            endpointing_ms: Ms of silence before considering speech final (default: 500)
            sample_rate: Audio sample rate (default: 16000)

        Returns:
            True if connection succeeded, False otherwise
        """
        logger.info("stt_connecting", model=self.model, language=self.language)

        self._connection = self.dg_client.listen.asynclive.v("1")

        # Register event handlers
        self._connection.on(
            LiveTranscriptionEvents.Transcript,
            self._wrap_transcript_handler(on_transcript),
        )
        self._connection.on(
            LiveTranscriptionEvents.Error,
            self._wrap_error_handler(on_error),
        )
        self._connection.on(
            LiveTranscriptionEvents.Close,
            self._wrap_close_handler(on_close),
        )
        # VAD events: let us know whether speech is being detected on the wire.
        # These are pure diagnostics, but they're the only way to discriminate
        # "browser sent silence" from "Deepgram isn't transcribing".
        self._connection.on(
            LiveTranscriptionEvents.SpeechStarted,
            self._wrap_speech_started_handler(),
        )
        self._connection.on(
            LiveTranscriptionEvents.UtteranceEnd,
            self._wrap_utterance_end_handler(),
        )

        # Configure transcription options
        options = LiveOptions(
            model=self.model,
            language=self.language,
            smart_format=True,
            encoding="linear16",
            channels=1,
            sample_rate=sample_rate,
            interim_results=True,
            endpointing=endpointing_ms,
            vad_events=True,
        )
        self._is_connected = await self._connection.start(options)

        if self._is_connected:
            logger.info("stt_connected")
        else:
            logger.error("stt_connection_failed")

        return self._is_connected

    async def send_audio(self, audio_bytes: bytes) -> bool:
        """
        Send audio data to Deepgram for transcription.

        Args:
            audio_bytes: 16kHz linear16 PCM audio bytes

        Returns:
            True if sent successfully
        """
        if not self._is_connected or not self._connection:
            logger.warning("stt_send_not_connected")
            return False

        try:
            return await self._connection.send(audio_bytes)
        except Exception as e:
            logger.error("stt_send_error", error=str(e))
            return False


    async def disconnect(self):
        """Close the Deepgram connection."""
        if self._connection and self._is_connected:
            try:
                await self._connection.finish()
                logger.info("stt_disconnected")
            except Exception as e:
                logger.error("stt_disconnect_error", error=str(e))
            finally:
                self._is_connected = False
                self._connection = None


    @property
    def is_connected(self) -> bool:
        """Check if the STT connection is active."""
        return self._is_connected

    # ─────────────────────────────────────────────
    # CALLBACK WRAPPERS
    # ─────────────────────────────────────────────

    def _wrap_transcript_handler(self, callback: Callable) -> Callable:
        """Wrap the user's transcript callback with logging."""
        async def handler(*args, **kwargs):
            try:
                result = kwargs.get("result") if "result" in kwargs else (args[1] if len(args) > 1 else (args[0] if args else None))
                # Log every Transcript event the SDK emits, even when the
                # transcript text is empty — that tells us whether the SDK is
                # actually dispatching these events at all.
                if result is not None:
                    try:
                        channel = result.channel
                        alternatives = channel.alternatives if channel else []
                        transcript = (
                            alternatives[0].transcript if alternatives else ""
                        )
                        is_final = getattr(result, "is_final", False)
                        speech_final = getattr(result, "speech_final", False)
                    except Exception:
                        transcript, is_final, speech_final = "<extract-error>", False, False
                    logger.info(
                        "stt_transcript_event",
                        transcript=transcript,
                        is_final=is_final,
                        speech_final=speech_final,
                    )

                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error("stt_callback_error", error=str(e))

        return handler

    def _wrap_speech_started_handler(self) -> Callable:
        """VAD SpeechStarted — Deepgram heard the start of speech on the wire."""
        import time as _t

        async def handler(*args, **kwargs):
            try:
                self.speech_started_at = _t.time()
                self.last_speech_event = "speech_started"
                logger.info("stt_speech_started")
            except Exception as e:
                logger.error("stt_speech_started_handler_error", error=str(e))

        return handler

    def _wrap_utterance_end_handler(self) -> Callable:
        """VAD UtteranceEnd — Deepgram closed the utterance window."""
        import time as _t

        async def handler(*args, **kwargs):
            try:
                self.last_speech_event = "utterance_end"
                logger.info("stt_utterance_end")
            except Exception as e:
                logger.error("stt_utterance_end_handler_error", error=str(e))

        return handler

    def _wrap_error_handler(self, callback: Optional[Callable]) -> Callable:
        """Wrap the user's error callback with logging."""
        async def handler(*args, **kwargs):
            error = kwargs.get("error") if "error" in kwargs else (args[1] if len(args) > 1 else (args[0] if args else None))
            logger.error("stt_error", error=str(error))
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error)
                else:
                    callback(error)

        return handler

    def _wrap_close_handler(self, callback: Optional[Callable]) -> Callable:
        """Wrap the user's close callback with logging."""
        async def handler(*args, **kwargs):
            close = kwargs.get("close") if "close" in kwargs else (args[1] if len(args) > 1 else (args[0] if args else None))
            logger.info("stt_connection_closed")
            self._is_connected = False
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(close)
                else:
                    callback(close)

        return handler