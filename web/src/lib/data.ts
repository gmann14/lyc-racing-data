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
  handicap_boat_count?: number;
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

export interface BoatOwner {
  owner_name: string;
  year_start: number | null;
  year_end: number | null;
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
  owners?: BoatOwner[];
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

export interface RaceWeather {
  temp_c: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  wind_gust_kmh: number | null;
  precipitation_mm: number | null;
  conditions: string | null;
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
  weather: RaceWeather | null;
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
  avg_finish_pct?: number;
  avg_finish?: number;
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
  best_avg_finish_pct: LeaderboardEntry[];
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

// --- Analysis types ---

export interface FleetByYear {
  year: number;
  unique_boats: number;
  tns_boats: number;
  trophy_boats: number;
}

export interface NewBoatsByYear {
  year: number;
  new_boats: number;
}

export interface ReturnRate {
  year: number;
  boats: number;
  returning: number;
  rate: number;
}

export interface ClassCount {
  class: string;
  count: number;
}

export interface AvgFieldSize {
  year: number;
  event_type: string;
  avg_field_size: number;
}

export interface RaceLength {
  year: number;
  event_type: string;
  avg_elapsed: string;
  avg_elapsed_seconds: number;
  avg_corrected: string | null;
  avg_corrected_seconds: number | null;
  sample_size: number;
}

export interface ParticipationLeader {
  id: number;
  name: string;
  class: string | null;
  sail_number: string | null;
  races: number;
  seasons: number;
  first_year: number;
  last_year: number;
  wins: number;
}

export interface StreakLeader {
  id: number;
  name: string;
  streak: number;
  start: number;
  end: number;
}

export interface TnsMonthData {
  year: number;
  month: string;
  race_nights: number;
  unique_boats: number;
  total_results: number;
}

export interface MonthlyWeather {
  month: string;
  avg_temp_c: number;
  avg_wind_kmh: number;
  race_days: number;
}

export interface AnalysisData {
  fleet_trends: {
    fleet_by_year: FleetByYear[];
    new_boats_by_year: NewBoatsByYear[];
    return_rates: ReturnRate[];
    class_distribution: Record<string, ClassCount[]>;
    avg_field_size: AvgFieldSize[];
  };
  race_lengths: RaceLength[];
  participation: {
    most_races: ParticipationLeader[];
    longest_streaks: StreakLeader[];
  };
  tns: {
    by_year_month: TnsMonthData[];
  };
  weather: {
    wind_distribution: Record<string, number>;
    monthly_averages: MonthlyWeather[];
    total_dates: number;
  };
}

export function getAnalysis(): AnalysisData {
  return readJson<AnalysisData>("analysis.json");
}
