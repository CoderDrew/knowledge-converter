"use client";

export type EngineStatus = "checking" | "online" | "offline";

export function Header({ status, onHome }: { status: EngineStatus; onHome: () => void }) {
  const label = { checking: "Connecting to engine", online: "Engine online", offline: "Engine offline" }[status];
  const dot = { checking: "bg-muted pulse-dot", online: "bg-success", offline: "bg-danger" }[status];
  return (
    <header className="sticky top-0 z-30 border-b border-line/80 bg-paper/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <button onClick={onHome} className="group flex items-center gap-3 text-left" aria-label="Knowledge Converter home">
          <span className="grid size-9 place-items-center rounded-[10px] bg-ink text-paper transition-transform duration-300 group-hover:rotate-[-6deg]">
            <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 18V6l5 6 5-6v12" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="19" cy="17" r="2" fill="var(--signal)" />
            </svg>
          </span>
          <span className="leading-tight">
            <span className="block text-[15px] font-semibold tracking-tight">Knowledge Converter</span>
            <span className="block text-xs text-muted">Mindjax Innovation Lab</span>
          </span>
        </button>
        <div className="flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-medium text-ink-2" role="status" aria-live="polite">
          <span className={`size-2 rounded-full ${dot}`} />
          <span>{label}</span>
        </div>
      </div>
    </header>
  );
}
