import { request } from "./client";

export type Lead = {
  name: string;
  phone: string;
  email?: string | null;
  company?: string | null;
  context?: string | null;
  source?: string | null;
  lead_id?: string | null;
  status?: string;
  called_at?: string | null;
  call_duration_seconds?: number | null;
  call_result?: string | null;
  notes?: string | null;
};

export type LeadCreate = Omit<Lead, "lead_id" | "status" | "called_at" | "call_duration_seconds" | "call_result" | "notes">;

export const fetchLeads = (signal?: AbortSignal) =>
  request<{ leads: Lead[] }>("/freelancer/leads", { signal });

export const createLead = (lead: LeadCreate) =>
  request<{ status: string; lead_id: string }>("/freelancer/leads", {
    method: "POST",
    body: lead,
  });

export const callLead = (leadId: string) =>
  request<{ status: string; call_sid: string; to: string }>(
    `/freelancer/call/${encodeURIComponent(leadId)}`,
    { method: "POST" },
  );
