import { motion } from "framer-motion";

/** Slow-drifting gradient mesh used as a decorative background. */
export function GradientMesh({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={
        "pointer-events-none absolute inset-0 overflow-hidden " + (className ?? "")
      }
    >
      <motion.div
        className="absolute -top-32 -left-24 h-[420px] w-[420px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(124,92,255,0.35) 0%, transparent 70%)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, 40, -10, 0], y: [0, 20, -15, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -top-10 right-0 h-[360px] w-[360px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(34,211,238,0.25) 0%, transparent 70%)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, -30, 20, 0], y: [0, 25, -10, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-0 left-1/3 h-[300px] w-[300px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(124,92,255,0.18) 0%, transparent 70%)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, 25, -20, 0], y: [0, -15, 10, 0] }}
        transition={{ duration: 30, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
