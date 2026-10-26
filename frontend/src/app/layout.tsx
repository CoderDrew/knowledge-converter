import type { Metadata, Viewport } from "next";
// Brand tokens first: they declare the self-hosted OFL fonts (./fonts) and every --mj-* value.
import "./brand-tokens.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Knowledge Converter — Mindjax",
  description: "Convert Word and PowerPoint files into clean, publish-ready HTML with extracted images and portable export packages.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light",
  themeColor: "#FFFFFF",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  );
}
