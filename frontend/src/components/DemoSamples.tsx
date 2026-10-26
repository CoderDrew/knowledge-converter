"use client";

import { useEffect, useState } from "react";
import { getDemoConversion, getDemoIndex, type Conversion, type DemoSample } from "@/lib/api";
import { DocIcon, SlidesIcon } from "./icons";

/**
 * Demo-mode replacement for the upload dropzone. Lists the pre-rendered
 * synthetic samples; choosing one opens the real workspace with real engine
 * output that was generated ahead of time. No file leaves the visitor's device.
 */
export function DemoSamples({ onLoaded }: { onLoaded: (conversion: Conversion) => void }) {
  const [samples, setSamples] = useState<DemoSample[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getDemoIndex(controller.signal)
      .then((index) => setSamples(index.samples))
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, []);

  async function open(id: string) {
    setBusy(id);
    setError(null);
    try {
      onLoaded(await getDemoConversion(id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-[var(--mj-radius-md)] border border-line bg-surface p-6 sm:p-8">
      <h2 className="text-[1.375rem] leading-[1.875rem] text-ink">Try it with a sample file</h2>
      <p className="mt-2 text-sm leading-relaxed text-ink-2">
        This public demo shows real converter output for two synthetic sample files. Uploads are turned off here, so nothing you
        own is sent anywhere.
      </p>
      <ul className="mt-6 grid gap-3">
        {samples === null && !error && <li className="text-sm text-muted">Loading samples…</li>}
        {samples?.map((s) => (
          <li key={s.id}>
            <button
              onClick={() => open(s.id)}
              disabled={busy !== null}
              aria-busy={busy === s.id}
              className="flex w-full items-center gap-3 rounded-xl border border-line-strong bg-paper px-4 py-3 text-left transition hover:border-ink disabled:opacity-60"
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-surface-2 text-ink-2" aria-hidden="true">
                {s.kind === "pptx" ? <SlidesIcon size={18} /> : <DocIcon size={18} />}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold">{s.name}</span>
                <span className="block text-xs text-muted">{s.kind === "pptx" ? "PowerPoint" : "Word"} · open the converted result</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {error && (
        <p className="mt-4 text-sm text-danger" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
