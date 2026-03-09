import fs from "fs";
import path from "path";

const DATA_DIR = path.join(process.cwd(), "public", "data");

function readJson<T>(relativePath: string): T {
  const filePath = path.join(DATA_DIR, relativePath);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

export interface Overview {
  total_seasons: number;
  total_events: number;
  canonical_event_count: number;
  total_races: number;
  total_results: number;
  total_boats: number;
  handicap_events: number;
  handicap_canonical_event_count: number;
  handicap_results: number;
  year_range: { first: number; last: number };
}

export interface SeasonSummary {
  year: number;
  event_count: number;
  special_event_count: number;
  handicap_event_count: number;
  canonical_event_count: number;
  handicap_canonical_event_count: number;
  tns_count: number;
  trophy_count: number;
  championship_count: number;
}

export interface EventVariantSource {
  event_id: number;
  name: string;
  source_file: string | null;
  race_count: number;
  standings_count: number;
  result_count: number;
  is_primary: boolean;
}

export interface EventSummary {
  id: number;
  name: string;
  slug: string;
  event_type: string;
  month: string | null;
  source_format: string;
  races_sailed: number | null;
  entries: number | null;
  canonical_event_id: number;
  is_variant_view: boolean;
  variant_view_count: number;
  variant_sources: EventVariantSource[];
  special_event_kind: string | null;
  exclude_from_handicap_stats: boolean;
  special_event_reasons: string[];
}

export interface BoatSummary {
  id: number;
  name: string;
  class: string | null;
  sail_number: string | null;
  club: string | null;
}

export interface SeasonDetail {
  year: number;
  events: EventSummary[];
  boats: BoatSummary[];
}

export interface BoatListItem {
  id: number;
  name: string;
  class: string | null;
  sail_number: string | null;
  club: string | null;
  total_results: number;
  seasons_raced: number;
  first_year: number;
  last_year: number;
  wins: number;
}

export interface BoatDetail {
  id: number;
  name: string;
  class: string | null;
  sail_number: string | null;
  club: string | null;
  stats: {
    total_races: number;
    seasons: number;
    first_year: number;
    last_year: number;
    wins: number;
    podiums: number;
    avg_finish: number | null;
  };
  seasons: Array<{
    year: number;
    races: number;
    wins: number;
    avg_finish: number | null;
  }>;
  trophies: Array<{
    year: number;
    name: string;
    event_type: string;
    summary_scope: string;
    nett_points: number | null;
  }>;
}

export interface RaceResult {
  rank: number | null;
  fleet: string | null;
  division: string | null;
  phrf_rating: number | null;
  start_time: string | null;
  finish_time: string | null;
  elapsed_time: string | null;
  corrected_time: string | null;
  bcr: number | null;
  points: number | null;
  status: string | null;
  display_name: string;
  participant_type: string;
  sail_number: string | null;
  raw_class: string | null;
  boat_name: string | null;
  boat_class: string | null;
  boat_id: number | null;
}

export interface Race {
  id: number;
  race_key: string | null;
  race_number: number | null;
  date: string | null;
  start_time: string | null;
  wind_direction: string | null;
  wind_speed_knots: number | null;
  course: string | null;
  distance_nm: number | null;
  notes: string | null;
  results: RaceResult[];
}

export interface Standing {
  rank: number;
  summary_scope: string;
  fleet: string | null;
  division: string | null;
  phrf_rating: number | null;
  total_points: number | null;
  nett_points: number | null;
  display_name: string;
  participant_type: string;
  sail_number: string | null;
  raw_class: string | null;
  boat_name: string | null;
  boat_class: string | null;
  boat_id: number | null;
}

export interface EventDetail {
  id: number;
  year: number;
  name: string;
  slug: string;
  event_type: string;
  month: string | null;
  source_format: string;
  races_sailed: number | null;
  entries: number | null;
  canonical_event_id: number;
  is_variant_view: boolean;
  variant_sources: EventVariantSource[];
  special_event_kind: string | null;
  exclude_from_handicap_stats: boolean;
  special_event_reasons: string[];
  standings: Standing[];
  races: Race[];
}

export interface LeaderboardEntry {
  id: number;
  name: string;
  class: string | null;
  sail_number: string | null;
  wins?: number;
  total_races?: number;
  win_pct?: number;
  seasons?: number;
  first_year?: number;
  last_year?: number;
  trophy_wins?: number;
  unique_boats?: number;
  total_results?: number;
}

export interface Leaderboards {
  most_wins: LeaderboardEntry[];
  most_seasons: LeaderboardEntry[];
  most_trophies: LeaderboardEntry[];
  best_win_pct: LeaderboardEntry[];
  excluded_event_count: number;
  fleet_by_year: Array<{
    year: number;
    unique_boats: number;
    total_results: number;
  }>;
}

export interface TrophyWinner {
  year: number;
  event_id: number;
  display_name: string;
  boat_name: string | null;
  boat_class: string | null;
  boat_id: number | null;
  nett_points: number | null;
}

export interface Trophy {
  name: string;
  slug: string;
  event_type: string;
  winners: TrophyWinner[];
}

export function getOverview(): Overview {
  return readJson<Overview>("overview.json");
}

export function getSeasons(): SeasonSummary[] {
  return readJson<SeasonSummary[]>("seasons.json");
}

export function getBoats(): BoatListItem[] {
  return readJson<BoatListItem[]>("boats.json");
}

export function getLeaderboards(): Leaderboards {
  return readJson<Leaderboards>("leaderboards.json");
}

export function getTrophies(): Trophy[] {
  return readJson<Trophy[]>("trophies.json");
}

export function getAllYears(): number[] {
  const seasons = getSeasons();
  return seasons.map((s) => s.year);
}
