// Minimal static server for the exported site (`out/`), for local production
// checks. It applies the same out/_headers rules Cloudflare Pages would, so
// the production Content-Security-Policy is exercised locally.
import { createServer } from "node:http";
import { readFileSync, existsSync, statSync } from "node:fs";
import { extname, join, normalize, resolve } from "node:path";

const root = resolve("out");
const port = Number(process.env.PORT || 3000);
const types = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8", ".zip": "application/zip",
};

const headerFile = join(root, "_headers");
// Parse Cloudflare Pages _headers blocks: a path pattern line, then indented
// "Name: value" lines; "! Name" detaches a header set by an earlier rule.
const rules = [];
if (existsSync(headerFile)) {
  for (const line of readFileSync(headerFile, "utf8").split(/\r?\n/)) {
    if (/^\S/.test(line)) rules.push({ pattern: line.trim(), set: [], unset: [] });
    else if (rules.length && /^\s+!\s*\S/.test(line)) rules.at(-1).unset.push(line.trim().slice(1).trim().toLowerCase());
    else if (rules.length && /^\s+\S+:/.test(line)) {
      const i = line.indexOf(":");
      rules.at(-1).set.push([line.slice(0, i).trim(), line.slice(i + 1).trim()]);
    }
  }
}
const matches = (pattern, pathname) =>
  new RegExp(`^${pattern.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*")}$`).test(pathname);
function headersFor(pathname) {
  const out = new Map();
  for (const rule of rules.filter((r) => matches(r.pattern, pathname))) {
    for (const name of rule.unset) out.delete(name);
    for (const [name, value] of rule.set) out.set(name.toLowerCase(), [name, value]);
  }
  return [...out.values()];
}

createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");
  let path = normalize(join(root, decodeURIComponent(url.pathname)));
  if (!path.startsWith(root)) {
    res.writeHead(403).end();
    return;
  }
  if (existsSync(path) && statSync(path).isDirectory()) path = join(path, "index.html");
  if (!existsSync(path) && existsSync(`${path}.html`)) path = `${path}.html`;
  if (!existsSync(path) || path.endsWith("_headers")) {
    res.writeHead(404, { "Content-Type": "text/plain" }).end("Not found");
    return;
  }
  for (const [name, value] of headersFor(url.pathname)) res.setHeader(name, value);
  res.writeHead(200, { "Content-Type": types[extname(path)] || "application/octet-stream" });
  res.end(readFileSync(path));
}).listen(port, "127.0.0.1", () => console.log(`Serving out/ at http://localhost:${port}`));
