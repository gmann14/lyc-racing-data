import { getTrophies } from "@/lib/data";
import TrophiesClient from "./trophies-client";

export default function TrophiesPage() {
  const trophies = getTrophies();
  return <TrophiesClient trophies={trophies} />;
}
