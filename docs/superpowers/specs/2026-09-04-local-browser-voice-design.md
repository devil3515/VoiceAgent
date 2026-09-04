# Design: Local Browser Voice (remove Twilio/SignalWire)

**Date:** 2026-09-04
**Status:** For review

## Goal

Remove all Twilio and SignalWire dependencies from the project and let the user
talk to both agent personas (clinic / Acme, and freelancer) directly through the
browser microphone and speakers — running the full pipeline locally with no phone
carrier.

The real pipeline is **unchanged**:

```
Mic → Deepgram (STT) → Bedrock Mantle (LLM, tools) → Cartesia (TTS) → Speakers
```

Twilio/SignalWire was only the audio carrier (8 kHz mulaw over a WebSocket). It is
replaced by a browser WebSocket that streams 16 kHz linear16 PCM in both
directions.

## Decisions (locked via clarifying questions)

1. **Scope** — Keep cloud STT/TTS/LLM. Remove only Twilio + SignalWire.
2. **Personas** — Support both clinic and freelancer from one shared WS.
3. **Architecture** — Unified WebSocket (`/ws/voice`) + full removal of carriers.
4. **Freelancer call** — Live talk only; remove `/freelancer/call/{lead_id}`.
5. **Outbound page** — Repurpose `/outbound` into a launchpad for `/talk`.

## Architecture

### New: `services/audio_transport.py`

A transport-agnostic interface so the agents never know whether audio comes from
Twilio or the browser.

```python
class AudioTransport(Protocol):
    async def receive(self) -> Optional[bytes]: ...   # 16k linear16 PCM frame
    async def send(self, pcm_16k: bytes) -> None: ...  # agent TTS audio
    def is_open(self) -> bool: ...
```

- `BrowserAudioTransport` — wraps a `fastapi.WebSocket`. Browser sends raw PCM
  `ArrayBuffer` frames (binary); backend sends PCM frames back the same way.
  No mulaw, no base64, no TwiML.
- Helper `close()` and a `receive_loop` generator if needed.

`audio_utils.py` (mulaw helpers) is left in place — still used by
`tests/test_services.py`. It becomes dead code on the live path but is not churned.

### Backend: `WS /ws/voice` (replaces `/ws/call` + `/ws/freelancer-call`)

Single endpoint:

- `ws/voice?persona=clinic`
- `ws/voice?persona=freelancer&lead_id=<id>`

On connect:
- `persona == "clinic"` → `VoiceAgent(transport=BrowserAudioTransport(ws))`
- `persona == "freelancer"` → `FreelancerVoiceAgent(transport=..., profile, lead_info)`
- Register in `active_calls` under a generated session id (no `call_sid`).
- Publish `call_ended` to the dashboard bus on disconnect, like today.

### Agent refactor (`agents/voice_agent.py`, `freelancer/agent.py`)

- `__init__` takes `transport: AudioTransport` instead of `twilio_ws`.
- Replace the `async for raw_message in self.twilio_ws.iter_text(): ... _handle_twilio_event()`
  loop with `async for pcm in self.transport.receive_loop(): self._process_incoming_audio(pcm)`.
- `_process_incoming_audio(pcm_bytes)` feeds Deepgram directly (pcm is already
  16k linear16 — drop the `twilio_to_deepgram` conversion).
- `_send_audio_to_twilio(pcm_16k)` → `_send_audio(pcm_16k)` → `transport.send(pcm_16k)`
  (drop `linear16_to_mulaw` / `chunk_audio` / `encode_twilio_payload`).
- Greeting, `_process_turn`, tool loop, `SessionManager`, freelancer follow-up
  email — all unchanged.

### Removed entirely

- `main.py` routes: `/twilio/inbound`, `/twilio/outbound`, `/twilio/outbound-flow`,
  `/signalwire/*`, `/freelancer/outbound-flow`, `/freelancer/call/{lead_id}`,
  `WS /ws/call`, `WS /ws/freelancer-call`.
