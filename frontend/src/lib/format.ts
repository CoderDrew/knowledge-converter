export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value >= 100 ? Math.round(value) : value.toFixed(1).replace(/\.0$/, "")} ${units[unit]}`;
}

export function formatSeconds(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(ms < 10_000 ? 2 : 1)} s`;
}

export function plural(count: number, word: string, pluralWord = `${word}s`): string {
  return `${count.toLocaleString()} ${count === 1 ? word : pluralWord}`;
}

export const ACCEPTED_EXTENSIONS = [".docx", ".pptx"] as const;

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot).toLowerCase();
}

/** Client-side checks give instant feedback; the server re-validates everything. */
export function validateFile(file: File, maxBytes: number): string | null {
  const ext = extensionOf(file.name);
  if (ext === ".doc" || ext === ".ppt") {
    return `Legacy ${ext} files aren't supported. Open the file in Office and save it as ${ext}x.`;
  }
  if (!ACCEPTED_EXTENSIONS.includes(ext as (typeof ACCEPTED_EXTENSIONS)[number])) {
    return "Choose a Word (.docx) or PowerPoint (.pptx) file.";
  }
  if (file.size === 0) return "That file is empty.";
  if (file.size > maxBytes) return `That file is ${formatBytes(file.size)}. The limit is ${formatBytes(maxBytes)}.`;
  return null;
}

/** Shorten base64 image payloads so the HTML view stays readable and fast. */
export function elideDataUris(html: string): { text: string; elided: number } {
  let elided = 0;
  const text = html.replace(/data:(image\/[a-z0-9.+-]+);base64,([A-Za-z0-9+/=]{64,})/g, (_match, type: string, payload: string) => {
    elided += 1;
    return `data:${type};base64,…[${formatBytes(Math.floor((payload.length * 3) / 4))} embedded]`;
  });
  return { text, elided };
}
