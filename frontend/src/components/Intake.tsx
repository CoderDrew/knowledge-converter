"use client";

import { useEffect, useRef, useState } from "react";
import { extensionOf, formatBytes } from "@/lib/format";
import { AlertIcon, CheckIcon, FileKindIcon, LockIcon, UploadIcon } from "./icons";

export type IntakePhase =
  | { kind: "idle" }
  | { kind: "uploading"; file: File; progress: number }
  | { kind: "converting"; file: File; startedAt: number }
  | { kind: "error"; file?: File; code: string; message: string };

const ERROR_TITLES: Record<string, string> = {
  unsupported_type: "Unsupported file type",
  legacy_format: "Legacy Office format",
  macro_enabled: "Macros aren't accepted",
  encrypted_or_legacy: "Protected or legacy file",
  not_office_file: "Not a valid Office file",
  type_mismatch: "Extension doesn't match contents",
  corrupted: "The file appears damaged",
  file_too_large: "File too large",
  archive_limits: "Document exceeds safe limits",
  too_many_images: "Too many images",
  processing_timeout: "Conversion timed out",
  resource_limit: "Document exceeds resource limits",
  rate_limited: "Slow down a moment",
  server_busy: "Engine is busy",
  network: "Engine unreachable",
  empty_file: "Empty file",
};

export function Intake({
  phase,
  maxBytes,
  disabled,
  onFile,
  onReset,
  onCancel,
}: {
  phase: IntakePhase;
  maxBytes: number;
  disabled: boolean;
  onFile: (file: File) => void;
  onReset: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="relative rounded-[22px] border border-line bg-surface p-2 shadow-card">
      {phase.kind === "idle" && <Dropzone maxBytes={maxBytes} disabled={disabled} onFile={onFile} />}
      {(phase.kind === "uploading" || phase.kind === "converting") && <Progress phase={phase} onCancel={onCancel} />}
      {phase.kind === "error" && <ErrorPanel phase={phase} onReset={onReset} />}
    </div>
  );
}

function Dropzone({ maxBytes, disabled, onFile }: { maxBytes: number; disabled: boolean; onFile: (file: File) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const depth = useRef(0);

  const pick = (files: FileList | null) => {
    if (files && files.length > 0) onFile(files[0]);
  };

  return (
    <div
      onDragEnter={(e) => {
        e.preventDefault();
        depth.current += 1;
        setOver(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        depth.current -= 1;
        if (depth.current <= 0) setOver(false);
      }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        depth.current = 0;
        setOver(false);
        if (!disabled) pick(e.dataTransfer.files);
      }}
      className={`relative flex min-h-[330px] flex-col items-center justify-center overflow-hidden rounded-[16px] border-2 border-dashed px-6 py-10 text-center transition-all duration-300 ${
        over ? "scale-[0.99] border-accent bg-accent-soft" : "border-line-strong bg-surface-2"
      } ${disabled ? "opacity-60" : ""}`}
    >
      <div
        className={`mb-6 grid size-16 place-items-center rounded-2xl transition-all duration-300 ${
          over ? "-translate-y-1 bg-accent text-accent-ink" : "bg-ink text-paper"
        }`}
      >
        <UploadIcon size={26} />
      </div>
      <p className="text-xl font-semibold tracking-tight">{over ? "Release to convert" : "Drop a document to convert"}</p>
      <p className="mt-2 text-sm text-muted">Word or PowerPoint, up to {formatBytes(maxBytes)}</p>
      <button
        type="button"
        disabled={disabled}
        onClick={() => input.current?.click()}
        className="mt-6 rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper transition hover:-translate-y-0.5 hover:shadow-lg disabled:pointer-events-none"
      >
        Choose a file
      </button>
      <input
        ref={input}
        type="file"
        className="sr-only"
        tabIndex={-1}
        accept=".docx,.pptx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation"
        onChange={(e) => {
          pick(e.target.files);
          e.target.value = "";
        }}
      />
      <div className="mt-7 flex flex-wrap items-center justify-center gap-2 text-xs font-medium text-ink-2">
        <span className="rounded-md border border-line bg-surface px-2 py-1 font-mono">.docx</span>
        <span className="rounded-md border border-line bg-surface px-2 py-1 font-mono">.pptx</span>
        <span className="flex items-center gap-1.5 rounded-md px-2 py-1 text-muted">
          <LockIcon size={13} /> Deleted after processing
        </span>
      </div>
      {disabled && <p className="mt-4 text-xs text-danger">Start the conversion engine to enable uploads.</p>}
    </div>
  );
}

function useElapsed(startedAt: number | null) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (startedAt === null) return;
    const timer = window.setInterval(() => setNow(Date.now()), 100);
    return () => window.clearInterval(timer);
  }, [startedAt]);
  return startedAt === null ? 0 : Math.max(0, now - startedAt);
}

