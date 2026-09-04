"""
Audio transport abstraction.

Decouples the voice agents from any specific carrier (Twilio / SignalWire /
browser) by exposing a small interface that only speaks 16 kHz linear16 PCM —
the format Deepgram expects on the way in and Cartesia emits on the way out.

Transports:
  - BrowserAudioTransport: wraps a FastAPI WebSocket. The browser sends raw
    16 kHz linear16 PCM frames as binary WebSocket messages and receives the
    agent's TTS audio the same way. No mulaw, no base64, no TwiML.
"""

from typing import Optional, AsyncIterator

from starlette.websockets import WebSocket as StarletteWebSocket
from utils.logging import get_logger

logger = get_logger(__name__)


class AudioTransport:
    """
    Interface for a bidirectional audio channel.

    All PCM exchanged here is 16 kHz, mono, signed 16-bit little-endian
    (linear16) — i.e. 2 bytes per sample.
    """

    async def receive(self) -> Optional[bytes]:
        """
        Return the next inbound PCM frame, or ``None`` when the channel is closed.
        """
        raise NotImplementedError

    async def send(self, pcm_16k: bytes) -> None:
        """Send an outbound PCM frame to the listener."""
        raise NotImplementedError

    def is_open(self) -> bool:
        """Whether the transport is still usable for I/O."""
        raise NotImplementedError

    async def receive_frames(self) -> AsyncIterator[bytes]:
        """Convenience async iterator over inbound audio frames (stops at close)."""
        while self.is_open():
            frame = await self.receive()
            if frame is None:
                break
            if not frame:
                # Skip empty frames produced by text/control messages.
                continue
            yield frame

    async def close(self) -> None:
        """Release the underlying channel."""
        raise NotImplementedError


class BrowserAudioTransport(AudioTransport):
    """
    Audio transport backed by a FastAPI/Starlette WebSocket.

    Frame contract (both directions): a single binary WebSocket message carries
    one PCM chunk of arbitrary length (16 kHz linear16 mono). Text messages are
    reserved for control/event metadata (JSON) and are surfaced via
    ``on_text`` if a callback was supplied at construction time.
    """

    def __init__(
        self,
        websocket: StarletteWebSocket,
        on_text: Optional[callable] = None,
    ):
        self.ws = websocket
        self._on_text = on_text
        self._open = True
        # Diagnostic counters — let us tell, on the server side, whether the
        # browser is actually sending audio frames or whether the silence is
        # upstream. Logged at transport teardown so we don't spam mid-call.
        self._frames_in = 0
        self._bytes_in = 0
        self._last_log_at = 0.0
        import time as _t
        self._t0 = _t.monotonic()

    async def receive(self) -> Optional[bytes]:
        try:
            message = await self.ws.receive()
        except Exception:
            self._open = False
            return None

        msg_type = message.get("type")

        if msg_type == "websocket.disconnect":
            self._open = False
            return None

        if msg_type == "websocket.receive":
            # Binary audio frame.
            if "bytes" in message and message["bytes"] is not None:
                data = message["bytes"]
                self._frames_in += 1
                self._bytes_in += len(data)
                return data
            # Text control message (JSON metadata / events).
            if "text" in message and message["text"] is not None:
                if self._on_text:
                    try:
                        self._on_text(message["text"])
                    except Exception as e:
                        logger.warning("transport_text_handler_error", error=str(e))
                return b""
            return b""

        # Any other message type (e.g. ping/pong handled internally) — skip.
        return b""

    async def send(self, pcm_16k: bytes) -> None:
        if not self._open:
            return
        try:
            await self.ws.send_bytes(pcm_16k)
        except Exception as e:
            logger.warning("transport_send_error", error=str(e))
            self._open = False

    def is_open(self) -> bool:
        return self._open

    async def close(self) -> None:
        import time as _t
        logger.info(
            "transport_closed",
            frames_in=self._frames_in,
            bytes_in=self._bytes_in,
            duration_s=round(_t.monotonic() - self._t0, 2),
        )
        self._open = False
        try:
            await self.ws.close()
        except Exception:
            pass
