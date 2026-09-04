import { request } from "./client";

export type Service = {
  name: string;
  description: string;
  starting_price?: string | null;
  delivery_time?: string | null;
};

export type FreelancerProfile = {
  name: string;
  email: string;
  phone: string;
  title: string;
  company?: string | null;
  bio: string;
  services: Service[];
  hourly_rate?: string | null;
  project_rate?: string | null;
  portfolio_url?: string | null;
  calendly_url?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  available_from?: string | null;
  working_hours: string;
  timezone: string;
  free_consultation: boolean;
  consultation_duration: string;
  follow_up_email: boolean;
  profile_id?: string | null;
  created_at?: string | null;
};

export const fetchProfile = (signal?: AbortSignal) =>
  request<FreelancerProfile>("/freelancer/profile", { signal });

export const updateProfile = (profile: FreelancerProfile) =>
  request<{ status: string; name: string }>("/freelancer/profile", {
    method: "POST",
    body: profile,
  });
