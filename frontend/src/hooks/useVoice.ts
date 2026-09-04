import { useCallback, useEffect, useRef, useState } from "react";
import { connectVoiceWs, type VoiceClient, type VoicePersona } from "@/api/voice";

const TARGET_SAMPLE_RATE = 16000;

export type TranscriptTurn = {
  id: number;
  role: "user" | "agent";
  text: string;
};

export type VoiceStatus =
  | "idle"
  | "connecting"
  | "listening"
  | "speaking"
  | "error"
  | "closed";

type UseVoiceOptions = {
  persona: VoicePersona;
  leadId?: string;
  /** Called when a transcript text frame arrives from the backend (JSON string). */
  onTranscript?: (turn: TranscriptTurn) => void;
};

/**
 * Bridges the browser mic + speakers to the backend /ws/voice endpoint.
 *
 * - Captures mic audio, resamples to 16 kHz, converts to Int16 linear16 PCM,
 *   and streams each frame over the binary WebSocket channel.
 * - Receives 16 kHz linear16 PCM frames from the agent and plays them.
 * - Surfaces a simple status + live VU level for UI feedback.
 */
export function useVoice({ persona, leadId, onTranscript }: UseVoiceOptions) {
  const [status, setStatus] = useState<VoiceStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [level, setLevel] = useState(0);

  const clientRef = useRef<VoiceClient | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const scriptNodeRef = useRef<ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  // No-op audio sink: the ScriptProcessorNode must be connected to *something*
  // to fire, but routing it to ctx.destination plays the mic back to the user,
  // which causes the browser's AGC to suppress the mic input — effectively
  // muting the caller. A MediaStreamAudioDestinationNode accepts the audio
  // into a stream we never read; onaudioprocess does the real work.
  const sinkNodeRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  const onTranscriptRef = useRef(onTranscript);
  const turnId = useRef(0);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  const playPcm = useCallback((pcm: Int16Array) => {
    const ctx = audioCtxRef.current;
    if (!ctx) return;
    const float = new Float32Array(pcm.length);
    for (let i = 0; i < pcm.length; i++) float[i] = pcm[i] / 32768;
    const buffer = ctx.createBuffer(1, float.length, TARGET_SAMPLE_RATE);
    buffer.copyToChannel(float, 0);
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(ctx.destination);
    src.start();
  }, []);

  const start = useCallback(async () => {
    setError(null);
    try {
      setStatus("connecting");

      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext;
      const ctx = new AudioCtx();
      audioCtxRef.current = ctx;
      if (ctx.state === "suspended") await ctx.resume();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      micStreamRef.current = stream;

      const client = connectVoiceWs(persona, leadId);
      clientRef.current = client;

      client.ws.onopen = () => setStatus("listening");
      client.ws.onclose = () => setStatus((s) => (s === "error" ? s : "closed"));
      client.ws.onerror = () => {
        setError("Voice connection error");
        setStatus("error");
      };
      client.ws.onmessage = (ev) => {
        if (typeof ev.data === "string") {
          // Text frames carry optional transcripts / control messages.
          try {
            const parsed = JSON.parse(ev.data) as {
              role?: "user" | "agent";
              text?: string;
            };
            if (parsed.text) {
              onTranscriptRef.current?.({
                id: ++turnId.current,
                role: parsed.role ?? "agent",
                text: parsed.text,
              });
            }
          } catch {
            /* ignore non-JSON control frames */
          }
          return;
        }
        // Binary frame: 16 kHz linear16 PCM from the agent.
        const pcm = new Int16Array(ev.data as ArrayBuffer);
        playPcm(pcm);
        setStatus("speaking");
        window.clearTimeout(speakingResetRef.current);
        speakingResetRef.current = window.setTimeout(
          () => setStatus((s) => (s === "speaking" ? "listening" : s)),
          400,
        );
      };

      // Resample mic frames to 16 kHz and send as linear16 Int16.
      const source = ctx.createMediaStreamSource(stream);
      sourceNodeRef.current = source;

      // We target 4096 frames per output buffer at 16 kHz (~256ms).
      const bufferSize = 4096;
      const processor = ctx.createScriptProcessor(bufferSize, 1, 1);
      scriptNodeRef.current = processor;

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        const ws = clientRef.current?.ws;
        if (ws && ws.readyState === WebSocket.OPEN) {
          client.sendAudioFrame(
            floatToLinear16(
              resample(input, ctx.sampleRate, TARGET_SAMPLE_RATE),
            ).buffer,
          );
        }
        // VU meter
        let sum = 0;
        for (let i = 0; i < input.length; i++) sum += input[i] * input[i];
        setLevel(Math.min(1, Math.sqrt(sum / input.length) * 3));
      };

      const sink = ctx.createMediaStreamDestination();
      sinkNodeRef.current = sink;
      source.connect(processor);
      processor.connect(sink);
    } catch (err) {
      const msg =
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone permission denied"
          : err instanceof Error
            ? err.message
            : "Failed to start voice session";
      setError(msg);
      setStatus("error");
    }
  }, [persona, leadId, playPcm]);

  const speakingResetRef = useRef<number | undefined>(undefined);

  const stop = useCallback(() => {
    try {
      scriptNodeRef.current?.disconnect();
      sourceNodeRef.current?.disconnect();
      sinkNodeRef.current?.disconnect();
      micStreamRef.current?.getTracks().forEach((t) => t.stop());
      clientRef.current?.close();
      audioCtxRef.current?.close();
    } catch {
      /* ignore */
    } finally {
      scriptNodeRef.current = null;
      sourceNodeRef.current = null;
      sinkNodeRef.current = null;
      micStreamRef.current = null;
      clientRef.current = null;
      audioCtxRef.current = null;
      setLevel(0);
      setStatus("idle");
    }
  }, []);

  // Clean up on unmount.
  useEffect(() => {
    return () => {
      try {
        scriptNodeRef.current?.disconnect();
        sourceNodeRef.current?.disconnect();
        sinkNodeRef.current?.disconnect();
        micStreamRef.current?.getTracks().forEach((t) => t.stop());
        clientRef.current?.close();
        audioCtxRef.current?.close();
      } catch {
        /* ignore */
      }
    };
  }, []);

  return { status, error, level, start, stop };
}

/** Linear resample a mono Float32 buffer to the target rate. */
function resample(
  input: Float32Array,
  fromRate: number,
  toRate: number,
): Float32Array {
  if (fromRate === toRate) return input;
  const ratio = fromRate / toRate;
  const newLen = Math.round(input.length / ratio);
  const out = new Float32Array(newLen);
  let pos = 0;
  for (let i = 0; i < newLen; i++) {
    const idx = i * ratio;
    const i0 = Math.floor(idx);
    const i1 = Math.min(i0 + 1, input.length - 1);
    const frac = idx - i0;
    out[i] = input[i0] * (1 - frac) + input[i1] * frac;
    pos = idx;
  }
  void pos;
  return out;
}

/** Convert a Float32 [-1,1] buffer to Int16 linear16 PCM. */
function floatToLinear16(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}
