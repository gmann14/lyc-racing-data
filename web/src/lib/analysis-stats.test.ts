import { test } from "node:test";
import assert from "node:assert/strict";
import { leaderKey, leaderName, topBy, weightedMonthlyAvg } from "./analysis-stats.ts";

test("leaderKey keeps owner-merged rows with the same boat id distinct", () => {
  // Buzz (id 64) appears under two owners in most_active / most_races
  const a = leaderKey({ id: 64, owner: "Barry Eisener" });
  const b = leaderKey({ id: 64, owner: "Bernd Hackstein" });
  assert.notEqual(a, b);
  assert.equal(leaderKey({ id: 23 }), "|23");
  assert.equal(leaderKey({ id: 23, owner: null }), "|23");
});

test("leaderName joins merged boat names", () => {
  assert.equal(leaderName({ name: "Sly Fox", boat_names: ["Sly Fox", "Mojo"] }), "Sly Fox / Mojo");
  assert.equal(leaderName({ name: "Poohsticks", boat_names: ["Poohsticks"] }), "Poohsticks");
  assert.equal(leaderName({ name: "Echo" }), "Echo");
});

const rows = [
  { name: "Sly Fox", boat_names: ["Sly Fox", "Mojo"], races: 433, wins: 58, seasons: 27 },
  { name: "Poohsticks", races: 418, wins: 109, seasons: 27 },
  { name: "Rumble Fish", races: 325, wins: 60, seasons: 18 },
];

test("topBy finds the real maximum, not the first row", () => {
  assert.deepEqual(topBy(rows, (r) => r.wins), { value: 109, holders: "Poohsticks" });
});

test("topBy names tied leaders, or counts them when more than two", () => {
  assert.deepEqual(topBy(rows, (r) => r.seasons), {
    value: 27,
    holders: "Sly Fox / Mojo & Poohsticks",
  });
  const threeWay = rows.map((r) => ({ ...r, seasons: 5 }));
  assert.deepEqual(topBy(threeWay, (r) => r.seasons), { value: 5, holders: "3 boats" });
});

test("topBy returns null for no rows", () => {
  assert.equal(topBy([], () => 0), null);
});

test("weightedMonthlyAvg weights each month by its race days", () => {
  const months = [
    { race_days: 1, avg: 30 },
    { race_days: 3, avg: 10 },
  ];
  // Unweighted mean would be 20
  assert.equal(weightedMonthlyAvg(months, (m) => m.avg), 15);
});

test("weightedMonthlyAvg returns null without race days", () => {
  assert.equal(weightedMonthlyAvg([], () => 1), null);
  assert.equal(weightedMonthlyAvg([{ race_days: 0 }], () => 1), null);
});
