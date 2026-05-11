# Wind-Shift Sensitivity Analysis

If actual on-water wind at LYC was systematically higher than Open-Meteo's afternoon average (Mahone Bay sea breeze funneling, gusts not captured in averages, etc.), how does that change ORC scoring outcomes?

This shifts the wind value used for Triple Number band classification by a constant offset and re-runs the analysis. Same Sonar proxy (Tamar) and same ToT model throughout.

## Headline impact across all 29 races

| Wind shift | Low-band races | Medium-band races | High-band races | Races with rank changes | Winner flips |
|---|---|---|---|---|---|
| **+0 kt** | 17 | 12 | 0 | 19 / 29 | 12 / 26 |
| **+3 kt** | 7 | 19 | 3 | 18 / 29 | 13 / 26 |
| **+5 kt** | 2 | 15 | 12 | 17 / 29 | 13 / 26 |
| **+7 kt** | 0 | 10 | 19 | 16 / 29 | 13 / 26 |

## Per-race effect of wind shift

Bold winners indicate races where the ORC winner changes from one wind shift to the next.

| Year | Course | Date | OM (kt) | +0 band | +3 band | +5 band | +7 band | +0 winner | +3 winner | +5 winner | +7 winner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2014 | Boland's Cup | 27/07/14 | 12.6 | medium | high | high | high | Shenanagans | **Gosling** | Gosling | Gosling |
| 2014 | Leeward Island | 22/06/14 | 4.7 | low | low | medium | medium | Shenanagans | Shenanagans | Shenanagans | Shenanagans |
| 2014 | RG Smith (Tancook) | 31/08/14 | 11.9 | medium | high | high | high | Scotch Mist | Scotch Mist | Scotch Mist | Scotch Mist |
| 2015 | Boland's Cup | 26/07/15 | 9.6 | medium | medium | high | high | Shenanagans | Shenanagans | Shenanagans | Shenanagans |
| 2015 | Leeward Island | 05/07/15 | 5.7 | low | low | medium | medium | Ping | Ping | Ping | Ping |
| 2015 | RG Smith (Tancook) | 30/08/15 | 7.3 | low | medium | medium | high | Ping | Ping | Ping | **Scotch Mist** |
| 2016 | Boland's Cup | 21/08/16 | 9.2 | medium | medium | high | high | Echo | Echo | Echo | Echo |
| 2016 | Leeward Island | 24/07/16 | 5.1 | low | low | medium | medium | Shenanagans | Shenanagans | Shenanagans | Shenanagans |
| 2016 | RG Smith (Tancook) | 04/09/16 | 8.4 | low | medium | medium | high | Ping | Ping | Ping | Ping |
| 2017 | Boland's Cup | 27/08/17 | 2.8 | low | low | low | medium | Mojo | Mojo | Mojo | Mojo |
| 2017 | Leeward Island | 30/07/17 | 7.8 | low | medium | medium | high | SOT After | SOT After | SOT After | **Scotch Mist** |
| 2017 | RG Smith (Tancook) | 03/09/17 | 9.1 | medium | medium | high | high | Echo | Echo | **Buzz** | Buzz |
| 2018 | Boland's Cup | 26/08/18 | 9.0 | low | medium | high | high | Echo | Echo | Echo | Echo |
| 2018 | Leeward Island | 22/07/18 | 9.6 | medium | medium | high | high | So-Gnarly | So-Gnarly | So-Gnarly | So-Gnarly |
| 2018 | RG Smith (Tancook) | 02/09/18 | 9.3 | medium | medium | high | high | Mojo | Mojo | Mojo | Mojo |
| 2019 | Boland's Cup | 11/08/19 | 10.4 | medium | medium | high | high | Ping | Ping | Ping | Ping |
| 2019 | Leeward Island | 23/06/19 | 13.6 | medium | high | high | high | Buzz 105 | Buzz 105 | Buzz 105 | Buzz 105 |
| 2019 | RG Smith (Tancook) | 01/09/19 | 2.4 | low | low | low | medium | Paradigm Shift | Paradigm Shift | Paradigm Shift | Paradigm Shift |
| 2020 | Boland's Cup | 09/08/20 | 6.4 | low | medium | medium | medium | Mojo | Mojo | Mojo | Mojo |
| 2020 | Leeward Island | 26/07/20 | 7.3 | low | medium | medium | high | Mojo | Mojo | Mojo | Mojo |
| 2020 | RG Smith (Tancook) | 06/09/20 | 7.9 | low | medium | medium | high | Paradigm Shift | Paradigm Shift | Paradigm Shift | Paradigm Shift |
| 2021 | Leeward Island | 25/07/21 | 9.6 | medium | medium | high | high | SOT After | SOT After | SOT After | SOT After |
| 2021 | RG Smith (Tancook) | 05/09/21 | 5.4 | low | low | medium | medium | Mojo | Mojo | Mojo | Mojo |
| 2022 | Boland's Cup | 24/07/22 | 8.4 | low | medium | medium | high | Mojo | Mojo | Mojo | **Poohsticks** |
| 2022 | Leeward Island | 21/08/22 | 5.9 | low | low | medium | medium | Shenanagans | Shenanagans | Shenanagans | Shenanagans |
| 2022 | RG Smith (Tancook) | 04/09/22 | 6.1 | low | medium | medium | medium | Mojo | Mojo | Mojo | Mojo |
| 2025 | Boland's Cup | 20/07/25 | 10.2 | medium | medium | high | high | Echo | Echo | Echo | Echo |
| 2025 | Leeward Island | — | — | medium | medium | medium | medium | Poohsticks | Poohsticks | Poohsticks | Poohsticks |
| 2025 | RG Smith (Tancook) | 30/08/25 | 8.7 | low | medium | medium | high | Mojo | Mojo | Mojo | Mojo |

## ToT ratio drift across wind bands (interpretation aid)

Some class pairs have very flat ToT relationships across wind bands (ratio barely changes); others have meaningful drift. Pairs with flat ratios are insensitive to wind shifts; pairs with drifty ratios can flip winners as wind moves between bands.

| Pair | Low ratio | Med ratio | High ratio | Drift (max - min) |
|---|---|---|---|---|
| J/105 / J/92 | 0.998 | 1.041 | 1.056 | 0.058 |
| J/105 / Sonar | 1.210 | 1.213 | 1.194 | 0.018 |
| J/105 / J/100 | 1.011 | 1.005 | 0.993 | 0.019 |
| J/92 / Sonar | 1.212 | 1.164 | 1.131 | 0.082 |
| J/100 / Sonar | 1.197 | 1.207 | 1.203 | 0.010 |
| J/29 OB / Sonar | 1.159 | 1.130 | 1.102 | 0.058 |
| J/27 / Sonar | 1.133 | 1.110 | 1.092 | 0.041 |
| Swan 57 / Sonar | 1.339 | 1.339 | 1.312 | 0.027 |
| C&C 29 / Sonar | 1.204 | 1.171 | 1.139 | 0.065 |

**Interpretation:**

- **Sonar vs J/105 drift is tiny (0.013)** — the Sonar/J/105 outcome barely depends on wind band. Shifting wind up won't rescue the J/105 from Sonar dominance.
- **J/92 vs Sonar drift is large (0.082)** — J/92 has a meaningful relative advantage in light wind that erodes in heavy wind. If actual wind was higher than logged, J/92 results would shift.
- **J/100, J/27, Swan 57 vs J/105 are also flat** — proxy ratios don't reshape with wind.
- **C&C 25, J/29 OB, J/92 vs J/105 drift more** — these comparisons are wind-band-sensitive.
