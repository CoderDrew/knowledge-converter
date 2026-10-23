"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Header, type EngineStatus } from "@/components/Header";
import { Intake, type IntakePhase } from "@/components/Intake";
import { Footer, HeroCopy, HowItWorks } from "@/components/Landing";
import { Workspace } from "@/components/Workspace";
import { ApiError, deleteConversion, getHealth, uploadForConversion, type Conversion } from "@/lib/api";
import { validateFile } from "@/lib/format";

const DEFAULT_MAX_BYTES = 20 * 1024 * 1024;

export default function Home() {
  const [engine, setEngine] = useState<EngineStatus>("checking");
  const [maxBytes, setMaxBytes] = useState(DEFAULT_MAX_BYTES);
  const [phase, setPhase] = useState<IntakePhase>({ kind: "idle" });
  const [conversion, setConversion] = useState<Conversion | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const checkEngine = useCallback(async () => {
    try {
      const health = await getHealth();
      setMaxBytes(health.limits.max_upload_bytes);
      setEngine("online");
    } catch {
      setEngine("offline");
    }
  }, []);

  useEffect(() => {
    checkEngine();
    const timer = window.setInterval(checkEngine, 15_000);
    return () => window.clearInterval(timer);
  }, [checkEngine]);

  const start = useCallback(
    (file: File) => {
      const problem = validateFile(file, maxBytes);
      if (problem) {
        setPhase({ kind: "error", file, code: problem.includes("limit") ? "file_too_large" : "unsupported_type", message: problem });
        return;
      }
      setPhase({ kind: "uploading", file, progress: 0 });
      const { promise, abort } = uploadForConversion(file, {
        onUploadProgress: (progress) => setPhase((p) => (p.kind === "uploading" ? { ...p, progress } : p)),
        onUploaded: () => setPhase({ kind: "converting", file, startedAt: Date.now() }),
      });
      abortRef.current = abort;
      promise
        .then((result) => {
          setConversion(result);
          setPhase({ kind: "idle" });
          window.scrollTo({ top: 0, behavior: "smooth" });
        })
        .catch((error: ApiError) => {
          if (error.code === "aborted") {
            setPhase({ kind: "idle" });
            return;
          }
          if (error.code === "network") checkEngine();
          setPhase({ kind: "error", file, code: error.code, message: error.message });
        })
        .finally(() => {
          abortRef.current = null;
        });
    },
    [maxBytes, checkEngine],
  );

  const reset = useCallback(() => {
    setConversion(null);
    setPhase({ kind: "idle" });
  }, []);

  const discard = useCallback(async () => {
    if (conversion) await deleteConversion(conversion.id);
    reset();
  }, [conversion, reset]);

  return (
    <>
      <Header status={engine} onHome={reset} />
      <main>
        {conversion ? (
          <Workspace conversion={conversion} onNew={reset} onDiscard={discard} />
        ) : (
          <>
            <section className="relative overflow-hidden">
              <div className="grid-backdrop pointer-events-none absolute inset-0" aria-hidden="true" />
              <div className="relative mx-auto grid max-w-7xl grid-cols-[minmax(0,1fr)] items-center gap-12 px-4 pt-14 pb-20 sm:px-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-16 lg:px-8 lg:pt-24 lg:pb-28">
                <HeroCopy />
                <div className="animate-rise animate-rise-delay-1">
                  <Intake
                    phase={phase}
                    maxBytes={maxBytes}
                    disabled={engine === "offline"}
                    onFile={start}
                    onReset={() => setPhase({ kind: "idle" })}
                    onCancel={() => abortRef.current?.()}
                  />
                </div>
              </div>
            </section>
            <HowItWorks />
          </>
        )}
      </main>
      <Footer />
    </>
  );
}
