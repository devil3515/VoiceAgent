import { useEffect, useRef, useState } from "react";
import { WS_BASE } from "@/api/client";
import type { DashboardEvent } from "@/api/events";

const MAX_EVENTS = 100;

export type EventStreamState = {
  events: DashboardEvent[];
  status: "connecting" | "open" | "reconnecting" | "closed";
};

/**
 * Subscribes to /ws/dashboard and re-emits the last MAX_EVENTS events.
 * Auto-reconnects with backoff (1s -> 5s).
 */
export function useEventStream(): EventStreamState {
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [status, setStatus] = useState<EventStreamState["status"]>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;

    const connect = () => {
      if (stoppedRef.current) return;
      setStatus((s) => (s === "open" ? "reconnecting" : s));
      const ws = new WebSocket(`${WS_BASE}/ws/dashboard`);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setStatus("open");
        setEvents((prev) => [
          ...prev,
          {
            ts: new Date().toISOString(),
            event: "_connected",
            level: "info",
          },
        ]);
      };

      ws.onmessage = (msg) => {
        try {
          const parsed = JSON.parse(msg.data) as DashboardEvent;
          setEvents((prev) => {
            const next = [...prev, parsed];
            return next.length > MAX_EVENTS
              ? next.slice(next.length - MAX_EVENTS)
              : next;
          });
        } catch {
          // ignore malformed
        }
      };

      ws.onclose = () => {
        if (stoppedRef.current) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 5000);
        retryRef.current += 1;
        setStatus("reconnecting");
        timerRef.current = window.setTimeout(connect, delay);
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          // ignore
        }
      };
    };

    connect();
    return () => {
      stoppedRef.current = true;
      if (timerRef.current) window.clearTimeout(timerRef.current);
      try {
        wsRef.current?.close();
      } catch {
        // ignore
      }
      setStatus("closed");
    };
  }, []);

  return { events, status };
}
