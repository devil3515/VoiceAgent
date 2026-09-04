import { request } from "./client";

export type HealthConfig = {
  deepgram: boolean;
  bedrock: boolean;
  cartesia: boolean;
};

export type Health = {
  status: "healthy" | string;
  active_calls: number;
  phase: number;
  config: HealthConfig;
  tools: string[];
  knowledge_base: { num_documents: number };
};

export const fetchHealth = (signal?: AbortSignal) =>
  request<Health>("/health", { signal });
