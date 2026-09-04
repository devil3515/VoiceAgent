/** Shape of a single event line streamed from /ws/dashboard. */
export type DashboardEvent = {
  ts: string;
  event: string;
  level?: string;
  logger?: string;
  [key: string]: unknown;
};
