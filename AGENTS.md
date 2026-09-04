# AGENTS.md — Voice Calling Agent

This file is the entry point for any AI coding agent working in this repository. Read it before touching any code.

## Project overview

This is a real-time, bidirectional voice agent. It streams 16 kHz linear16 PCM audio directly between the browser (mic + speakers) and the server over a single WebSocket, runs a tool-calling LLM loop, and replies with synthesized speech. **No phone carrier (Twilio / SignalWire) is required** — the original outbound-call routes and Twilio/SignalWire dependencies have been removed.

Two agent personas are wired up in the same server:

1. **`VoiceAgent` (clinic / Acme Corp persona)** — handles customer-care voice sessions. Speaks as "Alex". Uses five tools: `lookup_pricing`, `check_availability`, `book_appointment`, `search_knowledge`, `transfer_call`.
2. **`FreelancerVoiceAgent` (freelancer persona)** — live-talk sessions on behalf of a freelancer (default: a generic "John Doe" full-stack developer). Uses seven tools: `get_service_info`, `get_rates`, `book_consultation`, `share_portfolio`, `send_followup_email`, `transfer_to_freelancer`, `end_call`. Sources all facts from a `FreelancerProfile` Pydantic model — it never invents details.

The runtime is a single FastAPI app. The pipeline per session is:

```
Browser WebSocket (/ws/voice)  →  Deepgram (STT)  →  LLM (OpenAI-compatible, e.g. OpenRouter)
                                                  ↓ optional tool execution loop
                              Cartesia (TTS)  →  Browser WebSocket (/ws/voice)
```

Audio transport is abstracted behind `services/audio_transport.py` (`AudioTransport` + `BrowserAudioTransport`), so a future carrier backend can be dropped in without touching the agents. A React dashboard (in `frontend/`) provides the mic capture, playback, transcript, and an animated talk screen at `/talk`.

Auxiliary subsystems: a Redis-backed `SessionManager` (with in-memory fallback), an in-process keyword `KnowledgeBase` (8 default Acme Corp docs), a singleton `LeadManager` for freelancer leads, and a `tools/email_followup.py` that currently only logs the email body to stdout.

## Build and test commands

- **Install dependencies** (Python 3.13 venv already at `venv/`):
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```
- **Run the server**:
  ```bash
  python main.py
  # or equivalently:
  uvicorn main:app --host 0.0.0.0 --port 8000
  ```
  On startup, the server validates config, loads the knowledge base singleton, and prints the bound model, port, and voice WS URL. The default `SERVER_HOST` is `localhost:8000`.
- **Open the talk UI**: run the dashboard dev server (see `frontend/`) and visit `http://localhost:5173/talk?persona=clinic` (or `?persona=freelancer&lead_id=<id>`). The page captures mic audio, streams it to `/ws/voice?persona=…`, plays the agent's PCM replies, and shows a live transcript.
- **Smoke-test the service integrations** (config, audio conversion, Deepgram, the LLM both streaming and non-streaming, Cartesia, full STT→LLM→TTS pipeline):
  ```bash
  python -m tests.test_services
  ```
  This is the only automated test suite in the repo (`tests/test_services.py`). It exits non-zero if any test fails and prints a `📋 TEST SUMMARY` table at the end. Each sub-test is also importable as a coroutine for use in a custom runner.
- **Initiate a clinic voice session** (programmatically — normally the browser does this):
  ```bash
  # WS client connects to:
  ws://localhost:8000/ws/voice?persona=clinic
  ```
  For a freelancer lead, append `&lead_id=<lead_id>` (the lead id is returned by `POST /freelancer/leads`).

## Environment / configuration

All settings live in `.env` (template in `.env.example`) and are read by `config.py` into a single `Config` instance (`config = Config()`). Required keys (validated by `Config.validate()`):

- `DEEPGRAM_API_KEY`
- `BEDROCK_BASE_URL`, `BEDROCK_API_KEY`, `BEDROCK_MODEL_ID` (default `anthropic.claude-3-haiku-20240307-v1:0`; aliases in `Config.AVAILABLE_MODELS`: `haiku`, `sonnet`, `llama-70b`, `llama-8b`, `mistral`)
- `CARTESIA_API_KEY`, `CARTESIA_VOICE_ID`
- `REDIS_URL` (default `redis://localhost:6379/0`) — optional, falls back to in-process dict
- `SERVER_HOST`, `PORT` (default `8000`), `LOG_LEVEL`
- `MAX_TOOL_CALLS_PER_TURN` (default `5`), `KNOWLEDGE_BASE_PATH` (default `./knowledge.json`)

