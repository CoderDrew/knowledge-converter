"use client";

export type EngineStatus = "checking" | "online" | "offline" | "demo";

export function Header({ status, onHome }: { status: EngineStatus; onHome: () => void }) {
  const label = { checking: "Connecting to engine", online: "Engine online", offline: "Engine offline", demo: "Demo mode · samples only" }[status];
  const dot = { checking: "bg-muted pulse-dot", online: "bg-success", offline: "bg-danger", demo: "bg-accent" }[status];
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-paper">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <button onClick={onHome} className="flex items-center gap-4 rounded-[var(--mj-radius-sm)] text-left" aria-label="Knowledge Converter home">
          {/* Plain text wordmark per BRAND.md: MINDJAX in Michroma caps, +0.05em tracking. No symbol. */}
          <span className="font-display text-base tracking-[0.05em] text-ink">MINDJAX</span>
          <span className="h-5 w-px bg-line" aria-hidden="true" />
          <span className="text-base font-semibold text-ink">Knowledge Converter</span>
        </button>
        <div className="flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink-2" role="status" aria-live="polite">
          <span className={`size-2 rounded-full ${dot}`} />
          <span>{label}</span>
        </div>
      </div>
    </header>
  );
}
