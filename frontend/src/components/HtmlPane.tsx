"use client";

import { useEffect, useMemo, useState } from "react";
import hljs from "highlight.js/lib/core";
import xml from "highlight.js/lib/languages/xml";
import { getSource, type Conversion, type ProfileId } from "@/lib/api";
import { elideDataUris, formatBytes } from "@/lib/format";
import { CheckIcon, CopyIcon } from "./icons";

hljs.registerLanguage("xml", xml);

const HIGHLIGHT_LIMIT = 400_000;

type Profile = Conversion["profiles"][number];

export function HtmlPane({ conversionId, profile }: { conversionId: string; profile: Profile }) {
  const [source, setSource] = useState<{ key: string; html: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const key = `${conversionId}:${profile.id}`;

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    getSource(conversionId, profile.id, controller.signal)
      .then((html) => setSource({ key, html }))
      .catch((e: Error) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [conversionId, profile.id, key]);

  const current = source?.key === key ? source.html : null;

  const display = useMemo(() => {
    if (current === null) return null;
    const { text, elided } = elideDataUris(current);
    const lines = text.split("\n").length;
    if (text.length > HIGHLIGHT_LIMIT) return { markup: null, text, elided, lines };
    // highlight.js escapes the source; its output contains only span markup.
    const markup = hljs.highlight(text, { language: "xml", ignoreIllegals: true }).value;
    return { markup, text, elided, lines };
  }, [current]);

  const copy = async () => {
    if (current === null) return;
    try {
      await navigator.clipboard.writeText(current);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("Copy failed. Your browser blocked clipboard access; use Download instead.");
    }
  };

  return (
    <div className="overflow-hidden rounded-[var(--mj-radius-md)] border border-line bg-code-bg text-code-ink">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-3 text-xs">
          <span className="rounded-[var(--mj-radius-sm)] bg-surface-2 px-2 py-1 font-semibold text-ink">{profile.html_filename}</span>
          <span className="text-muted">{formatBytes(profile.html_bytes)}</span>
          {display && <span className="hidden text-muted sm:inline">{display.lines.toLocaleString()} lines</span>}
        </div>
        <button
          onClick={copy}
          disabled={current === null}
          className="inline-flex items-center gap-1.5 rounded-full border border-line-strong bg-surface px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-accent-soft disabled:opacity-40"
        >
          {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
          {copied ? "Copied" : "Copy HTML"}
        </button>
      </div>
      {display && display.elided > 0 && (
        <p className="border-b border-line bg-surface px-4 py-2 text-xs text-muted">
          {display.elided} embedded image{display.elided === 1 ? " is" : "s are"} shortened for readability. Copy and download include the complete markup.
        </p>
      )}
      <div className="code-view max-h-[68vh] min-h-[420px] overflow-auto">
        {error && <p className="p-5 text-sm text-danger">{error}</p>}
        {!error && display === null && <p className="p-5 text-sm text-muted">Loading markup…</p>}
        {display && (
          <pre className="p-5 font-mono text-[12.5px] leading-[1.7] whitespace-pre-wrap break-words">
            {display.markup !== null ? <code dangerouslySetInnerHTML={{ __html: display.markup }} /> : <code>{display.text}</code>}
          </pre>
        )}
      </div>
    </div>
  );
}
