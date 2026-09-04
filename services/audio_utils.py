"""
Audio conversion utilities for Twilio ↔ Deepgram ↔ Cartesia.

Twilio Media Streams:
  - Format: 8kHz mulaw (base64 encoded)
  - Chunk size: ~20ms = 160 bytes per chunk

Deepgram:
  - Format: 16kHz linear16 (PCM signed 16-bit little-endian)
  - Mono

Cartesia:
  - Format: 16kHz linear16 (PCM signed 16-bit little-endian)
  - Mono

Audio flow:
  INCOMING:  Twilio [8kHz mulaw] → convert → [16kHz PCM] → Deepgram
  OUTGOING:  Cartesia [16kHz PCM] → convert → [8kHz mulaw] → Twilio
"""

import base64
import audioop
import struct


# ─────────────────────────────────────────────
# INCOMING: Twilio → Deepgram
# ─────────────────────────────────────────────

def mulaw_to_linear16(mulaw_bytes: bytes) -> bytes:
    """
    Convert 8kHz mulaw audio to 16kHz linear16 PCM.

    Args:
        mulaw_bytes: Raw mulaw audio bytes (8kHz)

    Returns:
        Linear16 PCM audio bytes (16kHz, 16-bit, mono)
    """
    # Step 1: mulaw → linear16 (still 8kHz)
    linear_8k = audioop.ulaw2lin(mulaw_bytes, 2)  # 2 = 16-bit width

    # Step 2: Resample 8kHz → 16kHz
    linear_16k, _ = audioop.ratecv(
        linear_8k,
        2,       # sample width (16-bit = 2 bytes)
        1,       # channels (mono)
        8000,    # source sample rate
        16000,   # target sample rate
        None,    # state (unused for first call)
    )

    return linear_16k


def decode_twilio_payload(base64_payload: str) -> bytes:
    """Decode a base64-encoded mulaw payload."""
    return base64.b64decode(base64_payload)

decode_signalwire_payload = decode_twilio_payload


def twilio_to_deepgram(base64_payload: str) -> bytes:
    """
    Full incoming pipeline:
    base64 mulaw → Deepgram linear16 PCM

    Args:
        base64_payload: Base64-encoded 8kHz mulaw audio

    Returns:
        16kHz linear16 PCM audio ready for Deepgram
    """
    mulaw_bytes = decode_twilio_payload(base64_payload)
    linear16_16k = mulaw_to_linear16(mulaw_bytes)
    return linear16_16k

signalwire_to_deepgram = twilio_to_deepgram


# ─────────────────────────────────────────────
# OUTGOING: Cartesia → SignalWire / Twilio
# ─────────────────────────────────────────────

def linear16_to_mulaw(linear16_16k: bytes) -> bytes:
    """
    Convert 16kHz linear16 PCM to 8kHz mulaw audio.

    Args:
        linear16_16k: Linear16 PCM audio bytes (16kHz, 16-bit, mono)

    Returns:
        Mulaw audio bytes (8kHz)
    """
    # Step 1: Resample 16kHz → 8kHz
    linear_8k, _ = audioop.ratecv(
        linear16_16k,
        2,       # sample width
        1,       # channels
        16000,   # source rate
        8000,    # target rate
        None,
    )

    # Step 2: linear16 → mulaw
    mulaw = audioop.lin2ulaw(linear_8k, 2)

    return mulaw


def encode_twilio_payload(mulaw_bytes: bytes) -> str:
    """Encode mulaw audio to base64 for stream payload."""
    return base64.b64encode(mulaw_bytes).decode("utf-8")

encode_signalwire_payload = encode_twilio_payload


def cartesia_to_twilio(linear16_16k: bytes) -> str:
    """
    Full outgoing pipeline:
    Cartesia linear16 PCM → base64 mulaw
    """
    mulaw = linear16_to_mulaw(linear16_16k)
    base64_payload = encode_twilio_payload(mulaw)
    return base64_payload

cartesia_to_signalwire = cartesia_to_twilio


# ─────────────────────────────────────────────
# CHUNKING: Send audio in proper-sized chunks
# ─────────────────────────────────────────────

def chunk_audio(audio_bytes: bytes, chunk_size: int = 800) -> list[bytes]:
    """
    Split audio into chunks for Twilio.

    At 8kHz mulaw:
      800 bytes = 100ms of audio
      160 bytes = 20ms of audio (Twilio's typical chunk size)

    We use 800 bytes (100ms) for smoother playback.

    Args:
        audio_bytes: Raw mulaw audio to chunk
        chunk_size: Size of each chunk in bytes

    Returns:
        List of audio chunks
    """
    chunks = []
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i + chunk_size]
        if len(chunk) > 0:
            chunks.append(chunk)
    return chunks


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def create_silence_16k(duration_ms: int = 200) -> bytes:
    """
    Generate silence in 16kHz linear16 format.

    Useful for sending to Deepgram to keep the connection alive.
    """
    num_samples = int(16000 * duration_ms / 1000)
    return b'\x00' * (num_samples * 2)  # 2 bytes per sample


def estimate_duration_ms(audio_bytes: bytes, sample_rate: int = 8000, sample_width: int = 1) -> int:
    """Estimate the duration of audio in milliseconds."""
    num_samples = len(audio_bytes) // sample_width
    duration_ms = int(num_samples * 1000 / sample_rate)
    return duration_ms