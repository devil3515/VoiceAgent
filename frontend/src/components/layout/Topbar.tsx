import { Activity, Phone } from "lucide-react";
import { PulseDot } from "@/components/effects/PulseDot";
import { useEventStream } from "@/hooks/useEventStream";
import { useHealth } from "@/hooks/useHealth";
import clsx from "clsx";

const labels: Record<ReturnType<typeof useEventStream>["status"], string> = {
  connecting: "Connecting…",
  open: "Live",
  reconnecting: "Reconnecting…",
  closed: "Offline",
};

export function Topbar() {
  const { data, isLoading, isError } = useHealth();
  const { status } = useEventStream();

  const tone =
    status === "open"
      ? ("good" as const)
      : status === "connecting" || status === "reconnecting"
        ? ("warn" as const)
        : ("bad" as const);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-bg-0/70 px-5 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-text-0">Voice Agent</h1>
        <span className="hidden text-xs text-text-2 sm:inline">
          Real-time control panel
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div
          className={clsx(
            "flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-medium",
            tone === "good" && "border-good/30 bg-good/10 text-good",
            tone === "warn" && "border-warn/30 bg-warn/10 text-warn",
            tone === "bad" && "border-bad/30 bg-bad/10 text-bad",
          )}
        >
          <PulseDot active={tone !== "bad"} tone={tone} size={6} />
          {labels[status]}
        </div>

        <div className="hidden items-center gap-2 rounded-full border border-border bg-bg-2 px-3 py-1 text-[11px] text-text-1 sm:flex">
          <Phone className="h-3.5 w-3.5 text-text-2" />
          {isLoading
            ? "—"
            : isError
              ? "offline"
              : `${data?.active_calls ?? 0} active`}
        </div>

        <div className="hidden items-center gap-2 rounded-full border border-border bg-bg-2 px-3 py-1 text-[11px] text-text-1 md:flex">
          <Activity className="h-3.5 w-3.5 text-text-2" />
          {isLoading
            ? "—"
            : isError
              ? "API down"
              : data?.status ?? "unknown"}
        </div>
      </div>
    </header>
  );
}
