import Link from "next/link";
import { getLeaderboards, getOverview } from "@/lib/data";
import { METHODOLOGY_SECTIONS } from "@/lib/methodology";

export default function MethodologyPage() {
  const overview = getOverview();
  const leaderboards = getLeaderboards();

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-2">Methodology</h1>
      <p className="text-gray-500 max-w-3xl mb-8">
        This page defines how public archive metrics are currently calculated.
        It exists for two reasons: to make the numbers interpretable, and to
        make it obvious when a definition needs review.
      </p>

      <div className="grid gap-4 md:grid-cols-3 mb-8">
        <MetricCard
          label="Canonical events"
          value={overview.canonical_event_count.toLocaleString()}
          note="Duplicate overall/division views collapsed into one logical event."
        />
        <MetricCard
          label="Core handicap events"
          value={overview.handicap_canonical_event_count.toLocaleString()}
          note="Canonical events remaining after special-event exclusions."
        />
        <MetricCard
          label="Excluded special events"
          value={leaderboards.excluded_event_count.toLocaleString()}
          note="Still visible in the archive, but excluded from default leaderboards."
        />
      </div>

      <div className="space-y-8">
        {METHODOLOGY_SECTIONS.map((section) => (
          <section key={section.title}>
            <h2 className="text-xl font-bold text-navy mb-3">{section.title}</h2>
            <div className="grid gap-4">
              {section.items.map((item) => (
                <article
                  key={item.term}
                  className="rounded-lg border border-border bg-card p-5 shadow-sm"
                >
                  <h3 className="text-lg font-semibold text-navy">{item.term}</h3>
                  <p className="mt-1 text-sm text-gray-500">{item.summary}</p>
                  <p className="mt-3 text-sm leading-6 text-gray-600">{item.detail}</p>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>

      <div className="mt-10 rounded-lg border border-border bg-cream/50 p-5 text-sm text-gray-600">
        Definitions will change as cleanup improves. When they do, the next step
        is to record that change in a project changelog so historical comparisons
        stay auditable.
        {" "}
        <Link
          href="/leaderboards/"
          className="text-navy-light hover:text-gold transition-colors"
        >
          Back to leaderboards
        </Link>
        .
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
      <div className="text-xs uppercase tracking-wider text-gray-400">{label}</div>
      <div className="mt-2 text-3xl font-bold text-navy">{value}</div>
      <div className="mt-2 text-sm text-gray-500">{note}</div>
    </div>
  );
}