If a key is missing the server still starts but logs `config_missing_keys` at WARNING and `/health` reports the missing capability as `false`.

## Code organization

```
VoiceAgent/
├── main.py                 FastAPI app: Twilio/SignalWire webhooks, WS, REST API
├── config.py               Single Config class, reads env via python-dotenv
├── requirements.txt
├── .env.example            Template — never commit a real .env
├── testing.py              Unrelated micro snippet (sys.getrefcount), leave alone
│
├── agents/                 Pipeline orchestration
│   ├── voice_agent.py      VoiceAgent (clinic persona), owns STT/LLM/TTS, tool loop
│   ├── conversation.py     ConversationManager — OpenAI message list, tool-call history
│   ├── prompts.py          SYSTEM_PROMPT, GREETING_TEXT, CLARIFICATION_TEXTS
│   └── tools.py            TOOL_DEFINITIONS (OpenAI format) + execute_tool() router
│
├── freelancer/             Second persona: outbound freelancer calls
│   ├── agent.py            FreelancerVoiceAgent — same pipeline, different prompt/tools
│   ├── profile.py          FreelancerProfile + Service Pydantic models; get_default_profile()
│   ├── prompts.py          build_freelancer_prompt(profile), GREETING_TEMPLATE, WRAP_UP
│   └── tools.py            7 freelancer tool defs + a profile-bound tool map (closures)
│
├── leads/                  Lead management
│   └── manager.py          Lead Pydantic model + LeadManager singleton (in-memory)
│
├── memory/                 Per-call session state
│   └── session.py          SessionManager — Redis with in-memory fallback (1h TTL)
│
├── rag/                    Knowledge base (Phase 2: keyword; Phase 5: vector)
│   └── knowledge_base.py   KnowledgeBase, DEFAULT_DOCUMENTS, get_knowledge_base() singleton
│
├── services/               One file per external service
│   ├── deepgram_stt.py     DeepgramClient.listen.asynclive, Nova-2 model
│   ├── llm.py              LLMService — AsyncOpenAI pointed at any OpenAI-compatible endpoint; LLMResponse/ToolCall dataclasses
│   ├── cartesia_tts.py     httpx POST to /tts/bytes (and /tts/sse for streaming)
│   ├── google_calander.py  Google Calendar service factory (token.json on disk)
│   └── audio_utils.py      mulaw ↔ linear16, base64 helpers, chunk_audio
│
├── tools/                  Tool implementations (one async fn per tool)
│   ├── pricing.py          lookup_pricing — in-memory PRICING_DATA dict
│   ├── appointments.py     check_availability, book_appointment — in-memory _booked_slots
│   ├── knowledge.py        search_knowledge — wraps KnowledgeBase
│   ├── transfer.py         transfer_call — logs and returns "TRANSFER_REQUESTED: …"
│   ├── freelancer_services.py  get_service_info, get_rates (profile-bound)
│   ├── consultation_booking.py book_consultation (profile-bound)
│   ├── portfolio.py        share_portfolio (profile-bound)
│   └── email_followup.py   send_followup_email — currently prints to stdout
│
├── utils/
│   └── logging.py          structlog JSON logger; setup_logging() at startup
│
└── tests/
    └── test_services.py    Integration smoke tests, run with `python -m tests.test_services`
```

### Module conventions

- Every Python file begins with a `"""…"""` module docstring describing its role and (for the agent/prompts/services files) which phase of the project it belongs to. Match this style for new files.
- `__init__.py` files re-export the public surface (`VoiceAgent`, `ConversationManager`, the three services) using `__all__`. New top-level modules should follow the same pattern.
- Section dividers inside long files use the `─` Unicode character (e.g. `# ─── TWILIO WEBHOOKS ───`). Preserve them.
- All async work is `asyncio` + `async/await`; no thread pools, no sync I/O in the hot path. The LLM client is `AsyncOpenAI`; TTS uses `httpx.AsyncClient`; STT uses `deepgram-sdk` 3.7's `asynclive`.
- Configuration is **always** read from `config.config`; never call `os.getenv` inside a service/tool module.
- Logging: `from utils.logging import get_logger; logger = get_logger(__name__)` then `logger.info("event_name", key=value, …)`. Use snake_case event names. No `print` in production code except the one in `tools/email_followup.py` that prints the email body.
- Tools are `async` functions that accept named arguments matching their OpenAI `parameters` schema and return a `str`. `transfer_call` returns `"TRANSFER_REQUESTED: …"`; the freelancer `end_call` returns `"CALL_END: …"`. Both sentinels are detected by the agent's tool loop in `voice_agent.py` / `freelancer/agent.py`.
- Tool definitions live in OpenAI function-calling format in `agents/tools.py` (clinic) and `freelancer/tools.py` (freelancer). To add a new tool: write the async impl in `tools/`, append its definition to the appropriate list, add the impl to the `TOOL_MAP` / `get_freelancer_tool_map` dictionary, and (if it has new behavior) update the system prompt.

