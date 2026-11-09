import { getAnalysis, getOverview } from "@/lib/data";
import { AnalysisCharts } from "./AnalysisCharts";

export default function AnalysisPage() {
  const analysis = getAnalysis();
  const { total_seasons, year_range } = getOverview();

  return (
    <div className="animate-fade-in">
      <div className="text-center mb-8 md:mb-10">
        <h1 className="text-3xl md:text-4xl font-bold text-navy mb-3">
          {total_seasons} Years of Racing
        </h1>
        <p className="text-gray-500 max-w-2xl mx-auto">
          Fleet trends, race performance, participation patterns, and conditions
          across {year_range.first}&ndash;{year_range.last} of Lunenburg Yacht Club handicap racing.
          Earlier results are not yet digitized &mdash; some boats may have longer histories than shown.
        </p>
      </div>

      <AnalysisCharts data={analysis} />
    </div>
  );
}
