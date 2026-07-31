"""
FastAPI server — entry point for the voice calling agent.

Handles:
- Twilio webhook for inbound calls
- WebSocket for real-time audio streaming
- Health check endpoints
- Outbound call initiation (Phase 2+)
"""

import os
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
import uvicorn

from agents.voice_agent import VoiceAgent
from config import config
from utils.logging import setup_logging, get_logger

# ─── Initialize Logging ───
setup_logging(log_level=config.log_level)
logger = get_logger(__name__)

# ─── Validate Config ───
missing_keys = config.validate()
if missing_keys:
    logger.warning("config_missing_keys", missing=missing_keys)
    logger.warning("Some features may not work. Check your .env file.")
else:
    logger.info("config_valid")

# ─── FastAPI App ───
app = FastAPI(
    title="Voice Calling Agent",
    version="1.0.0",
    description="Phase 1 — Hello World",
)

# Track active calls
active_calls: dict[str, VoiceAgent] = {}


# ─────────────────────────────────────────────
# TWILIO WEBHOOKS
# ─────────────────────────────────────────────

@app.post("/twilio/inbound")
async def handle_inbound_call(request: Request):
    """
    Twilio calls this webhook when someone calls your number.

    We respond with TwiML that connects a Media Stream WebSocket
    for real-time audio exchange.
    """
    logger.info("inbound_call_received")

    response = VoiceResponse()
    connect = Connect()

    # Twilio requires wss:// (secure WebSocket)
    stream_url = f"wss://{config.server_host}/ws/call"
    logger.info("connecting_stream", url=stream_url)

    connect.stream(
        url=stream_url,
        name="voice-agent-stream",
    )
    response.append(connect)

    return HTMLResponse(
        content=str(response),
        status_code=200,
        media_type="application/xml",
    )


@app.post("/twilio/outbound")
async def start_outbound_call(request: Request):
    """
    Trigger an outbound call. (Phase 2+ — placeholder)
    """
    from twilio.rest import Client

    form_data = await request.form()
    to_number = form_data.get("to_number")

    if not to_number:
        return HTMLResponse(content="Missing to_number", status_code=400)

    client = Client(config.twilio_account_sid, config.twilio_auth_token)

    call = client.calls.create(
        to=to_number,
        from_=config.twilio_phone_number,
        url=f"https://{config.server_host}/twilio/outbound-flow",
    )

    logger.info("outbound_call_initiated", call_sid=call.sid, to=to_number)
    return HTMLResponse(content=f"Call initiated: {call.sid}")


@app.post("/twilio/outbound-flow")
async def handle_outbound_flow(request: Request):
    """TwiML for outbound calls (when the called party answers)."""
    response = VoiceResponse()
    connect = Connect()
    connect.stream(
        url=f"wss://{config.server_host}/ws/call",
        name="voice-agent-stream",
    )
    response.append(connect)

    return HTMLResponse(
        content=str(response),
        status_code=200,
        media_type="application/xml",
    )


# ─────────────────────────────────────────────
# WEBSOCKET — REAL-TIME AUDIO
# ─────────────────────────────────────────────

@app.websocket("/ws/call")
async def handle_call_stream(websocket: WebSocket):
    """
    Handle the real-time audio stream from Twilio.

    This is where the voice agent lives:
    - Twilio sends audio from the caller
    - VoiceAgent processes it (STT → LLM → TTS)
    - Audio is sent back to the caller
    """
    await websocket.accept()
    logger.info("websocket_accepted")

    # Create a new VoiceAgent for this call
    agent = VoiceAgent(twilio_ws=websocket)

    try:
        await agent.run()
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", call_sid=agent.call_sid)
    except Exception as e:
        logger.error(
            "websocket_error",
            call_sid=agent.call_sid,
            error=str(e),
            error_type=type(e).__name__,
        )
    finally:
        # Clean up
        if agent.call_sid and agent.call_sid in active_calls:
            del active_calls[agent.call_sid]
        logger.info("call_cleaned_up", call_sid=agent.call_sid)


# ─────────────────────────────────────────────
# HEALTH & INFO
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_calls": len(active_calls),
        "config": {
            "twilio": bool(config.twilio_account_sid),
            "deepgram": bool(config.deepgram_api_key),
            "bedrock": bool(config.aws_access_key_id),
            "cartesia": bool(config.cartesia_api_key),
        },
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Voice Calling Agent",
        "version": "1.0.0",
        "phase": "1 — Hello World",
        "model": config.bedrock_model_id,
        "health": "/health",
        "webhook": "/twilio/inbound",
    }


# ─────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(
        "server_starting",
        port=config.port,
        server_host=config.server_host,
        model=config.bedrock_model_id,
    )
    print(f"\n🚀 Voice Agent Server Starting")
    print(f"   Port: {config.port}")
    print(f"   Model: {config.bedrock_model_id}")
    print(f"   Health: http://localhost:{config.port}/health")
    print(f"   Webhook: https://{config.server_host}/twilio/inbound")
    print()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.port,
        log_level="info",
    )