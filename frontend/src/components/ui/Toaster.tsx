import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";
import clsx from "clsx";

type ToastTone = "success" | "error" | "info";
type Toast = { id: number; tone: ToastTone; message: string };

type Ctx = {
  show: (tone: ToastTone, message: string) => void;
  success: (msg: string) => void;
  error: (msg: string) => void;
  info: (msg: string) => void;
};

const ToastCtx = createContext<Ctx | null>(null);

export function Toaster({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback(
    (tone: ToastTone, message: string) => {
      const id = ++idRef.current;
      setToasts((prev) => [...prev, { id, tone, message }]);
      window.setTimeout(() => remove(id), 4000);
    },
    [remove],
  );

  const value = useMemo<Ctx>(
    () => ({
      show,
      success: (m) => show("success", m),
      error: (m) => show("error", m),
      info: (m) => show("info", m),
    }),
    [show],
  );

  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed top-4 right-4 z-50 flex w-[320px] max-w-[calc(100vw-2rem)] flex-col gap-2">
        <AnimatePresence initial={false}>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 16, scale: 0.96 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 16, scale: 0.96 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className={clsx(
                "pointer-events-auto glass flex items-start gap-2.5 rounded-lg p-3 shadow-lg",
                t.tone === "success" && "border-good/30",
                t.tone === "error" && "border-bad/40",
                t.tone === "info" && "border-accent/30",
              )}
            >
              <div className="mt-0.5">
                {t.tone === "success" && (
                  <CheckCircle2 className="h-4 w-4 text-good" />
                )}
                {t.tone === "error" && (
                  <AlertTriangle className="h-4 w-4 text-bad" />
                )}
                {t.tone === "info" && (
                  <Info className="h-4 w-4 text-accent" />
                )}
              </div>
              <p className="flex-1 text-sm leading-snug text-text-0">
                {t.message}
              </p>
              <button
                type="button"
                onClick={() => remove(t.id)}
                className="text-text-2 hover:text-text-0"
                aria-label="Dismiss"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast(): Ctx {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used inside <Toaster />");
  return ctx;
}
