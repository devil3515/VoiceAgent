"""
Voice Agent — orchestrates the full call pipeline.

STT (Deepgram) → LLM (Bedrock) → TTS (Cartesia)

Handles:
- Twilio WebSocket audio stream
- Real-time speech recognition
- LLM response generation
- TTS audio playback
- Turn management (who's speaking)
- Conversation state
"""

import asyncio
import json
import time
from typing import Optional

from services.deepgram_stt import DeepgramSTTService
from services.bedrock_llm import BedrockLLMService
from services.cartesia_tts import CartesiaTTSService
from services.audio_utils import (
    twilio_to_deepgram,
    linear16_to_mulaw,
    chunk_audio,
    encode_twilio_payload,
)
from agents.prompts import SYSTEM_PROMPT,GREETING_TEXT
from agents.conversation import ConversationManager
from utils.logging import get_logger

from config import config

logger=get_logger(__name__)


class VoiceAgent:
    """
    Handles a single voice call from start to finish.

    Lifecycle:
        1. Twilio opens WebSocket → agent.run()
        2. Agent connects STT, sends greeting
        3. Loop: receive audio → transcribe → generate → speak
        4. Twilio closes WebSocket → agent cleans up

    Usage:
        agent = VoiceAgent(twilio_websocket)
        await agent.run()
    """

    def __init__(self, twilio_ws):
        """
        Initialize voice agent for a call.

        Args:
            twilio_ws: FastAPI WebSocket connection to Twilio
        """
        # Twilio WebSocket
        self.twilio_ws=twilio_ws

        # Call metadata (set when 'start' event arrives)
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None

        # Services (initialized in run())
        self.stt: Optional[DeepgramSTTService] = None
        self.llm: Optional[BedrockLLMService] = None
        self.tts: Optional[CartesiaTTSService] = None

        # Conversation
        self.conversation = ConversationManager(
            system_prompt=SYSTEM_PROMPT,
            max_history=config.max_conversation_history,
        )

        #State
        self.current_transcript=""
        self.is_processing=False
        self.is_agent_speaking=False
        self.turn_count=0
        self.call_start_time: Optional[float]=None

    # ─────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────

    async def run(self):
        """
        Main entry point. Handles the full call lifecycle.

        1. Initialize services
        2. Connect STT
        3. Send greeting
        4. Process Twilio audio stream
        5. Clean up when call ends
        """
        logger.info("agent_call_starting")
        self.call_start_time = time.time()

        try:
            # Step 1: Initialize services
            self._init_services()

            # Step 2: Connect STT
            connected = await self.stt.connect(
                on_transcript=self._on_transcript,
                on_error=self._on_stt_error,
                on_close=self._on_stt_close,
                endpointing_ms=config.stt_endpointing_ms,
            )
            if not connected:
                logger.error("agent_stt_connection_failed")
                return

            # Step 3: Send greeting
            await self._send_greeting()

            # Step 4: Process Twilio audio stream
            async for raw_message in self.twilio_ws.iter_text():
                try:
                    data = json.loads(raw_message)
                    await self._handle_twilio_event(data)
                except json.JSONDecodeError:
                    logger.warning("agent_invalid_json")
                except Exception as e:
                    logger.error("agent_message_error", error=str(e))

        except Exception as e:
            logger.error("agent_call_error", error=str(e), error_type=type(e).__name__)
        finally:
            await self._cleanup()

    # ─────────────────────────────────────────────
    # SERVICE INITIALIZATION
    # ─────────────────────────────────────────────

    def _init_services(self):
        """Initialize all pipeline services."""
        self.stt = DeepgramSTTService(
            api_key=config.deepgram_api_key,
        )

        # ─── Bedrock Mantle (OpenAI-compatible) ───
        self.llm = BedrockLLMService(
            base_url=config.bedrock_base_url,
            api_key=config.bedrock_api_key,
            model_id=config.bedrock_model_id,
            max_tokens=config.llm_max_tokens,
            temperature=config.llm_temperature,
        )

        self.tts = CartesiaTTSService(
            api_key=config.cartesia_api_key,
            voice_id=config.cartesia_voice_id,
        )

        logger.info(
            "agent_services_initialized",
            stt="deepgram",
            llm="bedrock_mantle",
            tts="cartesia",
            model=config.bedrock_model_id,
        )

    # ─────────────────────────────────────────────
    # TWILIO EVENT HANDLING
    # ─────────────────────────────────────────────

    async def _handle_twilio_event(self, data: dict):
        """Route incoming Twilio WebSocket events."""
        event = data.get("event")

        if event == "connected":
            logger.info("agent_twilio_connected")

        elif event == "start":
            self.stream_sid = data["start"]["streamSid"]
            self.call_sid = data["start"].get("callSid", "unknown")
            logger.info("agent_call_started", call_sid=self.call_sid)

        elif event == "media":
            payload = data["media"]["payload"]
            await self._process_incoming_audio(payload)

        elif event == "stop":
            logger.info("agent_call_stopped", call_sid=self.call_sid)

    async def _process_incoming_audio(self, base64_mulaw: str):
        """Convert Twilio audio and send to Deepgram."""
        try:
            pcm_16k = twilio_to_deepgram(base64_mulaw)
            if self.stt and self.stt.is_connected:
                await self.stt.send_audio(pcm_16k)
        except Exception as e:
            logger.error("agent_audio_processing_error", error=str(e))


    # ─────────────────────────────────────────────
    # STT CALLBACKS
    # ─────────────────────────────────────────────
    async def _on_transcript(self, result, **kwargs):
        """Handle Deepgram transcription results."""
        try:
            transcript = result.channel.alternatives[0].transcript
            if not transcript:
                return

            if result.is_final:
                self.current_transcript += transcript + " "

            if result.speech_final and self.current_transcript.strip():
                user_text = self.current_transcript.strip()
                self.current_transcript = ""

                if not self.is_processing:
                    asyncio.create_task(self._process_turn(user_text))
                else:
                    logger.warning(
                        "agent_skipping_turn",
                        reason="still_processing",
                        text=user_text[:50],
                    )

        except Exception as e:
            logger.error("agent_transcript_error", error=str(e))

    async def _on_stt_error(self, error, **kwargs):
        logger.error("agent_stt_error", error=str(error))

    async def _on_stt_close(self, close, **kwargs):
        logger.info("agent_stt_closed")

    # ─────────────────────────────────────────────
    # FULL TURN PROCESSING
    # ─────────────────────────────────────────────
    async def _process_turn(self, user_text: str):
        """
        Process a complete user utterance:
        1. Add to conversation
        2. Get LLM response (OpenAI format → Bedrock Mantle)
        3. Add response to conversation
        4. Generate TTS and send to Twilio
        """
        self.is_processing = True
        self.turn_count += 1
        turn_start = time.time()

        logger.info(
            "agent_turn_start",
            turn=self.turn_count,
            user_text=user_text,
        )

        try:
            # Step 1: Add user message
            self.conversation.add_user_message(user_text)

            # Step 2: Get LLM response
            #         get_messages() returns OpenAI format — directly usable
            messages = self.conversation.get_messages()
            agent_text = await self.llm.generate(messages)

            # Step 3: Add assistant message
            self.conversation.add_assistant_message(agent_text)

            # Step 4: Generate TTS
            audio_data = await self.tts.synthesize(agent_text)

            # Step 5: Send audio to Twilio
            await self._send_audio_to_twilio(audio_data)

            total_latency = (time.time() - turn_start) * 1000

            logger.info(
                "agent_turn_complete",
                turn=self.turn_count,
                user_text=user_text,
                agent_text=agent_text,
                total_latency_ms=round(total_latency, 1),
            )

        except Exception as e:
            logger.error(
                "agent_turn_error",
                turn=self.turn_count,
                error=str(e),
                error_type=type(e).__name__,
            )
        finally:
            self.is_processing = False

    # ─────────────────────────────────────────────
    # SEND AUDIO TO TWILIO
    # ─────────────────────────────────────────────

    async def _send_audio_to_twilio(self, pcm_16k: bytes):
        """Convert PCM audio to Twilio format and send in chunks."""
        mulaw_audio = linear16_to_mulaw(pcm_16k)
        chunks = chunk_audio(mulaw_audio, chunk_size=800)

        self.is_agent_speaking = True

        for chunk in chunks:
            if not self.is_agent_speaking:
                break

            payload = encode_twilio_payload(chunk)

            message = {
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": payload},
            }

            try:
                await self.twilio_ws.send_text(json.dumps(message))
            except Exception as e:
                logger.error("agent_audio_send_error", error=str(e))
                break

            await asyncio.sleep(0.02)

        self.is_agent_speaking = False

    # ─────────────────────────────────────────────
    # GREETING
    # ─────────────────────────────────────────────

    async def _send_greeting(self):
        """Send an initial greeting when the call starts."""
        logger.info("agent_sending_greeting", greeting=GREETING_TEXT)

        try:
            audio_data = await self.tts.synthesize(GREETING_TEXT)
            await self._send_audio_to_twilio(audio_data)
        except Exception as e:
            logger.error("agent_greeting_error", error=str(e))


    # ─────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────

    async def _cleanup(self):
        """Clean up resources when the call ends."""
        if self.call_start_time:
            duration = time.time() - self.call_start_time
            logger.info(
                "agent_call_ended",
                call_sid=self.call_sid,
                duration_seconds=round(duration, 1),
                total_turns=self.turn_count,
                total_messages=self.conversation.message_count,
            )

        if self.stt:
            await self.stt.disconnect()

        self.is_agent_speaking = False
        self.is_processing = False
