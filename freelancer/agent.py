"""
Freelancer Voice Agent — outbound calls on behalf of a freelancer.

Same audio pipeline as clinic agent, different prompts + tools.
"""

import asyncio
import time
from typing import Optional

from services.deepgram_stt import DeepgramSTTService
from services.llm import LLMService
from services.cartesia_tts import CartesiaTTSService
from services.audio_transport import AudioTransport
from freelancer.profile import FreelancerProfile
from freelancer.prompts import build_freelancer_prompt, GREETING_TEMPLATE, WRAP_UP
from freelancer.tools import get_freelancer_tool_definitions, get_freelancer_tool_map
from agents.conversation import ConversationManager
from memory.session import SessionManager
from config import config
from utils.logging import get_logger

logger = get_logger(__name__)


class FreelancerVoiceAgent:
    """
    Voice agent for outbound calls on behalf of a freelancer.

    Usage:
        agent = FreelancerVoiceAgent(transport=transport, profile=profile, lead_info=lead_info)
        await agent.run()
    """

    def __init__(self, transport: AudioTransport, profile: FreelancerProfile, lead_info: Optional[dict] = None):
        self.transport = transport
        self.profile = profile
        self.lead_info = lead_info or {}
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None

        self.stt: Optional[DeepgramSTTService] = None
        self.llm: Optional[LLMService] = None
        self.tts: Optional[CartesiaTTSService] = None

        # Build prompt from profile
        system_prompt = build_freelancer_prompt(profile)
        self.conversation = ConversationManager(
            system_prompt=system_prompt,
            max_history=config.max_conversation_history,
        )
        self.session: Optional[SessionManager] = None

        # Tools
        self.tool_definitions = get_freelancer_tool_definitions()
        self.tool_map = get_freelancer_tool_map(profile)

        # State
        self.current_transcript = ""
        self.is_processing = False
        self.is_agent_speaking = False
        self.turn_count = 0
        self.call_start_time: Optional[float] = None
        self.call_ended = False

    # ─────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────

    async def run(self):
        """Handle the full call lifecycle."""
        logger.info(
            "freelancer_agent_call_starting",
            freelancer=self.profile.name,
            lead=self.lead_info,
        )
        self.call_start_time = time.time()

        try:
            self._init_services()
            self.session = SessionManager(call_id=self.lead_info.get("id", "local") if self.lead_info else "local")

            connected = await self.stt.connect(
                on_transcript=self._on_transcript,
                on_error=self._on_stt_error,
                on_close=self._on_stt_close,
                endpointing_ms=config.stt_endpointing_ms,
            )

            if not connected:
                logger.error("freelancer_agent_stt_connection_failed")
                return

            await self._send_greeting()

            async for frame in self.transport.receive_frames():
                if self.call_ended:
                    break
                await self._process_incoming_audio(frame)

        except Exception as e:
            logger.error("freelancer_agent_call_error", error=str(e))
        finally:
            await self._cleanup()

    # ─────────────────────────────────────────────
    # SERVICE INIT
    # ─────────────────────────────────────────────

    def _init_services(self):
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

    # ─────────────────────────────────────────────
    # AUDIO PROCESSING
    # ─────────────────────────────────────────────

    async def _process_incoming_audio(self, pcm_16k: bytes):
        try:
            if self.stt and self.stt.is_connected:
                await self.stt.send_audio(pcm_16k)
        except Exception as e:
            logger.error("freelancer_audio_error", error=str(e))

    # ─────────────────────────────────────────────
    # STT CALLBACKS
    # ─────────────────────────────────────────────

    async def _on_transcript(self, result, **kwargs):
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
        except Exception as e:
            logger.error("freelancer_transcript_error", error=str(e))

    async def _on_stt_error(self, error, **kwargs):
        logger.error("freelancer_stt_error", error=str(error))

    async def _on_stt_close(self, close, **kwargs):
        logger.info("freelancer_stt_closed")

    # ─────────────────────────────────────────────
    # TURN PROCESSING WITH TOOLS
    # ─────────────────────────────────────────────

    async def _process_turn(self, user_text: str):
        """Process a turn with the tool execution loop."""
        self.is_processing = True
        self.turn_count += 1
        turn_start = time.time()

        logger.info("freelancer_turn_start", turn=self.turn_count, user_text=user_text)

        try:
            self.conversation.add_user_message(user_text)
            max_iterations = config.max_tool_calls_per_turn
            agent_text = None

            for iteration in range(max_iterations):
                messages = self.conversation.get_messages()
                llm_response = await self.llm.generate(
                    messages=messages,
                    tools=self.tool_definitions,
                    tool_choice="auto",
                )

                if llm_response.has_tool_calls:
                    self.conversation.add_assistant_tool_calls(llm_response.tool_calls)

                    for tool_call in llm_response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["arguments"]
                        tool_id = tool_call["id"]

                        logger.info("freelancer_executing_tool", tool_name=tool_name, tool_args=tool_args)

                        tool_func = self.tool_map.get(tool_name)
                        if tool_func:
                            try:
                                result = await tool_func(**tool_args)
                            except Exception as e:
                                result = f"Error: {str(e)}"
                        else:
                            result = f"Unknown tool: {tool_name}"

                        self.conversation.add_tool_result(tool_call_id=tool_id, result=result)

                        if "TRANSFER_REQUESTED" in result:
                            agent_text = result.replace("TRANSFER_REQUESTED: ", "")
                            break
                        if "CALL_END" in result:
                            agent_text = WRAP_UP
                            self.call_ended = True
                            break

                    if agent_text:
                        break
                    continue

                elif llm_response.has_content:
                    agent_text = llm_response.content
                    self.conversation.add_assistant_message(agent_text)
                    break
                else:
                    agent_text = "Could you repeat that?"
                    break

            if agent_text is None:
                agent_text = WRAP_UP

            await self._speak(agent_text)

            total_latency = (time.time() - turn_start) * 1000
            logger.info(
                "freelancer_turn_complete",
                turn=self.turn_count,
                total_latency_ms=round(total_latency, 1),
            )

        except Exception as e:
            logger.error("freelancer_turn_error", error=str(e))
        finally:
            self.is_processing = False

    # ─────────────────────────────────────────────
    # SPEAK / AUDIO
    # ─────────────────────────────────────────────

    async def _speak(self, text: str):
        try:
            audio_data = await self.tts.synthesize(text)
            await self._send_audio(audio_data)
        except Exception as e:
            logger.error("freelancer_speak_error", error=str(e))

    async def _send_audio(self, pcm_16k: bytes):
        self.is_agent_speaking = True
        try:
            await self.transport.send(pcm_16k)
        except Exception as e:
            logger.error("freelancer_audio_send_error", error=str(e))
        finally:
            self.is_agent_speaking = False

    async def _send_greeting(self):
        greeting = GREETING_TEMPLATE.format(name=self.profile.name)
        logger.info("freelancer_greeting", greeting=greeting)
        await self._speak(greeting)

    # ─────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────

    async def _cleanup(self):
        if self.call_start_time:
            duration = time.time() - self.call_start_time
            logger.info(
                "freelancer_call_ended",
                call_sid=self.call_sid,
                duration_seconds=round(duration, 1),
                total_turns=self.turn_count,
            )

        if self.stt:
            await self.stt.disconnect()

        # Auto follow-up email
        if self.profile.follow_up_email and self.lead_info.get("email"):
            try:
                from tools.email_followup import send_followup_email
                await send_followup_email(
                    profile=self.profile,
                    email=self.lead_info["email"],
                    name=self.lead_info.get("name", "there"),
                    summary=self.conversation.get_transcript()[:500],
                )
            except Exception as e:
                logger.error("freelancer_followup_email_error", error=str(e))

        self.is_agent_speaking = False
        self.is_processing = False