import { getBoats } from "@/lib/data";
import ComparePanel from "@/components/ComparePanel";

export default function ComparePage() {
  const boats = getBoats();

  return (
    <div>
      <h1 className="text-2xl md:text-3xl font-bold text-navy mb-2">
        Head-to-Head
      </h1>
      <p className="text-gray-500 mb-6">
        Compare two boats across their shared races to see who comes out on top.
      </p>
      <ComparePanel boats={boats} />
    </div>
  );
}
