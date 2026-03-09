import { getBoats } from "@/lib/data";
import BoatDetailPanel from "@/components/BoatDetail";

export default function BoatsPage() {
  const boats = getBoats();

  return (
    <div>
      <h1 className="text-3xl font-bold text-navy mb-2">Boats</h1>
      <p className="text-gray-500 mb-6">
        {boats.length} boats across all seasons, sorted by total race appearances.
      </p>

      <BoatDetailPanel />

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-navy text-white text-left">
              <th className="px-4 py-2">Boat</th>
              <th className="px-4 py-2">Class</th>
              <th className="px-4 py-2">Sail #</th>
              <th className="px-4 py-2 text-right">Seasons</th>
              <th className="px-4 py-2 text-right">Races</th>
              <th className="px-4 py-2 text-right">Wins</th>
              <th className="px-4 py-2 text-right">Years</th>
            </tr>
          </thead>
          <tbody>
            {boats.map((b) => (
              <tr key={b.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-2">
                  <a
                    href={`#${b.id}`}
                    className="text-navy-light hover:underline font-medium"
                  >
                    {b.name}
                  </a>
                </td>
                <td className="px-4 py-2 text-gray-500">{b.class ?? "—"}</td>
                <td className="px-4 py-2 font-mono text-gray-500">{b.sail_number ?? "—"}</td>
                <td className="px-4 py-2 text-right font-mono">{b.seasons_raced}</td>
                <td className="px-4 py-2 text-right font-mono">{b.total_results}</td>
                <td className="px-4 py-2 text-right font-mono">{b.wins}</td>
                <td className="px-4 py-2 text-right text-xs text-gray-400">
                  {b.first_year}–{b.last_year}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
