"use client";

import { urls, type Conversion, type ProfileId } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import { DownloadIcon, ImageIcon } from "./icons";

const FOLDER: Record<ProfileId, string> = { clean: "assets/", assets: "assets/images/", freshservice: "images/" };

export function AssetsPane({ conversion, profileId }: { conversion: Conversion; profileId: ProfileId }) {
  const profile = conversion.profiles.find((p) => p.id === profileId)!;
  const otherFiles = profile.files.filter((f) => !f.startsWith(FOLDER[profileId]) || f.endsWith(".css"));

  return (
    <div className="space-y-5">
      {conversion.assets.length === 0 ? (
        <div className="grid min-h-[300px] place-items-center rounded-[18px] border border-dashed border-line-strong bg-surface p-8 text-center">
          <div>
            <ImageIcon size={28} className="mx-auto text-muted" />
            <p className="mt-3 font-semibold">No embedded images</p>
            <p className="mt-1 text-sm text-muted">This document contains text only.</p>
          </div>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {conversion.assets.map((asset, index) => (
            <li key={asset.filename} className="group overflow-hidden rounded-2xl border border-line bg-surface transition hover:-translate-y-0.5 hover:shadow-card">
              <div className="relative grid aspect-[16/10] place-items-center overflow-hidden border-b border-line bg-[repeating-conic-gradient(var(--surface-2)_0%_25%,var(--surface)_0%_50%)] bg-[length:16px_16px]">
                {asset.displayable ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={urls.asset(conversion.id, asset.filename)}
                    alt={asset.alt ?? `Extracted image ${index + 1}`}
                    loading="lazy"
                    className="max-h-full max-w-full object-contain p-3 transition duration-300 group-hover:scale-[1.02]"
                  />
                ) : (
                  <div className="p-4 text-center text-xs text-muted">
                    <ImageIcon size={22} className="mx-auto" />
                    <p className="mt-2">{asset.content_type}</p>
                    <p>Not displayable in browsers</p>
                  </div>
                )}
                <span className="absolute top-2 left-2 rounded-md bg-ink/85 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-paper">
                  {String(index + 1).padStart(2, "0")}
                </span>
                {asset.occurrences > 1 && (
                  <span className="absolute top-2 right-2 rounded-md bg-accent px-1.5 py-0.5 text-[10px] font-semibold text-accent-ink">
                    used {asset.occurrences}×
                  </span>
                )}
              </div>
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="min-w-0 truncate font-mono text-[13px] font-semibold" title={`${FOLDER[profileId]}${asset.filename}`}>
                    <span className="text-muted">{FOLDER[profileId]}</span>
                    {asset.filename}
                  </p>
                  <a
                    href={`${urls.asset(conversion.id, asset.filename)}?download=1`}
                    className="shrink-0 rounded-md p-1 text-muted transition hover:bg-surface-2 hover:text-ink"
                    aria-label={`Download ${asset.filename}`}
                  >
                    <DownloadIcon size={15} />
                  </a>
                </div>
                <p className="mt-1 text-xs text-muted tabular-nums">
                  {asset.width && asset.height ? `${asset.width} × ${asset.height} · ` : ""}
                  {formatBytes(asset.size_bytes)}
                </p>
                {(asset.slide || asset.context) && (
                  <p className="mt-2 line-clamp-2 text-xs text-ink-2">
                    {asset.slide ? <span className="font-semibold">Slide {asset.slide}</span> : <span className="text-muted">Near</span>}
                    {asset.context ? ` · ${asset.context}` : ""}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-2xl border border-line bg-surface p-5">
        <p className="font-mono text-[11px] font-semibold tracking-[0.16em] text-muted uppercase">Package contents · {profile.name}</p>
        <ul className="mt-3 flex flex-wrap gap-2 font-mono text-xs">
          {otherFiles.map((file) => (
            <li key={file} className="rounded-md border border-line bg-surface-2 px-2 py-1">
              {file}
            </li>
          ))}
          {conversion.assets.length > 0 && (
            <li className="rounded-md border border-dashed border-line-strong px-2 py-1 text-muted">
              {FOLDER[profileId]}… {conversion.assets.length} image{conversion.assets.length === 1 ? "" : "s"}
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}
