import { useMemo } from "react";
import { motion } from "framer-motion";
import { Phone, BookOpen, Users, Activity, Plug, Wrench } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { AnimatedNumber } from "@/components/effects/AnimatedNumber";
import { PulseDot } from "@/components/effects/PulseDot";
import { GradientMesh } from "@/components/effects/GradientMesh";
import { useHealth } from "@/hooks/useHealth";
import { useEventStream } from "@/hooks/useEventStream";
import { fetchLeads } from "@/api/leads";
import { useQuery } from "@tanstack/react-query";
import { formatTime, timeAgo } from "@/lib/format";
import { fadeUp, stagger } from "@/lib/motion";

const integrationItems: Array<{
  key: keyof import("@/api/health").HealthConfig;
  label: string;
}> = [
  { key: "deepgram", label: "Deepgram" },
  { key: "bedrock", label: "Bedrock" },
  { key: "cartesia", label: "Cartesia" },
];

export function Dashboard() {
  const { data: health, isLoading, isError } = useHealth();
  const { events, status } = useEventStream();
  const { data: leadsData } = useQuery({
    queryKey: ["leads", "count"],
    queryFn: ({ signal }) => fetchLeads(signal),
    refetchInterval: 30_000,
  });

  const leadsCount = leadsData?.leads.length ?? 0;
  const callsToday = useMemo(() => {
    const today = new Date().toDateString();
    return events.filter(
      (e) =>
        (e.event === "outbound_call_initiated" ||
          e.event === "freelancer_outbound_call") &&
        new Date(e.ts).toDateString() === today,
    ).length;
  }, [events]);

  return (
    <motion.div initial="hidden" animate="show" variants={stagger(0.05)}>
      {/* Hero */}
      <motion.div variants={fadeUp} className="mb-6">
        <Card glow className="relative overflow-hidden">
          <GradientMesh className="opacity-90" />
          <div className="relative">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-widest text-text-2">
                  Voice Agent · Control Panel
                </p>
                <h2 className="mt-1 text-2xl font-semibold tracking-tight text-text-0 md:text-3xl">
                  Everything's <span className="text-gradient">wired up</span>
                  {isLoading ? null : isError ? (
                    <span className="ml-2 text-bad">(API down)</span>
                  ) : (
                    <span className="ml-2 text-text-2">— quiet for now</span>
                  )}
                </h2>
                <p className="mt-2 max-w-xl text-sm text-text-1">
                  Trigger outbound calls, edit the freelancer profile, and watch
                  the agent's live event stream. The backend is on{" "}
                  <code className="rounded bg-bg-2 px-1.5 py-0.5 text-text-0">
                    localhost:8000
                  </code>
                  .
                </p>
              </div>
              <div className="flex items-center gap-2">
                <PulseDot
                  active={status === "open"}
                  tone={status === "open" ? "good" : "warn"}
                  size={10}
                />
                <span className="text-sm text-text-1">
                  {status === "open" ? "Streaming live events" : status}
                </span>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Kpi
                icon={<Phone className="h-4 w-4" />}
                label="Active calls"
                value={health?.active_calls ?? 0}
                tone="accent"
                pulse={(health?.active_calls ?? 0) > 0}
              />
              <Kpi
                icon={<Phone className="h-4 w-4" />}
                label="Calls today"
                value={callsToday}
                tone="good"
              />
              <Kpi
                icon={<Users className="h-4 w-4" />}
                label="Leads"
                value={leadsCount}
              />
              <Kpi
                icon={<BookOpen className="h-4 w-4" />}
                label="KB docs"
                value={health?.knowledge_base.num_documents ?? 0}
              />
            </div>
          </div>
        </Card>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Service status */}
        <motion.div variants={fadeUp} className="lg:col-span-1">
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Plug className="h-4 w-4 text-text-2" />
                  Integrations
                </span>
              }
              subtitle="Configured credentials detected on the backend"
            />
            {isLoading ? (
              <div className="space-y-2">
                {integrationItems.map((i) => (
                  <div
                    key={i.key}
                    className="h-10 animate-pulse rounded-md bg-bg-2"
                  />
                ))}
              </div>
            ) : (
              <ul className="space-y-2">
                {integrationItems.map((i) => {
                  const ok = health?.config[i.key];
                  return (
                    <li
                      key={i.key}
                      className="flex items-center justify-between rounded-md border border-border bg-bg-2 px-3 py-2"
                    >
                      <span className="text-sm text-text-0">{i.label}</span>
                      <Badge tone={ok ? "good" : "bad"}>
                        <PulseDot
                          active={!!ok}
                          tone={ok ? "good" : "bad"}
                          size={6}
                        />
                        {ok ? "ready" : "missing"}
                      </Badge>
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>
        </motion.div>

        {/* Tools */}
        <motion.div variants={fadeUp} className="lg:col-span-1">
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Wrench className="h-4 w-4 text-text-2" />
                  Clinic tools
                </span>
              }
              subtitle="Available to the Acme Corp agent"
            />
            <ul className="flex flex-wrap gap-1.5">
              {(health?.tools ?? []).map((t) => (
                <li key={t}>
                  <code className="rounded-md border border-border bg-bg-2 px-2 py-1 text-[11px] text-text-1">
                    {t}
                  </code>
                </li>
              ))}
              {!isLoading && (health?.tools ?? []).length === 0 && (
                <li className="text-xs text-text-2">none reported</li>
              )}
            </ul>
          </Card>
        </motion.div>

        {/* System health summary */}
        <motion.div variants={fadeUp} className="lg:col-span-1">
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Activity className="h-4 w-4 text-text-2" />
                  System
                </span>
              }
              subtitle="Polled from /health every 5s"
            />
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-text-2">
                  Status
                </dt>
                <dd className="mt-0.5">
                  <Badge
                    tone={
                      isError
                        ? "bad"
                        : health?.status === "healthy"
                          ? "good"
                          : "warn"
                    }
                  >
                    {isError ? "down" : health?.status ?? "—"}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-text-2">
                  Phase
                </dt>
                <dd className="mt-0.5 text-text-0">
                  {health?.phase ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-text-2">
                  Active calls
                </dt>
                <dd className="mt-0.5 text-text-0">
                  {health?.active_calls ?? 0}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-text-2">
                  KB size
                </dt>
                <dd className="mt-0.5 text-text-0">
                  {health?.knowledge_base.num_documents ?? 0} docs
                </dd>
              </div>
            </dl>
          </Card>
        </motion.div>
      </div>

      {/* Event log */}
      <motion.div variants={fadeUp} className="mt-6">
        <Card>
          <CardHeader
            title="Live event log"
            subtitle={`Last ${events.length} events from the backend`}
            right={
              <span className="text-[11px] text-text-2">
                stream: /ws/dashboard
              </span>
            }
          />
          <div className="h-[320px] overflow-y-auto rounded-md border border-border bg-bg-0/60 font-mono text-[12px] leading-relaxed">
            {events.length === 0 ? (
              <div className="flex h-full items-center justify-center text-text-2">
                Waiting for events…
              </div>
            ) : (
              <ul className="divide-y divide-border/60">
                {events
                  .slice()
                  .reverse()
                  .map((e, i) => (
                    <li
                      key={`${e.ts}-${i}`}
                      className="flex items-center gap-3 px-3 py-1.5"
                    >
                      <span className="w-20 shrink-0 text-text-2">
                        {formatTime(e.ts)}
                      </span>
                      <span
                        className={
                          e.event === "_connected"
                            ? "w-44 shrink-0 text-accent"
                            : e.event.startsWith("error") ||
                                e.level === "error"
                              ? "w-44 shrink-0 text-bad"
                              : e.level === "warning"
                                ? "w-44 shrink-0 text-warn"
                                : "w-44 shrink-0 text-text-1"
                        }
                      >
                        {e.event}
                      </span>
                      <span className="truncate text-text-2">
                        {summarizeEvent(e)}
                      </span>
                      <span className="ml-auto shrink-0 text-[10px] text-text-2">
                        {timeAgo(e.ts)}
                      </span>
                    </li>
                  ))}
              </ul>
            )}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  );
}

function Kpi({
  icon,
  label,
  value,
  tone = "neutral",
  pulse = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  tone?: "accent" | "good" | "neutral";
  pulse?: boolean;
}) {
  const accentBar =
    tone === "accent"
      ? "from-accent/70 to-accent-2/70"
      : tone === "good"
        ? "from-good/60 to-accent-2/40"
        : "from-border to-border";
  return (
    <div className="relative overflow-hidden rounded-lg border border-border bg-bg-2 p-4">
      <div
        className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r ${accentBar}`}
      />
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-text-2">
        {icon}
        {label}
        {pulse && <PulseDot tone="good" size={6} />}
      </div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-text-0">
        <AnimatedNumber value={value} />
      </div>
    </div>
  );
}

function summarizeEvent(e: import("@/api/events").DashboardEvent): string {
  if (e.event === "_connected") return "WebSocket connected";
  const skip = new Set(["ts", "event", "level", "logger"]);
  const parts: string[] = [];
  for (const [k, v] of Object.entries(e)) {
    if (skip.has(k)) continue;
    if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
      parts.push(`${k}=${v}`);
    }
    if (parts.length >= 4) break;
  }
  return parts.join("  ");
}
