import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Trash2,
  Save,
  RotateCcw,
  Briefcase,
  Link as LinkIcon,
  Clock,
  User,
  CheckCircle2,
} from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea, Checkbox } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toaster";
import { fadeUp, stagger } from "@/lib/motion";
import {
  fetchProfile,
  updateProfile,
  type FreelancerProfile as Profile,
  type Service,
} from "@/api/profile";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

function emptyService(): Service {
  return { name: "", description: "", starting_price: "", delivery_time: "" };
}

function normalize(p: Profile): Profile {
  return {
    ...p,
    services: p.services.map((s) => ({
      name: s.name ?? "",
      description: s.description ?? "",
      starting_price: s.starting_price ?? "",
      delivery_time: s.delivery_time ?? "",
    })),
  };
}

export function FreelancerProfilePage() {
  const qc = useQueryClient();
  const toast = useToast();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["freelancer", "profile"],
    queryFn: ({ signal }) => fetchProfile(signal),
  });

  const [draft, setDraft] = useState<Profile | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (data) {
      setDraft(normalize(data));
      setDirty(false);
    }
  }, [data]);

  const mutate = useMutation({
    mutationFn: (p: Profile) =>
      updateProfile({
        ...p,
        // strip empty optional strings so backend stores them as null
        company: p.company?.trim() ? p.company : null,
        hourly_rate: p.hourly_rate?.trim() ? p.hourly_rate : null,
        project_rate: p.project_rate?.trim() ? p.project_rate : null,
        portfolio_url: p.portfolio_url?.trim() ? p.portfolio_url : null,
        calendly_url: p.calendly_url?.trim() ? p.calendly_url : null,
        linkedin_url: p.linkedin_url?.trim() ? p.linkedin_url : null,
        github_url: p.github_url?.trim() ? p.github_url : null,
        available_from: p.available_from?.trim() ? p.available_from : null,
      }),
    onSuccess: (res) => {
      toast.success(`Profile saved (${res.name})`);
      qc.invalidateQueries({ queryKey: ["freelancer", "profile"] });
      setDirty(false);
    },
    onError: (e) => {
      toast.error(e instanceof Error ? e.message : "Save failed");
    },
  });

  const servicesValid = useMemo(() => {
    if (!draft) return true;
    return draft.services.every(
      (s) => s.name.trim().length > 0 && s.description.trim().length > 0,
    );
  }, [draft]);

  if (isLoading || !draft) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-md bg-bg-2" />
        <div className="h-64 animate-pulse rounded-xl bg-bg-1" />
      </div>
    );
  }

  if (isError) {
    return (
      <Card>
        <p className="text-sm text-bad">
          Could not load the freelancer profile. Is the backend running?
        </p>
      </Card>
    );
  }

  function patch<K extends keyof Profile>(key: K, value: Profile[K]) {
    setDraft((d) => (d ? { ...d, [key]: value } : d));
    setDirty(true);
  }

  function patchService(idx: number, key: keyof Service, value: string) {
    setDraft((d) => {
      if (!d) return d;
      const services = d.services.map((s, i) =>
        i === idx ? { ...s, [key]: value } : s,
      );
      return { ...d, services };
    });
    setDirty(true);
  }

  function addService() {
    setDraft((d) =>
      d ? { ...d, services: [...d.services, emptyService()] } : d,
    );
    setDirty(true);
  }

  function removeService(idx: number) {
    setDraft((d) =>
      d ? { ...d, services: d.services.filter((_, i) => i !== idx) } : d,
    );
    setDirty(true);
  }

  return (
    <motion.div initial="hidden" animate="show" variants={stagger(0.05)}>
      <motion.div
        variants={fadeUp}
        className="mb-6 flex flex-wrap items-end justify-between gap-3"
      >
        <div>
          <p className="text-xs uppercase tracking-widest text-text-2">
            Freelancer
          </p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight">
            Profile
          </h2>
          <p className="mt-1 text-sm text-text-1">
            This is exactly what the agent says on the call — it never invents
            anything.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <AnimatePresence>
            {dirty && (
              <motion.span
                initial={{ opacity: 0, x: 6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 6 }}
                className="inline-flex items-center gap-1 text-xs text-warn"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-warn" />
                unsaved
              </motion.span>
            )}
          </AnimatePresence>
          <Button
            variant="secondary"
            size="sm"
            iconLeft={<RotateCcw className="h-3.5 w-3.5" />}
            onClick={() => {
              if (data) {
                setDraft(normalize(data));
                setDirty(false);
              }
            }}
            disabled={!dirty}
          >
            Reset
          </Button>
          <Button
            size="sm"
            iconLeft={<Save className="h-3.5 w-3.5" />}
            loading={mutate.isPending}
            disabled={!dirty || !servicesValid}
            onClick={() => mutate.mutate(draft)}
          >
            Save
          </Button>
        </div>
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div variants={fadeUp} className="lg:col-span-2 space-y-6">
          {/* Identity */}
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <User className="h-4 w-4 text-text-2" />
                  Identity
                </span>
              }
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Name"
                value={draft.name}
                onChange={(e) => patch("name", e.target.value)}
              />
              <Input
                label="Title"
                value={draft.title}
                onChange={(e) => patch("title", e.target.value)}
              />
              <Input
                label="Email"
                type="email"
                value={draft.email}
                onChange={(e) => patch("email", e.target.value)}
              />
              <Input
                label="Phone"
                value={draft.phone}
                onChange={(e) => patch("phone", e.target.value)}
              />
              <Input
                label="Company"
                value={draft.company ?? ""}
                onChange={(e) => patch("company", e.target.value)}
                className="sm:col-span-2"
              />
              <Textarea
                label="Bio"
                value={draft.bio}
                onChange={(e) => patch("bio", e.target.value)}
                className="sm:col-span-2"
              />
            </div>
          </Card>

          {/* Services */}
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Briefcase className="h-4 w-4 text-text-2" />
                  Services
                </span>
              }
              subtitle="Each one needs a name and a description"
              right={
                <Button
                  size="sm"
                  variant="secondary"
                  iconLeft={<Plus className="h-3.5 w-3.5" />}
                  onClick={addService}
                >
                  Add service
                </Button>
              }
            />
            <div className="space-y-3">
              {draft.services.length === 0 && (
                <p className="rounded-md border border-dashed border-border bg-bg-0/40 px-3 py-4 text-center text-sm text-text-2">
                  No services yet. Add one to get started.
                </p>
              )}
              {draft.services.map((s, i) => (
                <motion.div
                  key={i}
                  layout
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-lg border border-border bg-bg-2 p-3"
                >
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      label="Name"
                      value={s.name}
                      onChange={(e) => patchService(i, "name", e.target.value)}
                    />
                    <Input
                      label="Starting price"
                      placeholder="$3,000"
                      value={s.starting_price ?? ""}
                      onChange={(e) =>
                        patchService(i, "starting_price", e.target.value)
                      }
                    />
                    <Textarea
                      label="Description"
                      className="sm:col-span-2"
                      value={s.description}
                      onChange={(e) =>
                        patchService(i, "description", e.target.value)
                      }
                    />
                    <Input
                      label="Delivery time"
                      placeholder="2-4 weeks"
                      value={s.delivery_time ?? ""}
                      onChange={(e) =>
                        patchService(i, "delivery_time", e.target.value)
                      }
                    />
                  </div>
                  <div className="mt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => removeService(i)}
                      className="inline-flex items-center gap-1 text-xs text-text-2 hover:text-bad"
                    >
                      <Trash2 className="h-3 w-3" />
                      Remove
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>
        </motion.div>

        <motion.div variants={fadeUp} className="space-y-6">
          {/* Rates */}
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Briefcase className="h-4 w-4 text-text-2" />
                  Rates
                </span>
              }
            />
            <div className="space-y-3">
              <Input
                label="Hourly rate"
                placeholder="$100-150/hour"
                value={draft.hourly_rate ?? ""}
                onChange={(e) => patch("hourly_rate", e.target.value)}
              />
              <Input
                label="Project rate"
                placeholder="Varies by scope"
                value={draft.project_rate ?? ""}
                onChange={(e) => patch("project_rate", e.target.value)}
              />
            </div>
          </Card>

          {/* Links */}
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <LinkIcon className="h-4 w-4 text-text-2" />
                  Links
                </span>
              }
            />
            <div className="space-y-3">
              <Input
                label="Portfolio"
                value={draft.portfolio_url ?? ""}
                onChange={(e) => patch("portfolio_url", e.target.value)}
                placeholder="https://…"
              />
              <Input
                label="Calendly"
                value={draft.calendly_url ?? ""}
                onChange={(e) => patch("calendly_url", e.target.value)}
                placeholder="https://calendly.com/…"
              />
              <Input
                label="LinkedIn"
                value={draft.linkedin_url ?? ""}
                onChange={(e) => patch("linkedin_url", e.target.value)}
              />
              <Input
                label="GitHub"
                value={draft.github_url ?? ""}
                onChange={(e) => patch("github_url", e.target.value)}
              />
            </div>
          </Card>

          {/* Availability */}
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Clock className="h-4 w-4 text-text-2" />
                  Availability
                </span>
              }
            />
            <div className="space-y-3">
              <Input
                label="Working hours"
                value={draft.working_hours}
                onChange={(e) => patch("working_hours", e.target.value)}
              />
              <Input
                label="Timezone"
                value={draft.timezone}
                onChange={(e) => patch("timezone", e.target.value)}
              />
              <Input
                label="Available from"
                value={draft.available_from ?? ""}
                onChange={(e) => patch("available_from", e.target.value)}
                placeholder="Immediately"
              />
              <div className="flex flex-col gap-2 pt-1">
                <Checkbox
                  name="free_consultation"
                  label="Offer free consultation"
                  checked={draft.free_consultation}
                  onChange={(e) =>
                    patch("free_consultation", e.target.checked)
                  }
                />
                <Input
                  label="Consultation duration"
                  value={draft.consultation_duration}
                  onChange={(e) =>
                    patch("consultation_duration", e.target.value)
                  }
                />
                <Checkbox
                  name="follow_up_email"
                  label="Send follow-up email after calls"
                  checked={draft.follow_up_email}
                  onChange={(e) => patch("follow_up_email", e.target.checked)}
                />
              </div>
            </div>
          </Card>

          <AnimatePresence>
            {!dirty && data && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 rounded-md border border-good/30 bg-good/10 px-3 py-2 text-sm text-good"
              >
                <CheckCircle2 className="h-4 w-4" />
                Profile is in sync with the backend.
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </motion.div>
  );
}
