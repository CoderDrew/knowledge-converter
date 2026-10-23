export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export type ProfileId = "clean" | "assets" | "freshservice";

export interface ProfileInfo {
  id: ProfileId;
  name: string;
  summary: string;
  html_filename: string;
}

export interface Health {
  status: string;
  version: string;
  limits: {
    max_upload_bytes: number;
    accepted_extensions: string[];
    result_ttl_seconds: number;
    conversion_timeout_seconds: number;
  };
  profiles: ProfileInfo[];
}

export interface AssetInfo {
  filename: string;
  content_type: string;
  width: number | null;
  height: number | null;
  size_bytes: number;
  alt: string | null;
  slide: number | null;
  context: string | null;
  occurrences: number;
  displayable: boolean;
}

export interface ConversionStats {
  headings: number;
  paragraphs: number;
  lists: number;
  list_items: number;
  tables: number;
  images: number;
  slides: number;
  words: number;
}

export interface Conversion {
  id: string;
  expires_at: string;
  title: string;
  source: { name: string; kind: "docx" | "pptx"; size_bytes: number };
  stats: ConversionStats;
  outline: { level: number; text: string; label?: string }[];
  warnings: string[];
  assets: AssetInfo[];
  profiles: (ProfileInfo & { html_bytes: number; package_bytes: number; files: string[] })[];
  timings_ms: { validate: number; parse: number; render: number; total: number };
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

const NETWORK_ERROR = new ApiError(
  "network",
  "The conversion engine could not be reached. Make sure the API is running, then try again.",
  0,
);

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch(`${API_BASE}/api/health`, { signal, cache: "no-store" });
  if (!response.ok) throw new ApiError("unavailable", "The conversion engine is unavailable.", response.status);
  return response.json();
}

function parseError(status: number, body: string): ApiError {
  try {
    const detail = JSON.parse(body).detail;
    if (detail && typeof detail === "object" && detail.message) return new ApiError(detail.code, detail.message, status);
    if (typeof detail === "string") return new ApiError("error", detail, status);
  } catch {
    /* fall through */
  }
  if (status === 413) return new ApiError("file_too_large", "The file is larger than the upload limit.", status);
  return new ApiError("error", "The conversion failed unexpectedly. Please try again.", status);
}

/**
 * Upload with real progress reporting. fetch() cannot observe upload
 * progress, so this uses XMLHttpRequest.
 */
export function uploadForConversion(
  file: File,
  handlers: { onUploadProgress: (fraction: number) => void; onUploaded: () => void },
): { promise: Promise<Conversion>; abort: () => void } {
  const xhr = new XMLHttpRequest();
  const promise = new Promise<Conversion>((resolve, reject) => {
    xhr.open("POST", `${API_BASE}/api/conversions`);
    xhr.responseType = "text";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) handlers.onUploadProgress(event.loaded / event.total);
    };
    xhr.upload.onload = () => handlers.onUploaded();
    xhr.onload = () => {
      if (xhr.status === 201) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new ApiError("error", "The engine returned an unreadable response.", xhr.status));
        }
      } else {
        reject(parseError(xhr.status, xhr.responseText));
      }
    };
    xhr.onerror = () => reject(NETWORK_ERROR);
    xhr.onabort = () => reject(new ApiError("aborted", "The upload was cancelled.", 0));
    const form = new FormData();
    form.append("file", file, file.name);
    xhr.send(form);
  });
  return { promise, abort: () => xhr.abort() };
}

export async function getSource(id: string, profile: ProfileId, signal?: AbortSignal): Promise<string> {
  const response = await fetch(urls.source(id, profile), { signal, cache: "no-store" });
  if (!response.ok) throw parseError(response.status, await response.text());
  return response.text();
}

export async function deleteConversion(id: string): Promise<void> {
  await fetch(`${API_BASE}/api/conversions/${id}`, { method: "DELETE" }).catch(() => undefined);
}

export const urls = {
  preview: (id: string, profile: ProfileId) => `${API_BASE}/api/conversions/${id}/profiles/${profile}/preview`,
  source: (id: string, profile: ProfileId) => `${API_BASE}/api/conversions/${id}/profiles/${profile}/source`,
  html: (id: string, profile: ProfileId) => `${API_BASE}/api/conversions/${id}/profiles/${profile}/html`,
  package: (id: string, profile: ProfileId) => `${API_BASE}/api/conversions/${id}/profiles/${profile}/package`,
  asset: (id: string, filename: string) => `${API_BASE}/api/conversions/${id}/assets/${encodeURIComponent(filename)}`,
};
