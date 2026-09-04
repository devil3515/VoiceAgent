import { WS_BASE } from "./client";

export type VoicePersona = "clinic" | "freelancer";

/** Build the /ws/voice URL for a given persona (+ optional freelancer lead id). */
export function buildVoiceUrl(persona: VoicePersona, leadId?: string): string {
  const params = new URLSearchParams({ persona });
  if (leadId) params.set("lead_id", leadId);
  return `${WS_BASE}/ws/voice?${params.toString()}`;
}

export type VoiceClient = {
  ws: WebSocket;
  /** Send one 16 kHz linear16 mono PCM frame (ArrayBuffer / Int16Array.buffer). */
  sendAudioFrame: (pcm: ArrayBufferLike) => void;
  close: () => void;
};

/** Open the voice WebSocket. Caller is responsible for wiring ws.onmessage / onopen. */
export function connectVoiceWs(persona: VoicePersona, leadId?: string): VoiceClient {
  const ws = new WebSocket(buildVoiceUrl(persona, leadId));
  ws.binaryType = "arraybuffer";

  return {
    ws,
    sendAudioFrame: (pcm) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(pcm);
      }
    },
    close: () => ws.close(),
  };
}
