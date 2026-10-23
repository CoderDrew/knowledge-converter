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
  ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2", ".txt": "text/plain",
};

const headerFile = join(root, "_headers");
const extraHeaders = existsSync(headerFile)
  ? readFileSync(headerFile, "utf8").split(/\r?\n/).filter((l) => /^\s+\S+:/.test(l)).map((l) => {
      const i = l.indexOf(":");
      return [l.slice(0, i).trim(), l.slice(i + 1).trim()];
    })
  : [];

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
  for (const [name, value] of extraHeaders) res.setHeader(name, value);
  res.writeHead(200, { "Content-Type": types[extname(path)] || "application/octet-stream" });
  res.end(readFileSync(path));
}).listen(port, "127.0.0.1", () => console.log(`Serving out/ at http://localhost:${port}`));
