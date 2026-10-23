"use client";

import { useEffect, useMemo, useState } from "react";
import { urls, type Conversion, type ProfileId } from "@/lib/api";
import { formatBytes, formatSeconds, plural } from "@/lib/format";
import { AssetsPane } from "./AssetsPane";
import { HtmlPane } from "./HtmlPane";
import { PreviewPane } from "./PreviewPane";
import {
  AlertIcon, ArchiveIcon, ArrowLeftIcon, ClockIcon, CodeIcon, DownloadIcon, EyeIcon, FileKindIcon, ImageIcon, TrashIcon,
} from "./icons";

type View = "preview" | "html" | "assets";

export function Workspace({ conversion, onNew, onDiscard }: { conversion: Conversion; onNew: () => void; onDiscard: () => void }) {
  const [profileId, setProfileId] = useState<ProfileId>("clean");
  const [view, setView] = useState<View>("preview");
  const profile = conversion.profiles.find((p) => p.id === profileId) ?? conversion.profiles[0];
  const { stats, source } = conversion;

  const statItems = useMemo(() => {
    const items: [string, number][] =
      source.kind === "pptx"
        ? [["slides", stats.slides], ["images", stats.images], ["tables", stats.tables], ["words", stats.words]]
        : [["headings", stats.headings], ["paragraphs", stats.paragraphs], ["list items", stats.list_items], ["tables", stats.tables], ["images", stats.images], ["words", stats.words]];
    return items;
  }, [source.kind, stats]);

  const tabs: { id: View; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: "preview", label: "Preview", icon: <EyeIcon size={16} /> },
    { id: "html", label: "HTML", icon: <CodeIcon size={16} /> },
    { id: "assets", label: "Assets", icon: <ImageIcon size={16} />, count: conversion.assets.length },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 pt-6 pb-16 sm:px-6 lg:px-8">
      {/* ------------------------------------------------------------ summary */}
      <div className="animate-rise flex flex-wrap items-center justify-between gap-3">
        <button onClick={onNew} className="inline-flex items-center gap-2 rounded-full px-1 py-1 text-sm font-medium text-muted transition hover:text-ink">
          <ArrowLeftIcon size={16} /> New conversion
        </button>
        <ExpiryBadge expiresAt={conversion.expires_at} onDiscard={onDiscard} />
      </div>

      <section className="animate-rise animate-rise-delay-1 mt-4 rounded-[22px] border border-line bg-surface p-5 shadow-card sm:p-7">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-sm text-muted">
              <span className="inline-flex items-center gap-1.5 rounded-md bg-success-soft px-2 py-0.5 text-xs font-semibold text-success">
                Converted in {formatSeconds(conversion.timings_ms.total)}
              </span>
              <span className="inline-flex min-w-0 items-center gap-1.5 truncate">
                <FileKindIcon kind={source.kind} size={15} />
                <span className="truncate">{source.name}</span>
                <span className="shrink-0">· {formatBytes(source.size_bytes)}</span>
              </span>
            </div>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-balance break-words sm:text-[2rem] sm:leading-tight">{conversion.title}</h1>
            <dl className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm">
              {statItems.map(([label, value]) => (
                <div key={label} className="flex items-baseline gap-1.5">
                  <dt className="sr-only">{label}</dt>
                  <dd className="font-semibold tabular-nums">{value.toLocaleString()}</dd>
                  <span className="text-muted">{label}</span>
                </div>
              ))}
            </dl>
          </div>
          <div className="flex flex-wrap gap-2 lg:justify-end">
            <a
              href={urls.html(conversion.id, profile.id)}
              className="inline-flex items-center gap-2 rounded-full border border-line-strong bg-surface px-4 py-2.5 text-sm font-semibold transition hover:-translate-y-0.5 hover:border-ink"
            >
              <DownloadIcon size={16} /> {profile.html_filename}
              <span className="font-normal text-muted">{formatBytes(profile.html_bytes)}</span>
            </a>
            <a
              href={urls.package(conversion.id, profile.id)}
              className="inline-flex items-center gap-2 rounded-full bg-accent px-4 py-2.5 text-sm font-semibold text-accent-ink shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <ArchiveIcon size={16} /> Download ZIP
              <span className="font-normal opacity-80">{formatBytes(profile.package_bytes)}</span>
            </a>
          </div>
        </div>

        {/* profile switcher */}
        <div className="mt-6 border-t border-line pt-5">
          <p className="mb-3 font-mono text-[11px] font-semibold tracking-[0.16em] text-muted uppercase" id="profile-label">
            Output profile
          </p>
          <div className="grid gap-2 sm:grid-cols-3" role="radiogroup" aria-labelledby="profile-label">
            {conversion.profiles.map((p) => {
              const active = p.id === profile.id;
              return (
                <button
                  key={p.id}
                  role="radio"
                  aria-checked={active}
                  onClick={() => setProfileId(p.id)}
                  className={`flex flex-col items-stretch justify-start rounded-2xl border p-4 text-left transition-all duration-200 ${
                    active ? "border-accent bg-accent-soft/70 ring-1 ring-accent" : "border-line bg-surface-2 hover:border-line-strong"
                  }`}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-semibold tracking-tight">{p.name}</span>
                    <span className={`grid size-4 place-items-center rounded-full border ${active ? "border-accent bg-accent" : "border-line-strong"}`}>
                      {active && <span className="size-1.5 rounded-full bg-accent-ink" />}
                    </span>
                  </span>
                  <span className="mt-1.5 block text-[13px] leading-snug text-muted">{p.summary}</span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {conversion.warnings.length > 0 && <Notes warnings={conversion.warnings} />}

      {/* -------------------------------------------------------------- views */}
      <div className="animate-rise animate-rise-delay-2 mt-6 grid gap-6 lg:grid-cols-[250px_minmax(0,1fr)]">
        <aside className="hidden lg:block">
          <Outline conversion={conversion} />
        </aside>
        <section className="min-w-0">
          <div className="mb-4 flex items-center gap-1 overflow-x-auto rounded-full border border-line bg-surface p-1 sm:inline-flex" role="tablist" aria-label="Result views">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                id={`tab-${tab.id}`}
                aria-selected={view === tab.id}
                aria-controls={`panel-${tab.id}`}
                onClick={() => setView(tab.id)}
                className={`inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
                  view === tab.id ? "bg-ink text-paper" : "text-ink-2 hover:bg-surface-2"
                }`}
              >
                {tab.icon}
                {tab.label}
                {tab.count !== undefined && (
                  <span className={`rounded-full px-1.5 text-xs tabular-nums ${view === tab.id ? "bg-paper/20" : "bg-surface-2"}`}>{tab.count}</span>
                )}
              </button>
            ))}
          </div>
          <div role="tabpanel" id={`panel-${view}`} aria-labelledby={`tab-${view}`}>
            {view === "preview" && <PreviewPane conversionId={conversion.id} profileId={profile.id} title={conversion.title} />}
            {view === "html" && <HtmlPane conversionId={conversion.id} profile={profile} />}
            {view === "assets" && <AssetsPane conversion={conversion} profileId={profile.id} />}
          </div>
        </section>
      </div>
    </div>
  );
}

