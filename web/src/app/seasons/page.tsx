import Link from "next/link";
import { getSeasons } from "@/lib/data";

export default function SeasonsPage() {
  const seasons = getSeasons();

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-6">Seasons</h1>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {seasons.map((s) => (
          <Link
            key={s.year}
            href={`/seasons/${s.year}/`}
            className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
          >
            <div className="text-2xl font-bold text-navy">{s.year}</div>
            <div className="text-sm text-gray-500 mt-1">
              {s.event_count} events
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {s.tns_count > 0 && <span>{s.tns_count} TNS</span>}
              {s.trophy_count > 0 && (
                <span className="ml-2">{s.trophy_count} trophies</span>
              )}
              {s.championship_count > 0 && (
                <span className="ml-2">{s.championship_count} champ</span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
