import { CodeIcon, DocIcon, ImageIcon, ShieldIcon, SlidesIcon, SparkIcon } from "./icons";

export function HeroCopy() {
  return (
    <div className="animate-rise">
      <p className="font-display text-xs tracking-[var(--mj-tracking-eyebrow)] text-accent uppercase">Document conversion</p>
      <h1 className="mt-5 text-[2rem] leading-[1.2] text-balance text-ink sm:text-[2.5rem]">
        Convert Word and PowerPoint to clean HTML
      </h1>
      <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-2 text-pretty">
        Drop a .docx or .pptx and get publish-ready semantic HTML, every embedded image, and a portable export package —
        without copy-paste cleanup.
      </p>
      <ConversionRail />
    </div>
  );
}

function ConversionRail() {
  return (
    <div className="mt-10 flex items-center gap-3 animate-rise animate-rise-delay-2" aria-hidden="true">
      <div className="flex gap-1.5">
        <Chip label="DOCX" icon={<DocIcon size={15} />} />
        <Chip label="PPTX" icon={<SlidesIcon size={15} />} className="hidden sm:flex" />
      </div>
      <div className="flow-line h-2 min-w-6 flex-1 rounded-full opacity-70 sm:max-w-36" />
      <div className="rounded-[var(--mj-radius-md)] bg-ink px-3 py-2 text-xs font-medium text-paper">engine</div>
      <div className="flow-line h-2 min-w-6 flex-1 rounded-full opacity-70 sm:max-w-36" />
      <div className="flex gap-1.5">
        <Chip label="HTML" icon={<CodeIcon size={15} />} accent />
        <Chip label="IMG" icon={<ImageIcon size={15} />} accent className="hidden sm:flex" />
      </div>
    </div>
  );
}

function Chip({ label, icon, accent, className = "flex" }: { label: string; icon: React.ReactNode; accent?: boolean; className?: string }) {
  return (
    <span
      className={`${className} items-center gap-1.5 rounded-[var(--mj-radius-md)] border px-2.5 py-2 text-xs font-semibold ${
        accent ? "border-accent/30 bg-accent-soft text-accent" : "border-line bg-surface text-ink-2"
      }`}
    >
      {icon}
      {label}
    </span>
  );
}

const FEATURES = [
  {
    icon: <SparkIcon size={20} />,
    title: "Structure, not just text",
    body: "Headings, nested lists, numbered steps, tables with merged cells, links, emphasis and callouts carry over as real semantic markup.",
  },
  {
    icon: <ImageIcon size={20} />,
    title: "Every image, in place",
    body: "Embedded screenshots are extracted in reading order, de-duplicated, sized, and referenced exactly where they appeared.",
  },
  {
    icon: <CodeIcon size={20} />,
    title: "Output profiles",
    body: "One conversion, three targets: self-contained Clean HTML, a styled HTML + Assets package, or a Freshservice knowledge article.",
  },
  {
    icon: <ShieldIcon size={20} />,
    title: "Built for untrusted files",
    body: "Structure checks, zip-bomb limits, sandboxed workers with timeouts, sanitised output, isolated previews, and automatic deletion.",
  },
];

export function HowItWorks() {
  return (
    <section className="border-t border-line bg-surface/60" aria-labelledby="how-heading">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.6fr]">
          <div>
            <p className="font-display text-xs tracking-[var(--mj-tracking-eyebrow)] text-accent uppercase">How it works</p>
            <h2 id="how-heading" className="mt-4 text-2xl leading-snug text-balance text-ink sm:text-[1.75rem]">
              Three steps from file to HTML
            </h2>
            <ol className="mt-8 space-y-4 text-[15px] text-ink-2">
              {[
                "Upload a Word or PowerPoint file.",
                "An isolated worker validates, parses and renders it.",
                "Review the preview, inspect the HTML, download the package.",
              ].map((step, index) => (
                <li key={step} className="flex gap-3">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-ink text-xs font-semibold text-paper">{index + 1}</span>
                  <span className="pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <article key={feature.title} className="rounded-[var(--mj-radius-md)] border border-line bg-surface p-6 transition-colors hover:border-accent">
                <div className="grid size-10 place-items-center rounded-[var(--mj-radius-md)] bg-accent-soft text-accent">{feature.icon}</div>
                <h3 className="mt-5 font-semibold tracking-tight">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{feature.body}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <p>© 2026 Mindjax</p>
        <p>No accounts, no tracking. Uploaded files are deleted after conversion; results expire automatically.</p>
      </div>
    </footer>
  );
}
