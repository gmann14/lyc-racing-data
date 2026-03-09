import { getBoats } from "@/lib/data";
import BoatDetailPanel from "@/components/BoatDetail";
import BoatsTable from "@/components/BoatsTable";

export default function BoatsPage() {
  const boats = getBoats();

  return (
    <div>
      <h1 className="text-2xl md:text-3xl font-bold text-navy mb-2">Boats</h1>
      <p className="text-gray-500 mb-6">
        {boats.length} boats across all seasons. Sort by column or search by
        name, class, or sail number.
      </p>

      <BoatDetailPanel />
      <BoatsTable boats={boats} />
    </div>
  );
}
