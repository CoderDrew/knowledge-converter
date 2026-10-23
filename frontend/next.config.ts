import type { NextConfig } from "next";

// Static export: the site is plain HTML/JS that any static host (Cloudflare
// Pages in production) can serve. All conversion work happens in the API.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
