"""
FastAPI server — entry point for the voice calling agent.

Phase 3: Local browser voice.
- No phone carrier (Twilio / SignalWire) required.
- Both agent personas (clinic + freelancer) run over a single WebSocket
  endpoint, /ws/voice, streaming 16 kHz linear16 PCM directly from/to the
  browser mic and speakers.
"""

import asyncio
import json
import uuid
from datetime import datetime
import os
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from agents.voice_agent import VoiceAgent
from config import config
from dashboard_bus import bus
from services.audio_transport import BrowserAudioTransport


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
    version="3.0.0",
    description="Local browser voice — no carrier required",
)

# CORS — open the dashboard frontend at http://localhost:5173.
# Local dev only; tighten allow_origins for any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_calls: dict[str, object] = {}


# ─────────────────────────────────────────────
# WEBSOCKET — LOCAL BROWSER VOICE (unified)
# ─────────────────────────────────────────────

@app.websocket("/ws/voice")
async def handle_voice_stream(websocket: WebSocket):
    """
    Unified local voice endpoint.

    Query params:
      - persona: "clinic" (default) | "freelancer"
      - lead_id: optional lead id (freelancer persona only)

    Audio contract: binary WebSocket frames carry 16 kHz linear16 mono PCM in
    both directions. Text frames are control/event metadata (JSON).
    """
    await websocket.accept()
    persona = (websocket.query_params.get("persona") or "clinic").lower()
    lead_id = websocket.query_params.get("lead_id")
    session_id = str(uuid.uuid4())

    transport = BrowserAudioTransport(websocket)
    agent = None

    try:
        if persona == "freelancer":
            from freelancer.agent import FreelancerVoiceAgent

            lead_info = None
            if lead_id:
                lead = get_lead_manager().get_lead(lead_id)
                if lead:
                    lead_info = lead.dict()

            agent = FreelancerVoiceAgent(
                transport=transport,
                profile=_current_freelancer_profile,
                lead_info=lead_info,
            )
        else:
            agent = VoiceAgent(transport=transport, session_id=session_id)

        active_calls[session_id] = agent
        bus.publish("call_started", session_id=session_id, persona=persona)

        logger.info("voice_ws_accepted", session_id=session_id, persona=persona)
        await agent.run()

    except WebSocketDisconnect:
        logger.info("voice_ws_disconnected", session_id=session_id)
    except Exception as e:
        logger.error(
            "voice_ws_error",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__,
        )
    finally:
        if session_id in active_calls:
            del active_calls[session_id]
        bus.publish("call_ended", session_id=session_id)
        logger.info("voice_ws_cleaned_up", session_id=session_id)


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
            "deepgram": bool(config.deepgram_api_key),
            "llm": bool(config.llm_base_url),
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
        "model": config.llm_model_id,
        "health": "/health",
        "voice_ws": "/ws/voice?persona=clinic",
        "knowledge_search": "/knowledge/search?q=your+query",
    }


# ─────────────────────────────────────────────
# DASHBOARD EVENT STREAM
# ─────────────────────────────────────────────

@app.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket):
    """Stream dashboard events (mirrored from structlog) to the SPA."""
    await websocket.accept()
    queue = bus.subscribe()
    logger.info("dashboard_ws_connected")
    try:
        # Send a hello so the client knows the connection is live.
        await websocket.send_text(
            json.dumps(
                {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "event": "_connected",
                    "level": "info",
                }
            )
        )
        while True:
            payload = await queue.get()
            await websocket.send_text(json.dumps(payload, default=str))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("dashboard_ws_error", error=str(e), error_type=type(e).__name__)
    finally:
        bus.unsubscribe(queue)
        logger.info("dashboard_ws_disconnected")


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


# NOTE: Freelancer calling is live-talk-only via /ws/voice?persona=freelancer.
# The legacy outbound-call + outbound-flow routes (which required a Twilio/
# SignalWire account) have been removed.


# ─────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(
        "server_starting",
        port=config.port,
        server_host=config.server_host,
        model=config.llm_model_id,
    )
    print(f"\n🚀 Voice Agent Server Starting (Phase 3 — Local Browser Voice)")
    print(f"   Port: {config.port}")
    print(f"   Model: {config.llm_model_id}")
    print(f"   Tools: lookup_pricing, check_availability, book_appointment, search_knowledge, transfer_call")
    print(f"   Knowledge Base: {len(get_knowledge_base().documents)} documents")
    print(f"   Health: http://localhost:{config.port}/health")
    print(f"   Voice WS: ws://localhost:{config.port}/ws/voice?persona=clinic")
    print()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.port,
        log_level="info",
    )