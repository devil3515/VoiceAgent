import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mic,
  CheckCircle2,
  Building2,
  User,
  ArrowRight,
} from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SegmentedTabs } from "@/components/ui/SegmentedTabs";
import { useToast } from "@/components/ui/Toaster";
import { fetchLeads, type Lead } from "@/api/leads";
import { fadeUp, stagger } from "@/lib/motion";
import { useQuery } from "@tanstack/react-query";

type Tab = "clinic" | "freelancer";

export function OutboundCall() {
  const [tab, setTab] = useState<Tab>("clinic");
  const navigate = useNavigate();
  const toast = useToast();

  const goTalk = (persona: Tab, leadId?: string) => {
    const params = new URLSearchParams({ persona });
    if (leadId) params.set("lead_id", leadId);
    navigate(`/talk?${params.toString()}`);
  };

  return (
    <motion.div initial="hidden" animate="show" variants={stagger(0.05)}>
      <motion.div variants={fadeUp} className="mb-6">
        <div>
          <p className="text-xs uppercase tracking-widest text-text-2">
            Talk
          </p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight">
            Start a conversation
          </h2>
          <p className="mt-1 text-sm text-text-1">
            Connect to an agent right from your browser — no phone line needed.
            Pick a persona and start speaking.
          </p>
        </div>
      </motion.div>

      <motion.div variants={fadeUp}>
        <div className="mb-4">
          <SegmentedTabs
            value={tab}
            onChange={(v) => setTab(v as Tab)}
            ariaLabel="Persona"
            tabs={[
              { id: "clinic", label: "Clinic (Acme)", icon: Building2 },
              { id: "freelancer", label: "Freelancer", icon: User },
            ]}
          />
        </div>
      </motion.div>

      <AnimatePresence mode="wait">
        {tab === "clinic" ? (
          <motion.div
            key="clinic"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
          >
            <ClinicLauncher onTalk={() => goTalk("clinic")} />
          </motion.div>
        ) : (
          <motion.div
            key="freelancer"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
          >
            <FreelancerLauncher onTalk={goTalk} toast={toast} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function ClinicLauncher({ onTalk }: { onTalk: () => void }) {
  return (
    <Card>
      <CardHeader
        title={
          <span className="inline-flex items-center gap-2">
            <Building2 className="h-4 w-4 text-text-2" />
            Clinic (Acme Corp)
          </span>
        }
        subtitle="Open a live voice session with the Acme reception agent"
      />
      <div className="flex items-center gap-3">
        <Button size="lg" onClick={onTalk} iconLeft={<Mic className="h-4 w-4" />}>
          Talk to clinic agent
          <ArrowRight className="h-4 w-4" />
        </Button>
        <span className="text-xs text-text-2">
          Streams over <code>/ws/voice?persona=clinic</code>
        </span>
      </div>
    </Card>
  );
}

function FreelancerLauncher({
  onTalk,
  toast,
}: {
  onTalk: (persona: "freelancer", leadId?: string) => void;
  toast: ReturnType<typeof useToast>;
}) {
  const [leadId, setLeadId] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["leads", "launchpad"],
    queryFn: ({ signal }) => fetchLeads(signal),
  });
  const leads: Lead[] = data?.leads ?? [];
  const selected = leads.find((l) => l.lead_id === leadId) ?? null;

  return (
    <Card>
      <CardHeader
        title={
          <span className="inline-flex items-center gap-2">
            <User className="h-4 w-4 text-text-2" />
            Freelancer lead
          </span>
        }
        subtitle="Open a live voice session for the freelancer agent"
      />
      <div className="space-y-4">
        <div>
          <label
            htmlFor="lead"
            className="mb-1.5 block text-xs font-medium text-text-1"
          >
            Lead (optional)
          </label>
          {isLoading ? (
            <div className="h-10 animate-pulse rounded-lg bg-bg-2" />
          ) : leads.length === 0 ? (
            <div className="rounded-md border border-border bg-bg-2 px-3 py-2 text-sm text-text-1">
              No leads yet — add one on the{" "}
              <a href="/leads" className="text-accent underline-offset-2 hover:underline">
                Leads
              </a>{" "}
              page, or talk without a lead.
            </div>
          ) : (
            <select
              id="lead"
              value={leadId}
              onChange={(e) => setLeadId(e.target.value)}
              className="w-full rounded-lg border border-border bg-bg-2 px-3 py-2 text-sm text-text-0 outline-none focus:border-accent/70 focus:ring-2 focus:ring-accent/30"
            >
              <option value="">General (no lead)</option>
              {leads.map((l) => (
                <option key={l.lead_id ?? l.name} value={l.lead_id ?? ""}>
                  {l.name} — {l.company ?? l.phone}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="flex items-center gap-3">
          <Button
            size="lg"
            onClick={() => {
              onTalk("freelancer", selected ? selected.lead_id ?? undefined : undefined);
              if (selected) toast.success(`Connecting with ${selected.name}`);
            }}
            iconLeft={<Mic className="h-4 w-4" />}
          >
            {selected ? `Talk to ${selected.name}` : "Talk to freelancer agent"}
            <ArrowRight className="h-4 w-4" />
          </Button>
          <span className="text-xs text-text-2">
            Streams over <code>/ws/voice?persona=freelancer</code>
          </span>
        </div>

        <div className="flex items-center gap-2 rounded-md border border-good/30 bg-good/10 px-3 py-2 text-sm text-good">
          <CheckCircle2 className="h-4 w-4" />
          Live talk only — no outbound dialing required.
        </div>
      </div>
    </Card>
  );
}
