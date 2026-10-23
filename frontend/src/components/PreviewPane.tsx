"use client";

import { useState } from "react";
import { urls, type ProfileId } from "@/lib/api";
import { LockIcon, MonitorIcon, PhoneIcon, TabletIcon } from "./icons";

const WIDTHS = [
  { id: "desktop", label: "Desktop", width: "100%", icon: <MonitorIcon size={15} /> },
  { id: "tablet", label: "Tablet", width: "768px", icon: <TabletIcon size={15} /> },
  { id: "mobile", label: "Mobile", width: "390px", icon: <PhoneIcon size={15} /> },
] as const;

/**
 * The preview is served by the API origin (not this site) with a CSP
 * `sandbox` header, and the iframe adds its own empty `sandbox` attribute:
 * no scripts, no forms, no same-origin access, no top navigation.
 */
export function PreviewPane({ conversionId, profileId, title }: { conversionId: string; profileId: ProfileId; title: string }) {
  const [device, setDevice] = useState<(typeof WIDTHS)[number]["id"]>("desktop");
  const [loaded, setLoaded] = useState<string | null>(null);
  const src = urls.preview(conversionId, profileId);
  const width = WIDTHS.find((w) => w.id === device)!.width;

  return (
    <div className="overflow-hidden rounded-[18px] border border-line bg-surface shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface-2 px-4 py-2.5">
        <div className="flex items-center gap-3">
          <span className="flex gap-1.5" aria-hidden="true">
            <span className="size-2.5 rounded-full bg-line-strong" />
            <span className="size-2.5 rounded-full bg-line-strong" />
            <span className="size-2.5 rounded-full bg-line-strong" />
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-md bg-surface px-2 py-1 text-xs font-medium text-muted">
            <LockIcon size={12} /> Sandboxed preview · scripts disabled
          </span>
        </div>
        <div className="hidden items-center gap-1 sm:flex" role="group" aria-label="Preview width">
          {WIDTHS.map((w) => (
            <button
              key={w.id}
              onClick={() => setDevice(w.id)}
              aria-pressed={device === w.id}
              title={w.label}
              className={`grid size-8 place-items-center rounded-lg transition ${device === w.id ? "bg-ink text-paper" : "text-muted hover:bg-surface hover:text-ink"}`}
            >
              {w.icon}
              <span className="sr-only">{w.label}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="relative bg-[repeating-linear-gradient(45deg,var(--surface-2),var(--surface-2)_10px,var(--paper)_10px,var(--paper)_20px)]">
        {loaded !== src && (
          <div className="absolute inset-0 z-10 grid place-items-center bg-surface/70 text-sm text-muted">Rendering preview…</div>
        )}
        <iframe
          key={src}
          title={`Preview of ${title}`}
          src={src}
          sandbox=""
          referrerPolicy="no-referrer"
          loading="lazy"
          onLoad={() => setLoaded(src)}
          className="mx-auto block h-[72vh] min-h-[480px] w-full bg-white transition-[max-width] duration-500 ease-out"
          style={{ maxWidth: width }}
        />
      </div>
    </div>
  );
}
