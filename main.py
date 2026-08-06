"""
FastAPI server — entry point for the voice calling agent.

Phase 2 additions:
- Outbound call support
- Knowledge base initialization
"""

from datetime import datetime
import os
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
import uvicorn

from agents.voice_agent import VoiceAgent
from config import config


from freelancer.profile import get_default_profile
from leads.manager import get_lead_manager


from utils.logging import setup_logging, get_logger

# ─── Initialize Logging ───
setup_logging(log_level=config.log_level)
logger = get_logger(__name__)


_current_freelancer_profile = get_default_profile()

# ─── Validate Config ───
missing_keys = config.validate()
if missing_keys:
    logger.warning("config_missing_keys", missing=missing_keys)
else:
    logger.info("config_valid")

# ─── Initialize Knowledge Base ───
from rag.knowledge_base import get_knowledge_base
kb = get_knowledge_base()
logger.info("knowledge_base_loaded", num_documents=len(kb.documents))

# ─── FastAPI App ───
app = FastAPI(
    title="Voice Calling Agent",
    version="2.0.0",
    description="Phase 2 — Smart Agent with Tools",
)

active_calls: dict[str, VoiceAgent] = {}


# ─────────────────────────────────────────────
# SIGNALWIRE WEBHOOKS
# ─────────────────────────────────────────────

@app.post("/signalwire/inbound")
@app.post("/twilio/inbound")
async def handle_inbound_call(request: Request):
    """SignalWire calls this webhook when someone calls your number."""
    logger.info("inbound_call_received")

    response = VoiceResponse()
    connect = Connect()
    stream_url = f"wss://{config.server_host}/ws/call"
    logger.info("connecting_stream", url=stream_url)

    connect.stream(url=stream_url, name="voice-agent-stream")
    response.append(connect)

    return HTMLResponse(
        content=str(response),
        status_code=200,
        media_type="application/xml",
    )


@app.post("/signalwire/outbound")
@app.post("/twilio/outbound")
async def start_outbound_call(request: Request):
    """Trigger an outbound call via SignalWire."""
    to_number = None

    # Support JSON or Form body
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        to_number = body.get("to_number") or body.get("to")
    else:
        try:
            form_data = await request.form()
            to_number = form_data.get("to_number") or form_data.get("to")
        except Exception:
            pass

    if not to_number:
        return HTMLResponse(content="Missing to_number", status_code=400)

    to_number = str(to_number).strip()

    client = config.get_signalwire_client()

    try:
        call = client.calls.create(
            to=to_number,
            from_=config.signalwire_phone_number,
            url=f"https://{config.server_host}/signalwire/outbound-flow",
        )

        logger.info("outbound_call_initiated", call_sid=call.sid, to=to_number)
        return HTMLResponse(content=f"Call initiated: {call.sid}")
    except Exception as e:
        error_msg = str(e)
        logger.error("outbound_call_failed", error=error_msg, to=to_number)
        if "21219" in error_msg or "verified number" in error_msg:
            return HTMLResponse(
                content=f"SignalWire Trial Restriction: Destination number '{to_number}' is not verified. Please verify this number in SignalWire Console under Phone Numbers -> Verified Numbers, or upgrade your account.",
                status_code=400,
            )
        return HTMLResponse(content=f"Call failed: {error_msg}", status_code=500)


@app.post("/signalwire/outbound-flow")
@app.post("/twilio/outbound-flow")
async def handle_outbound_flow(request: Request):
    """LaML/TwiML for outbound calls."""
    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=f"wss://{config.server_host}/ws/call", name="voice-agent-stream")
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
    """Handle the real-time audio stream from Twilio."""
    await websocket.accept()
    logger.info("websocket_accepted")

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
        if agent.call_sid and agent.call_sid in active_calls:
            del active_calls[agent.call_sid]
        logger.info("call_cleaned_up", call_sid=agent.call_sid)


# ─────────────────────────────────────────────
# KNOWLEDGE BASE API
# ─────────────────────────────────────────────

@app.get("/knowledge/search")
async def search_knowledge_api(q: str):
    """Search the knowledge base (for testing)."""
    kb = get_knowledge_base()
    results = kb.search(q, top_k=3)
    return {"query": q, "results": results}


@app.get("/knowledge/stats")
async def knowledge_stats():
    """Get knowledge base statistics."""
    kb = get_knowledge_base()
    return {
        "num_documents": len(kb.documents),
        "index_size": len(kb._index),
    }


