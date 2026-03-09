import { getSeasons } from "@/lib/data";
import SeasonDetailPanel from "@/components/SeasonDetail";

export default function SeasonsPage() {
  const seasons = getSeasons();

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-2">Seasons</h1>
      <p className="text-gray-500 mb-6">
        {seasons.length} seasons of racing, from {seasons[seasons.length - 1]?.year ?? "?"} to {seasons[0]?.year ?? "?"}.
      </p>

      <SeasonDetailPanel />

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {seasons.map((s) => (
          <a
            key={s.year}
            href={`#${s.year}`}
            className="bg-card rounded-lg border border-border p-4 card-hover block"
          >
            <div className="text-2xl font-bold text-navy">{s.year}</div>
            <div className="text-sm text-gray-500 mt-1">
              {s.handicap_canonical_event_count} core events
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {s.tns_count > 0 && (
                <span className="text-xs bg-blue-light text-navy-light px-1.5 py-0.5 rounded">
                  {s.tns_count} TNS
                </span>
              )}
              {s.trophy_count > 0 && (
                <span className="text-xs bg-gold-light/40 text-navy-light px-1.5 py-0.5 rounded">
                  {s.trophy_count} trophy
                </span>
              )}
              {s.championship_count > 0 && (
                <span className="text-xs bg-navy/10 text-navy-light px-1.5 py-0.5 rounded">
                  {s.championship_count} champ
                </span>
              )}
              {s.special_event_count > 0 && (
                <span className="text-xs bg-red-50 text-red-700 px-1.5 py-0.5 rounded">
                  {s.special_event_count} special
                </span>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
