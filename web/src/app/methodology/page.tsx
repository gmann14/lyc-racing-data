import Link from "next/link";
import { getLeaderboards, getOverview } from "@/lib/data";
import {
  METHODOLOGY_SECTIONS,
  PUBLIC_METRIC_DEFINITIONS,
} from "@/lib/methodology";

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
          label="Unique events"
          value={overview.canonical_event_count.toLocaleString()}
          note="Duplicate overall/division result pages are combined into one event record."
        />
        <MetricCard
          label="Core handicap events"
          value={overview.handicap_canonical_event_count.toLocaleString()}
          note="Core event records remaining after special-event exclusions."
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

        <section>
          <h2 className="text-xl font-bold text-navy mb-3">Metric Definitions</h2>
          <p className="mb-4 max-w-3xl text-sm text-gray-600">
            Some of the next analysis pages are definition-sensitive. Thursday
            night race length, for example, can legitimately mean elapsed time
            or corrected time, and can be averaged at the race level, the
            finisher level, or the winner-only level. These definitions are
            tracked here so future charts stay auditable.
          </p>
          <div className="grid gap-4">
            {PUBLIC_METRIC_DEFINITIONS.map((metric) => (
              <article
                key={metric.key}
                className="rounded-lg border border-border bg-card p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-navy">{metric.label}</h3>
                    <p className="mt-1 text-sm text-gray-500">{metric.summary}</p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${
                      metric.status === "live"
                        ? "bg-teal-50 text-teal-700"
                        : "bg-gold/15 text-navy"
                    }`}
                  >
                    {metric.status}
                  </span>
                </div>
                <dl className="mt-4 grid gap-3 text-sm text-gray-600 md:grid-cols-2">
                  <DefinitionRow label="Time Basis" value={metric.dimensions.timeBasis} />
                  <DefinitionRow label="Participant Scope" value={metric.dimensions.participantScope} />
                  <DefinitionRow label="Event Scope" value={metric.dimensions.eventScope} />
                  <DefinitionRow label="Aggregation" value={metric.dimensions.aggregation} />
                  {metric.dimensions.inclusionNotes ? (
                    <DefinitionRow
                      label="Notes"
                      value={metric.dimensions.inclusionNotes}
                    />
                  ) : null}
                </dl>
              </article>
            ))}
          </div>
        </section>
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

function DefinitionRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-gray-400">{label}</dt>
      <dd className="mt-1 leading-6">{value}</dd>
    </div>
  );
}
