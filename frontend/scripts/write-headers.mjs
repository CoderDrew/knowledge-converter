// Writes out/_headers (Cloudflare Pages format) after `next build`.
// The policy is derived from NEXT_PUBLIC_API_BASE_URL so the site may only
// talk to, embed, and load images from its own conversion API.
import { readFileSync, writeFileSync, existsSync } from "node:fs";

function readEnvFile(path) {
  if (!existsSync(path)) return {};
  return Object.fromEntries(
    readFileSync(path, "utf8")
      .split(/\r?\n/)
      .filter((line) => line && !line.startsWith("#") && line.includes("="))
      .map((line) => [line.slice(0, line.indexOf("=")).trim(), line.slice(line.indexOf("=") + 1).trim()]),
  );
}

const env = { ...readEnvFile(".env.production"), ...readEnvFile(".env.local"), ...process.env };
const demo = env.NEXT_PUBLIC_DEMO_MODE === "1";
// Demo mode has no API: everything is served from this site's own origin.
const api = demo ? "'self'" : new URL(env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").origin;

const csp = [
  "default-src 'self'",
  // Next.js static export bootstraps with inline scripts.
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self'",
  `img-src 'self' data: ${api}`,
  `connect-src 'self' ${api}`,
  `frame-src ${api}`,
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
].join("; ");

const headers = `/*
  Content-Security-Policy: ${csp}
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
  Cross-Origin-Opener-Policy: same-origin
${demo ? demoHeaders() : ""}`;

// Pre-rendered demo files: drop the app CSP and serve them like the API does,
// sandboxed (no scripts, opaque origin) and frameable only by this site.
function demoHeaders() {
  return `
/demo/*
  ! Content-Security-Policy
  Content-Security-Policy: default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; frame-ancestors 'self'; sandbox
`;
}

writeFileSync("out/_headers", headers);
console.log(`Wrote out/_headers (${demo ? "demo mode" : `API origin: ${api}`})`);
