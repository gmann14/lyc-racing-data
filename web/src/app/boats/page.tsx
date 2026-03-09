import { getBoats } from "@/lib/data";
import BoatDetailPanel from "@/components/BoatDetail";

export default function BoatsPage() {
  const boats = getBoats();

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-2">Boats</h1>
      <p className="text-gray-500 mb-6">
        {boats.length} boats across all seasons, sorted by total race
        appearances.
      </p>

      <BoatDetailPanel />

      <div className="bg-card rounded-lg shadow-sm border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-navy text-white text-left">
              <th className="px-4 py-3">Boat</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">Sail #</th>
              <th className="px-4 py-3 text-right">Seasons</th>
              <th className="px-4 py-3 text-right">Races</th>
              <th className="px-4 py-3 text-right">Wins</th>
              <th className="px-4 py-3 text-right">Years</th>
            </tr>
          </thead>
          <tbody>
            {boats.map((b) => (
              <tr
                key={b.id}
                className="border-b border-border/50 last:border-0 hover:bg-cream/50 transition-colors"
              >
                <td className="px-4 py-2.5">
                  <a
                    href={`#${b.id}`}
                    className="text-navy-light hover:text-gold font-medium transition-colors"
                  >
                    {b.name}
                  </a>
                </td>
                <td className="px-4 py-2.5 text-gray-400">
                  {b.class ?? "\u2014"}
                </td>
                <td className="px-4 py-2.5 font-mono text-gray-400">
                  {b.sail_number ?? "\u2014"}
                </td>
                <td className="px-4 py-2.5 text-right font-mono">
                  {b.seasons_raced}
                </td>
                <td className="px-4 py-2.5 text-right font-mono">
                  {b.total_results}
                </td>
                <td className="px-4 py-2.5 text-right font-mono font-semibold text-navy">
                  {b.wins}
                </td>
                <td className="px-4 py-2.5 text-right text-xs text-gray-400">
                  {b.first_year}&ndash;{b.last_year}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
