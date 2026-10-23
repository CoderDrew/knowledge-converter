import { CodeIcon, DocIcon, ImageIcon, ShieldIcon, SlidesIcon, SparkIcon } from "./icons";

export function HeroCopy() {
  return (
    <div className="animate-rise">
      <p className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs font-semibold tracking-wide text-ink-2">
        <span className="size-1.5 rounded-full bg-accent" />
        Document automation
      </p>
      <h1 className="mt-6 text-[2.6rem] leading-[1.02] font-semibold tracking-[-0.035em] text-balance sm:text-6xl">
        Word &amp; PowerPoint in.
        <br />
        <span className="font-display text-[1.08em] font-normal italic tracking-[-0.02em] text-accent">Clean HTML</span> out.
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
      <div className="rounded-xl bg-ink px-3 py-2 font-mono text-xs font-medium text-paper">engine</div>
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
      className={`${className} items-center gap-1.5 rounded-xl border px-2.5 py-2 font-mono text-[11px] font-semibold shadow-sm ${
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
            <p className="font-mono text-xs font-semibold tracking-[0.18em] text-accent uppercase">How it works</p>
            <h2 id="how-heading" className="mt-4 text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              From a manual cleanup chore to a workflow measured in{" "}
              <span className="font-display font-normal italic">seconds</span>.
            </h2>
            <ol className="mt-8 space-y-4 text-[15px] text-ink-2">
              {[
                "Upload a Word or PowerPoint file.",
                "An isolated worker validates, parses and renders it.",
                "Review the preview, inspect the HTML, download the package.",
              ].map((step, index) => (
                <li key={step} className="flex gap-3">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-ink font-mono text-[11px] text-paper">{index + 1}</span>
                  <span className="pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <article key={feature.title} className="rounded-2xl border border-line bg-surface p-6 transition hover:-translate-y-0.5 hover:shadow-card">
                <div className="grid size-10 place-items-center rounded-xl bg-accent-soft text-accent">{feature.icon}</div>
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
        <p>
          A <span className="font-semibold text-ink">Mindjax</span> Innovation Lab project.
        </p>
        <p>No accounts, no tracking. Uploaded files are deleted after conversion; results expire automatically.</p>
      </div>
    </footer>
  );
}