### HTTP / WS surface (all in `main.py`)

| Method | Path                                  | Purpose                                   |
|--------|---------------------------------------|-------------------------------------------|
| WS     | `/ws/voice?persona=clinic`            | Clinic agent stream (browser mic/speakers)|
| WS     | `/ws/voice?persona=freelancer[&lead_id=…]` | Freelancer agent stream (optional lead) |
| WS     | `/ws/dashboard`                       | Real-time bus events for the React dashboard |
| GET    | `/health`                             | Liveness + capability flags               |
| GET    | `/knowledge/search?q=…`               | KB test endpoint                          |
| GET    | `/knowledge/stats`                    | KB doc/index counts                       |
| GET/POST | `/freelancer/profile`               | Read/update the in-process profile        |
| POST   | `/freelancer/leads`                   | Add a `Lead`                              |
| GET    | `/freelancer/leads`                   | List all leads                            |

## Code style guidelines

- Python 3.13, target the existing import style (`from __future__` is not used).
- Type hints everywhere on public functions; `Optional[T]` for nullable args, Pydantic `BaseModel` for any structured data crossing module boundaries (already the case for `Lead`, `FreelancerProfile`, `Service`, `LLMResponse`, `ToolCall`).
- LLM-bound strings must be 1–2 sentences, no bullet points, no "I'm an AI". This is hard-coded in `agents/prompts.py::SYSTEM_PROMPT` and `freelancer/prompts.py::build_freelancer_prompt`. If you change prompt text, also update the matching "Example bad responses" section so the LLM does not regress.
- Latency-sensitive code uses `asyncio.create_task` for fire-and-forget turns (see `_on_transcript` in `agents/voice_agent.py`). The `is_processing` flag guards against overlapping LLM calls.
- Audio is 16 kHz linear16 PCM end-to-end: the browser resamples mic audio to 16 kHz Int16 before sending and receives 16 kHz Int16 frames to play. The carrier-counting helpers in `services/audio_utils.py` (`twilio_to_deepgram`, `linear16_to_mulaw`, `chunk_audio`, `encode_twilio_payload`) are now legacy/dead and only kept because `tests/test_services.py` exercises them — do not add new callers. New code talks to the `AudioTransport` interface in `services/audio_transport.py`.

## Testing instructions

There is no `pytest` setup. The canonical pre-flight before any change is:

```bash
source venv/bin/activate
python -m tests.test_services
```

This is the integration test — it really hits Deepgram, the configured LLM endpoint, and Cartesia, so it needs a populated `.env` and will incur API cost. If you add a new service, add a `test_<name>` coroutine to `tests/test_services.py` and wire it into `main()`.

For unit-only logic (tool implementations, conversation trimming, profile rendering), prefer calling the function directly from a short script over adding to `test_services.py`.

## Security considerations

- **Never commit `.env`.** The `.gitignore` already excludes it; the only safe-to-commit env file is `.env.example`. Real credentials are present in the local `.env` (Deepgram, the LLM provider, Cartesia). Treat any value you read from `config.*` as a secret.
- The LLM API is consumed via the OpenAI SDK with a custom `base_url` (`config.llm_base_url`). Do not log the API key or full `base_url` query string; the existing `llm_initialized` log event intentionally logs `base_url` but never `api_key`.
- `services/google_calander.py` reads OAuth credentials from a local `token.json` (not in the repo). If you wire it up, do not commit the resulting token.
- The `/ws/voice` socket is unauthenticated in this repo and accepts any browser client. Any deployment that hosts it publicly must add auth (a signed token / session cookie, or reverse-proxy auth) before exposing it.
- `SessionManager` stores call data in Redis with a 1 h TTL. PII (caller name/email from `book_appointment`, `book_consultation`) flows through it. Don't disable the `decode_responses=True` and `json.dumps`/loads round-trip; it's there to keep Redis values as strings.
- `tools/email_followup.py` currently only prints the email to stdout. When you wire it to a real provider (SendGrid/SES/SMTP), sanitize the body to avoid header injection through the `name` / `email` fields.
