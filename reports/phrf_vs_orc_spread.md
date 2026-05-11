# How does ORC compare to PHRF across conditions?

Deeper analysis of the 29 fixed-course Sunday races (2014–2025). For each race we look at:

- **Spread** of corrected times: how compressed/spread out is the corrected fleet?
- **Outlier sensitivity**: does trimming the slowest boat change the picture?
- **Wind band breakdown**: does each system behave differently in light/medium/heavy?
- **Rank agreement**: how similar are the orderings PHRF and ORC produce?
- **Per-class bias**: which classes systematically benefit / suffer under each system?

All ORC numbers use Tamar Sonar proxy (the current default).

## 1. Spread of corrected times across the fleet

Smaller spread = tighter, more competitive corrected results. Range expressed as percent of fastest boat's corrected time so we can compare across courses.

| Filter | Races | PHRF median range | ORC median range | PHRF median stdev | ORC median stdev |
|---|---|---|---|---|---|
| All races, no trim | 25 | 7.4% | 11.3% | 2.9% | 5.2% |
| All races, drop slowest | 25 | 5.6% | 5.7% | 2.1% | 3.4% |
| All races, drop slowest 2 | 25 | 3.8% | 4.8% | 1.9% | 2.5% |

## 2. Spread by wind band

Same metric, broken down by wind condition. If one system handles a particular condition better, its spread should be smaller.

| Wind band | Races | PHRF range | ORC range | Δ (ORC − PHRF) | PHRF stdev | ORC stdev |
|---|---|---|---|---|---|---|
| low | 15 | 11.7% | 15.5% | +3.8pp | 3.9% | 6.5% |
| medium | 10 | 6.2% | 5.3% | -0.9pp | 2.1% | 2.5% |
| high | 0 | — | — | — | — | — |

## 3. Rank agreement (Spearman ρ)

ρ = +1 means PHRF and ORC produce the same ordering. ρ = 0 means random. Negative ρ means inverted ordering. Computed only on the covered subset.

| Wind band | Races | Median ρ | Mean ρ | ρ < 0.5 (significant disagreement) |
|---|---|---|---|---|
| low | 16 | +0.85 | +0.76 | 2 / 16 |
| medium | 10 | +0.20 | +0.05 | 6 / 10 |
| high | 0 | — | — | — |
| **all** | **26** | **+0.80** | **+0.49** | **8 / 26** |

## 4. Per-class systematic effect

For each class, average rank shift (ORC rank − PHRF rank) across all races. Negative = ORC ranks this class HIGHER than PHRF does (class benefits from ORC). Positive = ORC ranks this class LOWER (class is hurt by ORC).

| Class | Boat-races | Mean rank shift | PHRF wins | ORC wins | Δ wins |
|---|---|---|---|---|---|
| Sonar | 40 | -1.10 | 4 | 16 | +12 |
| C&C 25 | 3 | -0.33 | 0 | 0 | 0 |
| Swan 57 | 6 | 0.00 | 0 | 0 | 0 |
| J/27 | 4 | 0.00 | 0 | 0 | 0 |
| J/92 | 10 | +0.50 | 0 | 1 | +1 |
| J/105 | 30 | +0.57 | 15 | 9 | -6 |
| C&C 29-2 | 5 | +0.60 | 1 | 0 | -1 |
| J/29 O/B | 16 | +1.25 | 4 | 3 | -1 |

*(Classes with fewer than 3 boat-results across all races omitted.)*

## 5. Per-class effect, split by wind band

Does each class do better or worse under ORC in specific conditions?

| Class | Low (n) | Mean shift Low | Med (n) | Mean shift Med | High (n) | Mean shift High |
|---|---|---|---|---|---|---|
| Sonar | 25 | -0.84 | 15 | -1.53 | 0 | — |
| J/105 | 17 | +0.18 | 13 | +1.08 | 0 | — |
| J/29 O/B | 11 | +1.27 | 5 | +1.20 | 0 | — |
| J/92 | 6 | +0.50 | 4 | +0.50 | 0 | — |
| Swan 57 | 4 | -0.25 | 2 | +0.50 | 0 | — |
| C&C 29-2 | 5 | +0.60 | 0 | — | 0 | — |
| J/27 | 3 | 0.00 | 1 | 0.00 | 0 | — |
| C&C 25 | 2 | -0.50 | 1 | 0.00 | 0 | — |

## Summary observations

- **Disagreement is wind-dependent.** Median rank correlation ρ is 0.85 in light wind vs 0.20 in medium vs n/a in high wind. The lower ρ, the less PHRF and ORC agree on ordering.
- **ORC produces a wider spread**, not a tighter one. Median corrected-time range is 11.3% under ORC vs 7.4% under PHRF. More spread = more separation between fastest and slowest corrected times. PHRF compresses the fleet more tightly.
- **The spread gap is driven almost entirely by the slowest boat in each race.** Dropping the slowest boat collapses the spreads to nearly identical: PHRF 5.6% vs ORC 5.7%. So ORC isn't structurally wider — it's more punishing to the back-of-fleet boat (probably an under-prepared / non-competitive entry whose elapsed time gets scaled up more heavily by the wind-band coefficient). For competitive racing among the top boats, ORC and PHRF produce similar spread.
- **Disagreement is greatest in MEDIUM wind, not light.** This is counterintuitive but consistent: in light wind, both systems heavily favor the smaller boats (everyone agrees Sonars win); in medium wind, PHRF gives a single coefficient while ORC's medium-band ToT does something different, producing diverging orderings in 6 of 10 medium-wind races.
- **Class bias is real and material.** Sonars gain ~1.1 positions on average under ORC and went from 4 PHRF wins to 16 ORC wins (+12). J/105 (Mojo) and J/29 OB lose the most. Caveat: partly an artifact of proxy cert choice — see sonar_sensitivity.md.