function Progress({ phase, onCancel }: { phase: Extract<IntakePhase, { kind: "uploading" | "converting" }>; onCancel: () => void }) {
  const uploading = phase.kind === "uploading";
  const elapsed = useElapsed(phase.kind === "converting" ? phase.startedAt : null);
  const kind = extensionOf(phase.file.name).slice(1);
  const percent = uploading ? Math.round(phase.progress * 100) : 100;

  return (
    <div className="flex min-h-[330px] flex-col justify-center rounded-[16px] bg-surface-2 px-6 py-8 sm:px-8" aria-live="polite">
      <div className="flex items-center gap-4">
        <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-accent-soft text-accent">
          <FileKindIcon kind={kind} size={22} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{phase.file.name}</p>
          <p className="text-sm text-muted">
            {kind.toUpperCase()} · {formatBytes(phase.file.size)}
          </p>
        </div>
      </div>

      <ol className="mt-8 space-y-5">
        <Step
          state={uploading ? "active" : "done"}
          title="Upload"
          detail={uploading ? `${percent}% sent` : "Received by the engine"}
          bar={uploading ? phase.progress : 1}
        />
        <Step
          state={uploading ? "pending" : "active"}
          title="Validate, parse and render"
          detail={uploading ? "Waiting for upload" : `Isolated worker running · ${(elapsed / 1000).toFixed(1)} s`}
          indeterminate={!uploading}
        />
        <Step state="pending" title="Results ready" detail="Preview, HTML and assets" />
      </ol>

      <button onClick={onCancel} className="mt-8 self-start text-sm font-medium text-muted underline-offset-4 hover:text-ink hover:underline">
        Cancel
      </button>
    </div>
  );
}

function Step({
  state,
  title,
  detail,
  bar,
  indeterminate,
}: {
  state: "pending" | "active" | "done";
  title: string;
  detail: string;
  bar?: number;
  indeterminate?: boolean;
}) {
  return (
    <li className={`flex gap-4 transition-opacity ${state === "pending" ? "opacity-45" : ""}`}>
      <span
        className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border text-xs ${
          state === "done"
            ? "border-success bg-success text-surface"
            : state === "active"
              ? "border-accent text-accent"
              : "border-line-strong text-muted"
        }`}
      >
        {state === "done" ? <CheckIcon size={14} /> : state === "active" ? <span className="size-2 rounded-full bg-accent pulse-dot" /> : null}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-sm font-semibold">{title}</p>
          <p className="truncate text-xs text-muted tabular-nums">{detail}</p>
        </div>
        {(bar !== undefined || indeterminate) && (
          <div className="relative mt-2 h-1.5 overflow-hidden rounded-full bg-line">
            {indeterminate ? (
              <div className="shimmer absolute inset-0 rounded-full bg-accent/70" />
            ) : (
              <div className="h-full rounded-full bg-accent transition-[width] duration-200" style={{ width: `${Math.round((bar ?? 0) * 100)}%` }} />
            )}
          </div>
        )}
      </div>
    </li>
  );
}

function ErrorPanel({ phase, onReset }: { phase: Extract<IntakePhase, { kind: "error" }>; onReset: () => void }) {
  return (
    <div className="flex min-h-[330px] flex-col justify-center rounded-[16px] bg-danger-soft/60 px-6 py-8 sm:px-8" role="alert">
      <div className="grid size-12 place-items-center rounded-xl bg-danger-soft text-danger">
        <AlertIcon size={22} />
      </div>
      <p className="mt-5 text-xl font-semibold tracking-tight">{ERROR_TITLES[phase.code] ?? "Conversion failed"}</p>
      <p className="mt-2 max-w-md text-[15px] leading-relaxed text-ink-2">{phase.message}</p>
      {phase.file && (
        <p className="mt-3 truncate text-sm text-muted">
          {phase.file.name} · {formatBytes(phase.file.size)}
        </p>
      )}
      <button onClick={onReset} className="mt-7 self-start rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-paper transition hover:-translate-y-0.5">
        Try another file
      </button>
    </div>
  );
}