- `config.get_twilio_client()`, `get_signalwire_client()`.
- `config` fields: `twilio_*`, `signalwire_*`.
- `requirements.txt`: remove `twilio>=8.0.0`.
- `Config.validate()`: stop requiring Twilio keys; require only
  `DEEPGRAM_API_KEY`, `BEDROCK_*` (base_url, api_key, model_id),
  `CARTESIA_*` (api_key, voice_id). `/health` drops the `twilio` flag.

### Kept / still works

- Both personas' prompts, all tools, knowledge base, session memory.
- `GET /freelancer/profile`, `GET/POST /freelancer/profile`,
  `GET/POST /freelancer/leads` (load a lead's context into a talk session).
- `/health`, `/knowledge/search`, `/knowledge/stats`, `WS /ws/dashboard`.

## Frontend changes

Stack: Vite + React 19 + TypeScript + Tailwind v4 + framer-motion 12 +
lucide-react + @tanstack/react-query (already installed).

### New page: `/talk` (`frontend/src/pages/Talk.tsx`)

- Persona switch: Clinic (Acme) / Freelancer, reusing existing tab-pill pattern.
- Freelancer mode shows a lead dropdown (fetches `/freelancer/leads`).
- Mic Start/Stop control (getUserMedia), live transcript panel (user + agent turns
  streamed over the WS text channel), waveform / VU meter reusing `GradientMesh`,
  `PulseDot`, `AnimatedNumber` effects + framer-motion.
- Audio plumbing: `AudioWorklet` (or ScriptProcessor fallback) resamples mic to
  16 kHz mono `Int16` PCM, sends `ArrayBuffer` frames; incoming PCM →
  `AudioContext.decodeAudioData` → speakers.

### New API module: `api/voice.ts`

- `connectVoiceWs(persona, leadId?)` → opens `WS_BASE + /ws/voice?...`, returns a
  typed wrapper exposing `sendAudioFrame(ArrayBuffer)`, `onAgentAudio(cb)`,
  `onTranscript(cb)`, `close()`. Text frames carry transcript/event metadata;
  binary frames carry PCM.

### Updates

- `App.tsx`: add route `/talk` → `Talk`; keep `/outbound`.
- `OutboundCall.tsx`: Clinic tab → button linking to `/talk`. Freelancer tab →
  list leads with a "Talk to lead" button → `/talk?lead=<id>`. Remove the phone
  number form + `startClinicCall` usage.
- `api/calls.ts`: delete `startClinicCall` (no more `/twilio/outbound`).
- `api/health.ts`: `HealthConfig` drops `twilio`.
- `pages/Dashboard.tsx`: integrations list drops the Twilio pill; "Calls today"
  counts remain based on event log. (No Twilio-specific events will be emitted.)
- `lib/format.ts` `short_sid` usages in OutboundCall can be dropped.

### `.env.example`

Remove the `# ─── Twilio ───` block (`TWILIO_ACCOUNT_SID/AUTH_TOKEN/PHONE_NUMBER`).

### `AGENTS.md`

Update overview, HTTP/WS surface table, config section, and the "Audio is always
8 kHz mulaw on the Twilio side" note. Reflect the new `/ws/voice` contract and
that audio is now 16 kHz linear16 end-to-end via the browser.

## Verification

- `source venv/bin/activate && python main.py` starts with **no** Twilio keys set;
  `/health` shows `status: healthy`, only `deepgram/bedrock/cartesia` config flags.
- `python -m tests.test_services` still passes (audio_utils mulaw tests intact).
- Manual: open `localhost:5173/talk`, pick a persona, grant mic, speak → agent
  transcribes, runs tools, speaks back via Cartesia. Freelancer mode with a lead
  loads that lead's context and still sends a follow-up email on end.
- Confirm no remaining references: grep for `twilio|signalwire` returns only the
  kept `audio_utils.py` dead-code helpers and any test that explicitly names them.

## Out of scope

- WebRTC (raw WS chosen; lighter for a local tool).
- Keeping Twilio as an optional provider (fully removed).
- Auth on `/ws/voice` (local dev only, same as current unauthenticated endpoints).
