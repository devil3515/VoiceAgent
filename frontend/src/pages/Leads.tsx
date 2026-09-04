import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Phone,
  Trash2,
  Search,
  X,
  AlertTriangle,
  CheckCircle2,
  Users,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toaster";
import { fadeUp, stagger } from "@/lib/motion";
import {
  callLead,
  createLead,
  fetchLeads,
  type Lead,
  type LeadCreate,
} from "@/api/leads";
import { formatPhone, timeAgo } from "@/lib/format";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const STATUS_TONE: Record<string, "neutral" | "accent" | "good" | "warn" | "bad"> = {
  pending: "neutral",
  queued: "warn",
  calling: "accent",
  called: "good",
  interested: "good",
  not_interested: "bad",
  consultation_booked: "accent",
  failed: "bad",
};

export function Leads() {
  const qc = useQueryClient();
  const toast = useToast();
  const { data, isLoading } = useQuery({
    queryKey: ["leads"],
    queryFn: ({ signal }) => fetchLeads(signal),
    refetchInterval: 15_000,
  });
  const leads: Lead[] = data?.leads ?? [];

  const [query, setQuery] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return leads;
    return leads.filter(
      (l) =>
        l.name.toLowerCase().includes(q) ||
        (l.company ?? "").toLowerCase().includes(q) ||
        l.phone.toLowerCase().includes(q),
    );
  }, [leads, query]);

  const callMut = useMutation({
    mutationFn: (id: string) => callLead(id),
    onSuccess: (res) => {
      toast.success(`Calling ${res.to}`);
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
    onError: (e) =>
      toast.error(e instanceof Error ? e.message : "Call failed"),
  });

  return (
    <motion.div initial="hidden" animate="show" variants={stagger(0.05)}>
      <motion.div
        variants={fadeUp}
        className="mb-6 flex flex-wrap items-end justify-between gap-3"
      >
        <div>
          <p className="text-xs uppercase tracking-widest text-text-2">Leads</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight">
            People to call
          </h2>
          <p className="mt-1 text-sm text-text-1">
            Saved in memory on the backend. Restarting the server clears them.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-2" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search…"
              className="h-9 w-56 rounded-lg border border-border bg-bg-2 pl-8 pr-3 text-sm text-text-0 outline-none placeholder:text-text-2 focus:border-accent/70 focus:ring-2 focus:ring-accent/30"
            />
          </div>
          <Button
            size="sm"
            iconLeft={<Plus className="h-3.5 w-3.5" />}
            onClick={() => setDrawerOpen(true)}
          >
            Add lead
          </Button>
        </div>
      </motion.div>

      <motion.div variants={fadeUp}>
        <Card>
          {isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-12 animate-pulse rounded-md bg-bg-2"
                />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              onAdd={() => setDrawerOpen(true)}
              hasAny={leads.length > 0}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wide text-text-2">
                    <th className="pb-2 pr-3 font-medium">Name</th>
                    <th className="pb-2 pr-3 font-medium">Company</th>
                    <th className="pb-2 pr-3 font-medium">Phone</th>
                    <th className="pb-2 pr-3 font-medium">Status</th>
                    <th className="pb-2 pr-3 font-medium">Last called</th>
                    <th className="pb-2 pr-0 text-right font-medium">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  <AnimatePresence initial={false}>
                    {filtered.map((l) => (
                      <motion.tr
                        key={l.lead_id}
                        layout
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="text-text-0"
                      >
                        <td className="py-2.5 pr-3">
                          <div className="font-medium">{l.name}</div>
                          {l.context && (
                            <div className="text-xs text-text-2">
                              {l.context}
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 pr-3 text-text-1">
                          {l.company ?? "—"}
                        </td>
                        <td className="py-2.5 pr-3 font-mono text-xs">
                          {formatPhone(l.phone)}
                        </td>
                        <td className="py-2.5 pr-3">
                          <Badge tone={STATUS_TONE[l.status ?? "pending"] ?? "neutral"}>
                            {l.status ?? "pending"}
                          </Badge>
                        </td>
                        <td className="py-2.5 pr-3 text-xs text-text-2">
                          {l.called_at ? timeAgo(l.called_at) : "—"}
                        </td>
                        <td className="py-2.5 pr-0 text-right">
                          <div className="inline-flex items-center gap-1.5">
                            <Button
                              size="sm"
                              variant="secondary"
                              iconLeft={<Phone className="h-3.5 w-3.5" />}
                              loading={
                                callMut.isPending &&
                                callMut.variables === l.lead_id
                              }
                              onClick={() =>
                                l.lead_id && callMut.mutate(l.lead_id)
                              }
                            >
                              Call
                            </Button>
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </motion.div>

      <AddLeadDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onCreated={() => {
          setDrawerOpen(false);
          qc.invalidateQueries({ queryKey: ["leads"] });
          toast.success("Lead added");
        }}
      />
    </motion.div>
  );
}

function AddLeadDrawer({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState<{
    name: string;
    phone: string;
    email: string;
    company: string;
    context: string;
    source: string;
  }>({
    name: "",
    phone: "",
    email: "",
    company: "",
    context: "",
    source: "",
  });
  const mutate = useMutation({
    mutationFn: (l: LeadCreate) => createLead(l),
    onSuccess: onCreated,
    onError: (e) => {
      // surface inside the drawer
      alert(e instanceof Error ? e.message : "Failed to create lead");
    },
  });

  const valid = form.name.trim() && form.phone.trim();

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 260, damping: 28 }}
            className="fixed right-0 top-0 z-50 flex h-full w-[380px] max-w-[calc(100vw-2rem)] flex-col border-l border-border bg-bg-0"
          >
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <h3 className="text-sm font-semibold">Add lead</h3>
              <button
                onClick={onClose}
                className="text-text-2 hover:text-text-0"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!valid) return;
                mutate.mutate({
                  ...form,
                  email: form.email?.trim() || undefined,
                  company: form.company?.trim() || undefined,
                  context: form.context?.trim() || undefined,
                  source: form.source?.trim() || undefined,
                });
              }}
              className="flex flex-1 flex-col gap-3 overflow-y-auto p-5"
            >
              <Input
                label="Name *"
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
              />
              <Input
                label="Phone *"
                placeholder="+15551234567"
                value={form.phone}
                onChange={(e) =>
                  setForm((f) => ({ ...f, phone: e.target.value }))
                }
              />
              <Input
                label="Email"
                type="email"
                value={form.email}
                onChange={(e) =>
                  setForm((f) => ({ ...f, email: e.target.value }))
                }
              />
              <Input
                label="Company"
                value={form.company}
                onChange={(e) =>
                  setForm((f) => ({ ...f, company: e.target.value }))
                }
              />
              <Textarea
                label="Context"
                placeholder="Why are you calling them?"
                value={form.context}
                onChange={(e) =>
                  setForm((f) => ({ ...f, context: e.target.value }))
                }
              />
              <Input
                label="Source"
                placeholder="LinkedIn, referral, …"
                value={form.source}
                onChange={(e) =>
                  setForm((f) => ({ ...f, source: e.target.value }))
                }
              />
              <div className="mt-auto flex items-center justify-end gap-2 pt-4">
                <Button variant="ghost" type="button" onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={mutate.isPending}
                  disabled={!valid}
                  iconLeft={<CheckCircle2 className="h-4 w-4" />}
                >
                  Save lead
                </Button>
              </div>
            </form>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function EmptyState({
  onAdd,
  hasAny,
}: {
  onAdd: () => void;
  hasAny: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <div className="rounded-full border border-border bg-bg-2 p-3">
        {hasAny ? (
          <Search className="h-5 w-5 text-text-2" />
        ) : (
          <Users className="h-5 w-5 text-text-2" />
        )}
      </div>
      <div>
        <p className="text-sm font-medium text-text-0">
          {hasAny ? "No leads match your search" : "No leads yet"}
        </p>
        <p className="mt-1 text-xs text-text-2">
          {hasAny
            ? "Try a different name, company, or phone."
            : "Add your first lead to start the conversation."}
        </p>
      </div>
      {!hasAny && (
        <Button
          size="sm"
          variant="secondary"
          iconLeft={<Plus className="h-3.5 w-3.5" />}
          onClick={onAdd}
        >
          Add lead
        </Button>
      )}
    </div>
  );
}

// keep the AlertTriangle import live even if the row actions don't use it
// (used to flag unreachable numbers; not in v1, kept for future use)
void AlertTriangle;
void Trash2;