function Outline({ conversion }: { conversion: Conversion }) {
  return (
    <div className="sticky top-24 rounded-2xl border border-line bg-surface p-4">
      <p className="font-mono text-[11px] font-semibold tracking-[0.16em] text-muted uppercase">
        {conversion.source.kind === "pptx" ? "Slides" : "Structure"}
      </p>
      {conversion.outline.length === 0 ? (
        <p className="mt-3 text-sm text-muted">No headings were found in this document.</p>
      ) : (
        <ol className="mt-3 max-h-[60vh] space-y-0.5 overflow-y-auto pr-1 text-sm">
          {conversion.outline.map((item, index) => (
            <li
              key={`${index}-${item.text}`}
              className="flex gap-2 rounded-lg px-2 py-1.5 text-ink-2"
              style={{ paddingLeft: `${0.5 + Math.max(0, item.level - (conversion.source.kind === "pptx" ? 2 : 1)) * 0.85}rem` }}
            >
              {item.label && <span className="shrink-0 font-mono text-[11px] leading-5 text-muted">{item.label.replace("Slide ", "")}</span>}
              <span className="line-clamp-2">{item.text}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Notes({ warnings }: { warnings: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="animate-rise animate-rise-delay-2 mt-4 rounded-2xl border border-warn/25 bg-warn-soft px-4 py-3 text-sm sm:px-5">
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center gap-3 text-left">
        <AlertIcon size={17} className="shrink-0 text-warn" />
        <span className="flex-1 font-semibold">
          {plural(warnings.length, "conversion note")}
          <span className="font-normal text-ink-2"> — content that was simplified or needs a human check</span>
        </span>
        <span className="text-xs font-semibold text-warn">{open ? "Hide" : "Review"}</span>
      </button>
      {open && (
        <ul className="mt-3 space-y-1.5 border-t border-warn/20 pt-3 pl-8 text-ink-2">
          {warnings.map((w) => (
            <li key={w} className="list-disc">
              {w}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ExpiryBadge({ expiresAt, onDiscard }: { expiresAt: string; onDiscard: () => void }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 15_000);
    return () => window.clearInterval(timer);
  }, []);
  const minutes = Math.max(0, Math.round((new Date(expiresAt).getTime() - now) / 60_000));
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="inline-flex items-center gap-1.5 text-muted">
        <ClockIcon size={15} />
        {minutes > 0 ? `Results auto-delete in ${plural(minutes, "minute")}` : "Results have expired"}
      </span>
      <button
        onClick={onDiscard}
        className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-ink-2 transition hover:border-danger hover:text-danger"
      >
        <TrashIcon size={14} /> Delete now
      </button>
    </div>
  );
}
