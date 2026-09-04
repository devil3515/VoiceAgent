import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, MicOff, Stethoscope, User, AlertCircle } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SegmentedTabs } from "@/components/ui/SegmentedTabs";
import { GradientMesh } from "@/components/effects/GradientMesh";
import { PulseDot } from "@/components/effects/PulseDot";
import { fadeUp, stagger } from "@/lib/motion";
import { useVoice, type TranscriptTurn } from "@/hooks/useVoice";
import { fetchLeads, type Lead } from "@/api/leads";
import { useQuery } from "@tanstack/react-query";
import type { VoicePersona } from "@/api/voice";

const personas: { id: VoicePersona; label: string; icon: typeof Stethoscope; blurb: string }[] = [
  { id: "clinic", label: "Clinic (Acme)", icon: Stethoscope, blurb: "The Acme Corp reception agent" },
  { id: "freelancer", label: "Freelancer", icon: User, blurb: "Outbound agent for your leads" },
];

export function Talk() {
  const [searchParams] = useSearchParams();
  const initialPersona = (searchParams.get("persona") as VoicePersona) || "clinic";
  const initialLead = searchParams.get("lead_id") ?? "";

  const [persona, setPersona] = useState<VoicePersona>(
    initialPersona === "freelancer" ? "freelancer" : "clinic",
  );
  const [leadId, setLeadId] = useState<string>(initialLead);
  const [transcript, setTranscript] = useState<TranscriptTurn[]>([]);

  const { status, error, level, start, stop } = useVoice({
    persona,
    leadId: persona === "freelancer" ? leadId || undefined : undefined,
    onTranscript: (turn) => setTranscript((prev) => [...prev, turn].slice(-50)),
  });

  const { data: leadsData } = useQuery({
    queryKey: ["leads", "talk"],
    queryFn: ({ signal }) => fetchLeads(signal),
    enabled: persona === "freelancer",
  });
  const leads: Lead[] = leadsData?.leads ?? [];
  const selectedLead = leads.find((l) => l.lead_id === leadId) ?? null;

  const live = status === "listening" || status === "speaking";

  const statusMeta = useMemo(() => {
    switch (status) {
      case "connecting":
        return { label: "Connecting…", tone: "warn" as const };
      case "listening":
        return { label: "Listening", tone: "good" as const };
      case "speaking":
        return { label: "Agent speaking", tone: "accent" as const };
      case "error":
        return { label: "Error", tone: "bad" as const };
      case "closed":
        return { label: "Disconnected", tone: "neutral" as const };
      default:
        return { label: "Idle", tone: "neutral" as const };
    }
  }, [status]);

  return (
    <motion.div initial="hidden" animate="show" variants={stagger(0.05)} className="mx-auto max-w-4xl">
      <motion.div variants={fadeUp} className="mb-6">
        <p className="text-xs uppercase tracking-widest text-text-2">Talk</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-tight">
          Talk to your agent
        </h2>
        <p className="mt-1 text-sm text-text-1">
          Speak directly through your browser. Audio streams over a local
          WebSocket — no phone number required.
        </p>
      </motion.div>

      <motion.div variants={fadeUp}>
        <Card glow className="relative overflow-hidden">
          <GradientMesh className="opacity-70" />

          <div className="relative space-y-6">
            {/* Persona switcher */}
            <SegmentedTabs
              value={persona}
              onChange={(v) => setPersona(v as VoicePersona)}
              disabled={live}
              ariaLabel="Persona"
              tabs={personas.map((p) => ({
                id: p.id,
                label: p.label,
                icon: p.icon,
              }))}
            />

            {/* Lead picker (freelancer only) */}
            <AnimatePresence>
              {persona === "freelancer" && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <label
                    htmlFor="lead"
                    className="mb-1.5 block text-xs font-medium text-text-1"
                  >
                    Lead to talk about
                  </label>
                  <select
                    id="lead"
                    value={leadId}
                    onChange={(e) => setLeadId(e.target.value)}
                    disabled={live}
                    className="w-full rounded-lg border border-border bg-bg-2 px-3 py-2 text-sm text-text-0 outline-none focus:border-accent/70 focus:ring-2 focus:ring-accent/30 disabled:opacity-60"
                  >
                    <option value="">General (no lead)</option>
                    {leads.map((l) => (
                      <option key={l.lead_id ?? l.name} value={l.lead_id ?? ""}>
                        {l.name} — {l.company ?? l.phone}
                      </option>
                    ))}
                  </select>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Visualizer + status */}
            <div className="flex flex-col items-center gap-5 py-2">
              <VoiceOrb status={status} level={level} />
              <div className="flex items-center gap-2">
                <PulseDot
                  active={live || status === "connecting"}
                  tone={statusMeta.tone === "neutral" ? "accent" : statusMeta.tone}
                  size={10}
                />
                <span className="text-sm text-text-1">{statusMeta.label}</span>
                {selectedLead && (
                  <Badge tone="accent">{selectedLead.name}</Badge>
                )}
              </div>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center justify-center gap-3">
              {!live ? (
                <Button
                  size="lg"
                  onClick={start}
                  loading={status === "connecting"}
                  iconLeft={<Mic className="h-4 w-4" />}
                >
                  {status === "closed" || status === "error" ? "Reconnect" : "Start talking"}
                </Button>
              ) : (
                <Button
                  size="lg"
                  variant="danger"
                  onClick={stop}
                  iconLeft={<MicOff className="h-4 w-4" />}
                >
                  Stop
                </Button>
              )}
              <span className="text-xs text-text-2">
                {live ? "Press to end the call" : `Streams over /ws/voice?persona=${persona}`}
              </span>
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-md border border-bad/30 bg-bad/10 px-3 py-2 text-sm text-bad">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {error}
              </div>
            )}
          </div>
        </Card>
      </motion.div>

      {/* Transcript */}
      <motion.div variants={fadeUp} className="mt-6">
        <Card>
          <CardHeader
            title="Conversation"
            subtitle="Live transcript"
            right={
              <button
                type="button"
                onClick={() => setTranscript([])}
                className="text-[11px] text-text-2 hover:text-text-0"
              >
                clear
              </button>
            }
          />
          <div className="h-[280px] overflow-y-auto rounded-md border border-border bg-bg-0/60 p-3 text-sm">
            {transcript.length === 0 ? (
              <div className="flex h-full items-center justify-center text-text-2">
                Start talking to see the transcript…
              </div>
            ) : (
              <ul className="space-y-2">
                <AnimatePresence initial={false}>
                  {transcript.map((t) => (
                    <motion.li
                      key={t.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex ${t.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-3 py-2 ${
                          t.role === "user"
                            ? "bg-accent/20 text-text-0"
                            : "bg-bg-2 text-text-1"
                        }`}
                      >
                        <span className="mb-0.5 block text-[10px] uppercase tracking-wide text-text-2">
                          {t.role}
                        </span>
                        {t.text}
                      </div>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ul>
            )}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  );
}

/** Animated central orb that pulses with the mic level. */
function VoiceOrb({ status, level }: { status: string; level: number }) {
  const active = status === "listening" || status === "speaking";
  const speaking = status === "speaking";
  const scale = 1 + (active ? level * 0.35 : 0);

  const color = speaking
    ? "radial-gradient(circle at 30% 30%, rgba(124,92,255,0.55), rgba(61,220,236,0.15))"
    : active
      ? "radial-gradient(circle at 30% 30%, rgba(52,211,153,0.5), rgba(124,92,255,0.12))"
      : "radial-gradient(circle at 30% 30%, rgba(80,86,120,0.4), rgba(40,44,68,0.12))";

  return (
    <motion.div
      className="relative flex h-44 w-44 items-center justify-center rounded-full"
      animate={{ scale }}
      transition={{ type: "spring", stiffness: 200, damping: 18 }}
      style={{ background: color, boxShadow: active ? "0 0 60px -10px rgba(124,92,255,0.5)" : "none" }}
    >
      {active && (
        <>
          <motion.span
            className="absolute inset-0 rounded-full border border-accent/40"
            animate={{ scale: [1, 1.4], opacity: [0.6, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut" }}
          />
          <motion.span
            className="absolute inset-0 rounded-full border border-accent/30"
            animate={{ scale: [1, 1.7], opacity: [0.4, 0] }}
            transition={{ duration: 1.6, repeat: Infinity, ease: "easeOut", delay: 0.8 }}
          />
        </>
      )}
      <span className="relative z-10 text-text-0">
        {speaking ? (
          <Mic className="h-10 w-10 text-white/90" />
        ) : active ? (
          <Mic className="h-10 w-10 text-white/90" />
        ) : (
          <MicOff className="h-9 w-9 text-text-2" />
        )}
      </span>
    </motion.div>
  );
}
