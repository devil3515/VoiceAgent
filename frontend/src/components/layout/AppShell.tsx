import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { motion } from "framer-motion";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <motion.main
          key={typeof window !== "undefined" ? window.location.pathname : "x"}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className="flex-1 overflow-y-auto px-5 py-6 md:px-8 md:py-8"
        >
          <div className="mx-auto w-full max-w-6xl">{children}</div>
        </motion.main>
      </div>
    </div>
  );
}
