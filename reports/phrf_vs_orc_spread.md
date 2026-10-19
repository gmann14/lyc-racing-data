# How does ORC compare to PHRF across conditions?

> **Proxy-certificate simulation.** The ORC side uses proxy certificates (same class, different boat) — see `phrf_vs_orc_fixed_course.md` for what that means and its caveats.

Deeper analysis of the 29 fixed-course Sunday races (2014–2025). For each race we look at:

- **Spread** of corrected times: how compressed/spread out is the corrected fleet?
- **Outlier sensitivity**: does trimming the back of the fleet change the picture?
- **Wind band breakdown**: does each system behave differently in light/medium/heavy?
- **Rank agreement**: how similar are the orderings PHRF and ORC produce?
- **Per-class bias**: which classes systematically benefit / suffer under each system?

All ORC numbers use the Tamar Sonar proxy (the current default).

## 1. Spread of corrected times across the fleet

Smaller spread = tighter, more competitive corrected results. Range expressed as percent of fastest boat's corrected time so we can compare across courses. Both systems are measured on the **same boats**: covered boats that also have a published PHRF corrected time. Trimming drops the boat(s) that finish last on average across both systems, from both.

| Filter | Races | PHRF median range | ORC median range | PHRF median stdev | ORC median stdev |
|---|---|---|---|---|---|
| All races, no trim | 25 | 6.8% | 10.0% | 3.0% | 4.0% |
| All races, drop last boat | 25 | 4.2% | 4.6% | 2.2% | 2.9% |
| All races, drop last 2 boats | 25 | 3.7% | 3.9% | 1.9% | 2.6% |

Races need 2+ boats with both times. 1 race with 2+ covered boats has no published PHRF corrected times (pursuit race) and is left out of the spread tables but still counted in the rank tables below. Trimming only applies where at least two boats remain.

## 2. Spread by wind band

Same metric, broken down by wind condition. If one system handles a particular condition better, its spread should be smaller.

| Wind band | Races | PHRF range | ORC range | Δ (ORC − PHRF) | PHRF stdev | ORC stdev |
|---|---|---|---|---|---|---|
| low | 15 | 9.6% | 11.3% | +1.7pp | 3.8% | 5.7% |
| medium | 10 | 5.5% | 4.3% | -1.2pp | 2.2% | 2.4% |
| high | 0 | — | — | — | — | — |

## 3. Rank agreement (Spearman ρ)

ρ = +1 means PHRF and ORC produce the same ordering. ρ = 0 means random. Negative ρ means inverted ordering. Computed only on the covered subset, with PHRF re-ranked within it.

| Wind band | Races | Median ρ | Mean ρ | ρ < 0.5 (significant disagreement) |
|---|---|---|---|---|
| low | 16 | +0.85 | +0.83 | 1 / 16 |
| medium | 10 | +0.20 | +0.01 | 7 / 10 |
| high | 0 | — | — | — |
| **all** | **26** | **+0.77** | **+0.51** | **8 / 26** |

## 4. Per-class systematic effect

For each class, average rank shift (ORC rank − PHRF rank) across all races. Negative = ORC ranks this class HIGHER than PHRF does (class benefits from ORC). Positive = ORC ranks this class LOWER (class is hurt by ORC). Wins count the best covered boat under each system.

| Class | Boat-races | Mean rank shift | PHRF wins | ORC wins | Δ wins |
|---|---|---|---|---|---|
| Sonar | 40 | -1.10 | 6 | 16 | +10 |
| C&C 25 | 3 | -0.67 | 0 | 0 | +0 |
| J/27 | 4 | +0.00 | 0 | 0 | +0 |
| Swan 57 | 6 | +0.33 | 0 | 0 | +0 |
| C&C 29-2 | 5 | +0.40 | 1 | 0 | -1 |
| J/92 | 10 | +0.50 | 0 | 1 | +1 |
| J/105 | 30 | +0.57 | 16 | 9 | -7 |
| J/29 O/B | 16 | +1.25 | 6 | 3 | -3 |

*(Classes with fewer than 3 boat-results across all races omitted.)*

## 5. Per-class effect, split by wind band

Does each class do better or worse under ORC in specific conditions?

| Class | Low (n) | Mean shift Low | Med (n) | Mean shift Med | High (n) | Mean shift High |
|---|---|---|---|---|---|---|
| Sonar | 25 | -0.84 | 15 | -1.53 | 0 | — |
| J/105 | 17 | +0.18 | 13 | +1.08 | 0 | — |
| J/29 O/B | 11 | +1.27 | 5 | +1.20 | 0 | — |
| J/92 | 6 | +0.50 | 4 | +0.50 | 0 | — |
| Swan 57 | 4 | +0.00 | 2 | +1.00 | 0 | — |
| C&C 29-2 | 5 | +0.40 | 0 | — | 0 | — |
| J/27 | 3 | +0.00 | 1 | +0.00 | 0 | — |
| C&C 25 | 2 | -0.50 | 1 | -1.00 | 0 | — |

## Summary observations

- **Rank agreement by band.** Median ρ is +0.85 in low wind (16 races), +0.20 in medium wind (10 races); agreement is lowest in medium wind. No race fell in the high band. With this few races per band, and different boats sailing in each, that is not evidence that the two systems diverge as the wind changes: under the proxy certs the Sonar/J/105 ToT ratio is nearly flat across bands, and most winner changes come from a fixed Sonar rating offset (see `phrf_vs_orc_fixed_course.md`).
- **Spread on the same boats.** Median corrected-time range is 10.0% under the ORC simulation vs 6.8% under PHRF (25 races), so the simulation spreads the fleet more than PHRF does.
- **Back-of-fleet sensitivity.** Dropping the boat that finishes last in both systems gives PHRF 4.2% vs ORC 4.6%; dropping two gives 3.7% vs 3.9%. The no-trim gap of +3.2pp becomes +0.4pp after one trim, so the difference in spread is concentrated at the back of the fleet.
- **Class bias is material under these proxy certs.** Sonar boats gain 1.1 places on average and go from 6 PHRF wins to 16 simulated ORC wins (+10). J/29 O/B and J/105 lose the most. This follows from the proxy certs' Sonar/J/105 rating offset, so it is only as reliable as those certs — see `sonar_sensitivity.md`.
