"""
Test all services individually before running the full agent.

Run: python -m tests.test_services
"""

import asyncio
import os
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import config
from utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def test_config():
    """Test configuration."""
    print("\n" + "=" * 50)
    print("TEST 1: Configuration")
    print("=" * 50)

    missing = config.validate()
    if missing:
        for key in missing:
            print(f"  ❌ {key}: NOT SET")
        return False

    print(f"  ✅ Twilio: {config.twilio_account_sid[:8]}...")
    print(f"  ✅ Deepgram: {config.deepgram_api_key[:8]}...")
    print(f"  ✅ LLM endpoint: {config.llm_base_url}")
    print(f"  ✅ LLM Model: {config.llm_model_id}")
    print(f"  ✅ Cartesia: {config.cartesia_api_key[:8]}...")
    return True


async def test_deepgram():
    """Test Deepgram STT connection."""
    print("\n" + "=" * 50)
    print("TEST 2: Deepgram STT")
    print("=" * 50)

    from services.deepgram_stt import DeepgramSTTService

    stt = DeepgramSTTService(api_key=config.deepgram_api_key)

    try:
        connected = await stt.connect(
            on_transcript=lambda result, **kwargs: None,
            on_error=lambda error, **kwargs: print(f"  ❌ Error: {error}"),
            endpointing_ms=1000,
        )

        if connected:
            silence = b'\x00' * 32000
            await stt.send_audio(silence)
            print("  ✅ Deepgram connection established")
            await stt.disconnect()
            return True
        else:
            print("  ❌ Failed to connect")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_llm():
    """Test LLM service (OpenAI-compatible)."""
    print("\n" + "=" * 50)
    print("TEST 3: LLM Service")
    print("=" * 50)

    from services.llm import LLMService

    llm = LLMService(
        base_url=config.llm_base_url,
        api_key=config.llm_api_key,
        model_id=config.llm_model_id,
    )

    try:
        messages = [
            {"role": "system", "content": "You are a phone assistant. Keep responses to 1-2 sentences."},
            {"role": "user", "content": "Hi, I'm calling about your premium plan."},
        ]

        response = await llm.generate(messages)
        print(f"  👤 User: Hi, I'm calling about your premium plan.")
        print(f"  🤖 Agent: {response}")

        if response:
            print("  ✅ LLM service working")
            return True
        else:
            print("  ❌ Empty response")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_llm_streaming():
    """Test LLM service streaming."""
    print("\n" + "=" * 50)
    print("TEST 4: LLM Service (Streaming)")
    print("=" * 50)

    from services.llm import LLMService

    llm = LLMService(
        base_url=config.llm_base_url,
        api_key=config.llm_api_key,
        model_id=config.llm_model_id,
    )

    try:
        messages = [
            {"role": "system", "content": "You are a phone assistant. Keep responses to 1-2 sentences."},
            {"role": "user", "content": "What's the weather like?"},
        ]

        print("  🤖 Agent (streaming): ", end="", flush=True)
        full_response = ""
        async for chunk in llm.generate_stream(messages):
            print(chunk, end="", flush=True)
            full_response += chunk
        print()

        if full_response:
            print("  ✅ Streaming working")
            return True
        else:
            print("  ❌ Empty streaming response")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_cartesia():
    """Test Cartesia TTS."""
    print("\n" + "=" * 50)
    print("TEST 5: Cartesia TTS")
    print("=" * 50)

    from services.cartesia_tts import CartesiaTTSService

    tts = CartesiaTTSService(
        api_key=config.cartesia_api_key,
        voice_id=config.cartesia_voice_id,
    )

    try:
        audio_data = await tts.synthesize("Hello, thanks for calling!")

        if audio_data and len(audio_data) > 0:
            print(f"  ✅ Generated {len(audio_data)} bytes of audio")

            wav_path = os.path.join(tempfile.gettempdir(), "test_cartesia.wav")
            with wave.open(wav_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(audio_data)

            print(f"  🔊 Saved to: {wav_path}")
            return True
        else:
            print("  ❌ No audio generated")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_full_pipeline():
    """Test the full STT → LLM → TTS pipeline."""
    print("\n" + "=" * 50)
    print("TEST 6: Full Pipeline (simulated)")
    print("=" * 50)

    from services.llm import LLMService
    from services.cartesia_tts import CartesiaTTSService
    from agents.conversation import ConversationManager
    from agents.prompts import SYSTEM_PROMPT

    conv = ConversationManager(system_prompt=SYSTEM_PROMPT)
    llm = LLMService(
        base_url=config.llm_base_url,
        api_key=config.llm_api_key,
        model_id=config.llm_model_id,
    )
    tts = CartesiaTTSService(
        api_key=config.cartesia_api_key,
        voice_id=config.cartesia_voice_id,
    )

    try:
        user_text = "What's the price of your premium plan?"
        print(f"  👤 User: {user_text}")

        conv.add_user_message(user_text)
        messages = conv.get_messages()
        agent_text = await llm.generate(messages)
        conv.add_assistant_message(agent_text)
        print(f"  🤖 Agent: {agent_text}")

        audio_data = await tts.synthesize(agent_text)

        wav_path = os.path.join(tempfile.gettempdir(), "test_pipeline.wav")
        with wave.open(wav_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(audio_data)

        print(f"  ✅ Full pipeline working!")
        print(f"  🔊 Saved to: {wav_path}")
        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_audio_conversion():
    """Test audio format conversion."""
    print("\n" + "=" * 50)
    print("TEST 7: Audio Conversion")
    print("=" * 50)

    from services.audio_utils import (
        mulaw_to_linear16,
        linear16_to_mulaw,
        chunk_audio,
    )

    try:
        mulaw_input = b'\xff' * 8000
        linear16 = mulaw_to_linear16(mulaw_input)
        print(f"  ✅ mulaw→linear16: {len(mulaw_input)} → {len(linear16)} bytes")

        mulaw_output = linear16_to_mulaw(linear16)
        print(f"  ✅ linear16→mulaw: {len(linear16)} → {len(mulaw_output)} bytes")

        chunks = chunk_audio(mulaw_output, chunk_size=800)
        print(f"  ✅ Chunked into {len(chunks)} chunks")

        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def main():
    print("🔧 Voice Agent — Phase 1 Test Suite")
    print("=" * 50)

    results = {}
    results["config"] = await test_config()
    results["audio_conversion"] = await test_audio_conversion()
    results["deepgram"] = await test_deepgram()
    results["llm"] = await test_llm()
    results["llm_streaming"] = await test_llm_streaming()
    results["cartesia"] = await test_cartesia()
    results["full_pipeline"] = await test_full_pipeline()

    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! Ready for live calls.")
    else:
        print("\n⚠️  Some tests failed. Fix issues before proceeding.")


if __name__ == "__main__":
    asyncio.run(main())