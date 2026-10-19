import { test } from "node:test";
import assert from "node:assert/strict";
import type { Standing } from "./data.ts";
import { formatScope, groupStandingsByScope } from "./standings.ts";

function standing(summary_scope: string, rank: number, display_name = `Boat ${rank}`): Standing {
  return {
    rank,
    summary_scope,
    fleet: null,
    division: null,
    phrf_rating: null,
    total_points: null,
    nett_points: rank,
    display_name,
    participant_type: "boat",
    sail_number: null,
    raw_class: null,
    boat_name: display_name,
    boat_class: null,
    boat_id: null,
  };
}

test("formatScope labels fleets, divisions and classes", () => {
  assert.equal(formatScope("overall"), "Overall");
  assert.equal(formatScope("a_fleet"), "A Fleet");
  assert.equal(formatScope("p_division"), "P Division");
  assert.equal(formatScope("iod_division"), "IOD Division");
  assert.equal(formatScope("c420_class"), "C420 Class");
});

test("formatScope turns digit pairs into decimals and drops _year", () => {
  assert.equal(formatScope("laser_4_7_fleet"), "Laser 4.7 Fleet");
  assert.equal(formatScope("2_4_mr_class"), "2.4 mR Class");
  assert.equal(formatScope("2015_year"), "2015");
});

test("groupStandingsByScope returns fleet tables when there is no overall scope", () => {
  // 2025 Glube Cup August TNS: only a_fleet / b_fleet standings
  const groups = groupStandingsByScope([
    standing("a_fleet", 1),
    standing("a_fleet", 2),
    standing("b_fleet", 1),
  ]);
  assert.deepEqual(
    groups.map((g) => [g.scope, g.rows.length]),
    [
      ["a_fleet", 2],
      ["b_fleet", 1],
    ],
  );
});

test("groupStandingsByScope puts overall first and keeps data order otherwise", () => {
  const groups = groupStandingsByScope([
    standing("a_fleet", 1),
    standing("b_fleet", 1),
    standing("overall", 1),
    standing("s_fleet", 1),
  ]);
  assert.deepEqual(
    groups.map((g) => g.scope),
    ["overall", "a_fleet", "b_fleet", "s_fleet"],
  );
});

test("groupStandingsByScope treats a missing scope as overall and handles empty input", () => {
  assert.deepEqual(groupStandingsByScope([]), []);
  const groups = groupStandingsByScope([standing("", 1)]);
  assert.equal(groups[0]?.scope, "overall");
});
