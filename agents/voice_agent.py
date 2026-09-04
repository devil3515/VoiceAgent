"""
Voice Agent — orchestrates the full call pipeline with tools.

STT (Deepgram) → LLM (OpenAI-compatible) → [Tool Execution] → TTS (Cartesia)

The audio I/O is provided by an ``AudioTransport`` so the agent is agnostic to the
carrier: it works equally over a phone carrier (Twilio/SignalWire) or, in local
mode, directly over a browser WebSocket streaming 16 kHz linear16 PCM.

Key Phase 2 additions:
- Tool execution loop (LLM can call tools, get results, continue)
- Session state management
- Knowledge base integration
- Local browser voice mode (no carrier required)
"""

import asyncio
import time
from typing import Optional

from services.deepgram_stt import DeepgramSTTService
from services.llm import LLMService
from services.cartesia_tts import CartesiaTTSService
from services.audio_transport import AudioTransport
from agents.prompts import SYSTEM_PROMPT, GREETING_TEXT, CLARIFICATION_TEXTS
from agents.conversation import ConversationManager
from agents.tools import execute_tool, get_tool_definitions
from memory.session import SessionManager
from config import config
from utils.logging import get_logger

logger = get_logger(__name__)


class VoiceAgent:
    """
    Handles a single voice call with tool support.

    Lifecycle:
        1. A transport (browser WebSocket / carrier) opens → agent.run()
        2. Agent connects STT, sends greeting
        3. Loop: receive audio → transcribe → LLM (with tools) → speak
        4. Tool execution loop if LLM requests tools
        5. Transport closes → agent cleans up
    """

    def __init__(self, transport: AudioTransport, session_id: Optional[str] = None):
        self.transport = transport
        self.session_id: Optional[str] = session_id
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = session_id

        # Services
        self.stt: Optional[DeepgramSTTService] = None
        self.llm: Optional[LLMService] = None
        self.tts: Optional[CartesiaTTSService] = None

        # Conversation & Session
        self.conversation = ConversationManager(
            system_prompt=SYSTEM_PROMPT,
            max_history=config.max_conversation_history,
        )
        self.session: Optional[SessionManager] = None

        # State
        self.current_transcript = ""
        # Deepgram can finalize an utterance with an EMPTY transcript even when
        # interim results carried real text (e.g. "Yeah."). Keep the best interim
        # per utterance so we can recover it when the final comes back empty.
        self._last_interim_text = ""
        self.is_processing = False
        self.is_agent_speaking = False
        self.turn_count = 0
        self.call_start_time: Optional[float] = None
        self.tool_definitions = get_tool_definitions()
        # "Are you there?" check-in: when the user has been silent for a while,
        # we prompt once so a quiet caller (or a silent browser) gets a chance
        # to react. We fire at most one check-in per call so it can't loop.
        self._checkin_sent = False
        self._checkin_task: Optional[asyncio.Task] = None

    # ─────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────

    async def run(self):
        """Main entry point. Handles the full call lifecycle."""
        logger.info("agent_call_starting")
        self.call_start_time = time.time()

        try:
            self._init_services()

            # Initialize session
            self.session = SessionManager(call_id=self.session_id or "local")

            # Connect STT
            connected = await self.stt.connect(
                on_transcript=self._on_transcript,
                on_error=self._on_stt_error,
                on_close=self._on_stt_close,
                endpointing_ms=config.stt_endpointing_ms,
            )

            if not connected:
                logger.error("agent_stt_connection_failed")
                return

            # Send greeting
            await self._send_greeting()
            # If the user stays silent, fire one check-in after a grace period.
            self._checkin_task = asyncio.create_task(self._checkin_loop())

            # Process inbound audio frames from the transport.
            async for frame in self.transport.receive_frames():
                await self._process_incoming_audio(frame)

        except Exception as e:
            logger.error("agent_call_error", error=str(e), error_type=type(e).__name__)
        finally:
            await self._cleanup()

    # ─────────────────────────────────────────────
    # SERVICE INITIALIZATION
    # ─────────────────────────────────────────────

    def _init_services(self):
        """Initialize all pipeline services."""
        self.stt = DeepgramSTTService(api_key=config.deepgram_api_key)

        self.llm = LLMService(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key,
            model_id=config.llm_model_id,
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
            llm="llm_service",
            tts="cartesia",
            model=config.llm_model_id,
            tools=[t["function"]["name"] for t in self.tool_definitions],
        )

    # ─────────────────────────────────────────────
    # AUDIO PROCESSING
    # ─────────────────────────────────────────────

    async def _process_incoming_audio(self, pcm_16k: bytes):
        """Forward raw 16 kHz linear16 PCM to Deepgram."""
        try:
            if self.stt and self.stt.is_connected:
                await self.stt.send_audio(pcm_16k)
        except Exception as e:
            logger.error("agent_audio_processing_error", error=str(e))

    # ─────────────────────────────────────────────
    # STT CALLBACKS
    # ─────────────────────────────────────────────

    async def _on_transcript(self, result, **kwargs):
        """Handle Deepgram transcription results.

        Deepgram emits a stream of interim results (often empty due to
        background noise) and, when it decides the utterance is over, a
        ``speech_final`` result. That final result can be EMPTY even when
        earlier interim results carried the real words — so we keep the best
        interim text per utterance and use it as a fallback when the final is
        blank. We also require a non-empty transcript before treating an empty
        ``speech_final`` (noise) as a real turn.
        """
        try:
            transcript = result.channel.alternatives[0].transcript
            is_final = getattr(result, "is_final", False)
            speech_final = getattr(result, "speech_final", False)

            # Track the most meaningful interim text seen in this utterance.
            if transcript and not speech_final:
                self._last_interim_text = transcript

            if not transcript:
                # Empty result. If this is the end-of-utterance marker, try to
                # recover real words from the interim we cached. Otherwise it's
                # just background noise — ignore it.
                if speech_final and self._last_interim_text.strip():
                    user_text = self._last_interim_text.strip()
                    self.current_transcript = ""
                    self._last_interim_text = ""
                    self._handle_user_turn(user_text)
                return

            if is_final:
                self.current_transcript += transcript + " "

            if speech_final and self.current_transcript.strip():
                user_text = self.current_transcript.strip()
                self.current_transcript = ""
                self._last_interim_text = ""
                self._handle_user_turn(user_text)

        except Exception as e:
            logger.error("agent_transcript_error", error=str(e))

    def _handle_user_turn(self, user_text: str):
        """Kick off a turn for a finalized user utterance."""
        # The user has spoken — the check-in is no longer needed.
        self._cancel_checkin()
        if not self.is_processing:
            asyncio.create_task(self._process_turn(user_text))
        else:
            logger.warning(
                "agent_skipping_turn",
                reason="still_processing",
                text=user_text[:50],
            )

    async def _on_stt_error(self, error, **kwargs):
        logger.error("agent_stt_error", error=str(error))

    async def _on_stt_close(self, close, **kwargs):
        logger.info("agent_stt_closed")

    # ─────────────────────────────────────────────
    # FULL TURN PROCESSING (with tool execution loop)
    # ─────────────────────────────────────────────

    async def _process_turn(self, user_text: str):
        """
        Process a complete user utterance with tool support.
        
        Flow:
        1. Add user message to conversation
        2. Call LLM (with tools available)
        3. If LLM returns tool calls → execute tools → call LLM again
        4. If LLM returns text → generate TTS → speak
        5. Repeat until LLM returns text (or max tool calls reached)
        """
        self.is_processing = True
        self.turn_count += 1
        turn_start = time.time()

        logger.info("agent_turn_start", turn=self.turn_count, user_text=user_text)

        try:
            # Step 1: Add user message
            self.conversation.add_user_message(user_text)

            # Step 2: Tool execution loop
            max_iterations = config.max_tool_calls_per_turn
            agent_text = None

            for iteration in range(max_iterations):
                # Get current messages
                messages = self.conversation.get_messages()

                # Call LLM with tools
                llm_response = await self.llm.generate(
                    messages=messages,
                    tools=self.tool_definitions,
                    tool_choice="auto",
                )

                # ─── LLM wants to call tools ───
                if llm_response.has_tool_calls:
                    # Add assistant tool call message to conversation
                    self.conversation.add_assistant_tool_calls(
                        llm_response.tool_calls
                    )

                    # Execute each tool call
                    for tool_call in llm_response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["arguments"]
                        tool_id = tool_call["id"]

                        logger.info(
                            "agent_executing_tool",
                            iteration=iteration,
                            tool_name=tool_name,
                            tool_args=tool_args,
                        )

                        # Execute the tool
                        result = await execute_tool(
                            tool_name=tool_name,
                            arguments=tool_args,
                            call_sid=self.call_sid,
                        )

                        # Add tool result to conversation
                        self.conversation.add_tool_result(
                            tool_call_id=tool_id,
                            result=result,
                        )

                        # Store in session for reference
                        if self.session:
                            await self.session.set(
                                f"last_tool_{tool_name}",
                                {"args": tool_args, "result": result},
                            )

                        # Check if this is a transfer request
                        if tool_name == "transfer_call" and "TRANSFER_REQUESTED" in result:
                            agent_text = result.replace("TRANSFER_REQUESTED: ", "")
                            break

                    # If transfer was requested, break out of the loop
                    if agent_text:
                        break

                    # Continue the loop — LLM will get tool results and respond
                    continue

                # ─── LLM returned text ───
                elif llm_response.has_content:
                    agent_text = llm_response.content
                    self.conversation.add_assistant_message(agent_text)
                    break

                # ─── LLM returned neither (shouldn't happen) ───
                else:
                    logger.warning("agent_empty_llm_response", iteration=iteration)
                    agent_text = "I'm sorry, could you say that again?"
                    break

            # Fallback if we hit max iterations
            if agent_text is None:
                agent_text = "I'm working on that. Let me transfer you to someone who can help."
                logger.warning("agent_max_tool_iterations", max_iterations=max_iterations)

            # Step 3: Generate TTS and speak
            await self._speak(agent_text)

            total_latency = (time.time() - turn_start) * 1000

            logger.info(
                "agent_turn_complete",
                turn=self.turn_count,
                user_text=user_text,
                agent_text=agent_text,
                total_latency_ms=round(total_latency, 1),
            )

            # Save transcript to session
            if self.session:
                await self.session.set(
                    "last_turn",
                    {
                        "user": user_text,
                        "agent": agent_text,
                        "latency_ms": round(total_latency, 1),
                    },
                )

        except Exception as e:
            logger.error(
                "agent_turn_error",
                turn=self.turn_count,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Speak a fallback message
            try:
                await self._speak("I'm sorry, I ran into an issue. Could you try again?")
            except Exception:
                pass

        finally:
            self.is_processing = False

    # ─────────────────────────────────────────────
    # SPEAK (TTS + Send to Twilio)
    # ─────────────────────────────────────────────

    async def _speak(self, text: str):
        """
        Convert text to speech and stream it back over the transport.
        
        Args:
            text: Text to speak
        """
        try:
            audio_data = await self.tts.synthesize(text)
            await self._send_audio(audio_data)
        except Exception as e:
            logger.error("agent_speak_error", error=str(e), text=text[:100])

    # ─────────────────────────────────────────────
    # SEND AUDIO OVER TRANSPORT
    # ─────────────────────────────────────────────

    async def _send_audio(self, pcm_16k: bytes):
        """Stream a PCM frame (16 kHz linear16) to the listener via the transport."""
        self.is_agent_speaking = True
        try:
            await self.transport.send(pcm_16k)
        except Exception as e:
            logger.error("agent_audio_send_error", error=str(e))
        finally:
            self.is_agent_speaking = False

    # ─────────────────────────────────────────────
    # GREETING
    # ─────────────────────────────────────────────

    async def _send_greeting(self):
        """Send an initial greeting when the call starts."""
        logger.info("agent_sending_greeting", greeting=GREETING_TEXT)
        await self._speak(GREETING_TEXT)

    # ─────────────────────────────────────────────
    # CHECK-IN ("are you there?")
    # ─────────────────────────────────────────────

    async def _checkin_loop(self):
        """
        If the user hasn't spoken after the greeting, prompt once.

        Fires at most one check-in per call so a quiet caller doesn't get
        spammed. Cancelled as soon as ``_on_transcript`` sees a real utterance.
        """
        try:
            # 6s grace after the greeting — long enough to wait for the
            # browser to finish setting up the mic capture + Deepgram VAD
            # to settle, short enough that the call doesn't feel dead.
            await asyncio.sleep(6.0)
            if self._checkin_sent or self.is_processing or self.turn_count > 0:
                return
            # If we've already received a final transcript, the user is
            # obviously there — skip. We deliberately do NOT skip on VAD
            # events, since VAD triggers on any sound (including the user's
            # TV, a fan, or browser-side echo).
            self._checkin_sent = True
            logger.info("agent_checkin_sending")
            await self._speak(
                "Hey, are you still there? I'm listening whenever you're ready."
            )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("agent_checkin_error", error=str(e))

    def _cancel_checkin(self):
        """Cancel a pending check-in (call when the user actually speaks)."""
        if self._checkin_task and not self._checkin_task.done():
            self._checkin_task.cancel()
            self._checkin_task = None
    # ─────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────

    async def _cleanup(self):
        """Clean up resources when the call ends."""
        self._cancel_checkin()
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

        # Save final transcript to session
        if self.session:
            await self.session.set(
                "call_summary",
                {
                    "call_sid": self.call_sid,
                    "duration_seconds": round(time.time() - self.call_start_time, 1) if self.call_start_time else 0,
                    "total_turns": self.turn_count,
                    "transcript": self.conversation.get_transcript(),
                },
            )

        self.is_agent_speaking = False
        self.is_processing = False