# ─────────────────────────────────────────────
# HEALTH & INFO
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_calls": len(active_calls),
        "phase": 2,
        "config": {
            "signalwire": bool(config.signalwire_project_id),
            "deepgram": bool(config.deepgram_api_key),
            "bedrock": bool(config.bedrock_base_url),
            "cartesia": bool(config.cartesia_api_key),
        },
        "tools": ["lookup_pricing", "check_availability", "book_appointment", "search_knowledge", "transfer_call"],
        "knowledge_base": {
            "num_documents": len(get_knowledge_base().documents),
        },
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Voice Calling Agent",
        "version": "2.0.0",
        "phase": "2 — Smart Agent with Tools",
        "model": config.bedrock_model_id,
        "health": "/health",
        "webhook": "/signalwire/inbound",
        "knowledge_search": "/knowledge/search?q=your+query",
    }


# ─────────────────────────────────────────────
# FREELANCER API ROUTES
# ─────────────────────────────────────────────

@app.get("/freelancer/profile")
async def get_freelancer_profile():
    """Get the current freelancer profile."""
    return _current_freelancer_profile.dict()


@app.post("/freelancer/profile")
async def update_freelancer_profile(request: Request):
    """Create or update the freelancer profile."""
    global _current_freelancer_profile
    from freelancer.profile import FreelancerProfile
    body = await request.json()
    _current_freelancer_profile = FreelancerProfile(**body)
    logger.info("freelancer_profile_updated", name=_current_freelancer_profile.name)
    return {"status": "updated", "name": _current_freelancer_profile.name}


@app.post("/freelancer/leads")
async def add_freelancer_lead(request: Request):
    """Add a new lead to call."""
    from leads.manager import Lead
    body = await request.json()
    lead = Lead(**body)
    lm = get_lead_manager()
    lead_id = lm.add_lead(lead)
    return {"status": "added", "lead_id": lead_id}


@app.get("/freelancer/leads")
async def list_freelancer_leads():
    """List all leads."""
    lm = get_lead_manager()
    return {"leads": [l.dict() for l in lm.get_all_leads()]}


@app.post("/freelancer/call/{lead_id}")
async def call_freelancer_lead(lead_id: str):
    """Trigger an outbound call to a lead via SignalWire."""
    lm = get_lead_manager()
    lead = lm.get_lead(lead_id)
    if not lead:
        return HTMLResponse(content="Lead not found", status_code=404)

    try:
        client = config.get_signalwire_client()
        to_phone = lead.phone.strip()
        call = client.calls.create(
            to=to_phone,
            from_=config.signalwire_phone_number,
            url=f"https://{config.server_host}/freelancer/outbound-flow",
        )
        lm.update_lead_status(lead_id, "called", called_at=datetime.now().isoformat())
        logger.info("freelancer_outbound_call", lead_id=lead_id, call_sid=call.sid)
        return {"status": "calling", "call_sid": call.sid, "to": lead.phone}
    except Exception as e:
        logger.error("freelancer_outbound_error", error=str(e))
        return HTMLResponse(content=str(e), status_code=500)


# ─────────────────────────────────────────────
# FREELANCER OUTBOUND FLOW
# ─────────────────────────────────────────────

@app.post("/freelancer/outbound-flow")
async def freelancer_outbound_flow(request: Request):
    """TwiML for freelancer outbound calls."""
    response = VoiceResponse()
    connect = Connect()
    connect.stream(
        url=f"wss://{config.server_host}/ws/freelancer-call",
        name="freelancer-agent-stream",
    )
    response.append(connect)
    return HTMLResponse(content=str(response), status_code=200, media_type="application/xml")


@app.websocket("/ws/freelancer-call")
async def handle_freelancer_call_stream(websocket: WebSocket):
    """WebSocket for freelancer outbound calls."""
    await websocket.accept()
    logger.info("freelancer_websocket_accepted")

    from freelancer.agent import FreelancerVoiceAgent

    agent = FreelancerVoiceAgent(
        twilio_ws=websocket,
        profile=_current_freelancer_profile,
    )

    try:
        await agent.run()
    except WebSocketDisconnect:
        logger.info("freelancer_websocket_disconnected")
    except Exception as e:
        logger.error("freelancer_websocket_error", error=str(e))
    finally:
        logger.info("freelancer_call_cleaned_up")


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
    print(f"\n🚀 Voice Agent Server Starting (Phase 2)")
    print(f"   Port: {config.port}")
    print(f"   Model: {config.bedrock_model_id}")
    print(f"   Tools: lookup_pricing, check_availability, book_appointment, search_knowledge, transfer_call")
    print(f"   Knowledge Base: {len(get_knowledge_base().documents)} documents")
    print(f"   Health: http://localhost:{config.port}/health")
    print(f"   Webhook: https://{config.server_host}/signalwire/inbound")
    print()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.port,
        log_level="info",
    )