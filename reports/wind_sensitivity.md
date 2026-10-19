# Wind-Shift Sensitivity Analysis

> **Proxy-certificate simulation** — see `phrf_vs_orc_fixed_course.md`.

If actual on-water wind at LYC was systematically higher than Open-Meteo's afternoon average (Mahone Bay sea breeze funneling, gusts not captured in averages, etc.), how does that change ORC scoring outcomes?

This shifts the wind value used for Triple Number band classification by a constant offset and re-runs the analysis. Same Sonar proxy (Tamar) and same ToT model throughout.

Races without a wind value stay in the assumed Medium band at every shift: 2025 Leeward Island.

## Headline impact across all 29 races

| Wind shift | Low-band races | Medium-band races | High-band races | Races with rank changes | Winner flips |
|---|---|---|---|---|---|
| **+0 kt** | 17 | 12 | 0 | 19 / 29 | 12 / 26 |
| **+3 kt** | 7 | 19 | 3 | 18 / 29 | 13 / 26 |
| **+5 kt** | 2 | 15 | 12 | 16 / 29 | 12 / 26 |
| **+7 kt** | 0 | 10 | 19 | 15 / 29 | 12 / 26 |

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
| 2021 | RG Smith (Tancook) | 05/09/21 | 5.4 | low | low | medium | medium | Mojo | Mojo | **Second Chance** | Second Chance |
| 2022 | Boland's Cup | 24/07/22 | 8.4 | low | medium | medium | high | Mojo | Mojo | Mojo | **Poohsticks** |
| 2022 | Leeward Island | 21/08/22 | 5.9 | low | low | medium | medium | Shenanagans | Shenanagans | Shenanagans | Shenanagans |
| 2022 | RG Smith (Tancook) | 04/09/22 | 6.1 | low | medium | medium | medium | Mojo | Mojo | Mojo | Mojo |
| 2025 | Boland's Cup | 20/07/25 | 10.2 | medium | medium | high | high | Echo | Echo | Echo | Echo |
| 2025 | Leeward Island | — | — | medium | medium | medium | medium | Poohsticks | Poohsticks | Poohsticks | Poohsticks |
| 2025 | RG Smith (Tancook) | 30/08/25 | 8.7 | low | medium | medium | high | Mojo | Mojo | Mojo | Mojo |

## ToT ratio drift across wind bands (interpretation aid)

Some class pairs have very flat ToT relationships across wind bands (ratio barely changes); others have meaningful drift. Pairs with flat ratios are insensitive to wind shifts; pairs with drifty ratios can flip winners as wind moves between bands. Drift = max ÷ min − 1, so it does not depend on which class is on top.

| Pair | Low ratio | Med ratio | High ratio | Drift |
|---|---|---|---|---|
| J/105 / J/92 | 0.998 | 1.041 | 1.056 | 5.8% |
| Sonar / J/105 | 0.826 | 0.825 | 0.837 | 1.5% |
| J/105 / J/100 | 1.011 | 1.005 | 0.993 | 1.9% |
| J/92 / Sonar | 1.212 | 1.164 | 1.131 | 7.2% |
| J/100 / Sonar | 1.197 | 1.207 | 1.203 | 0.8% |
| J/29 O/B / Sonar | 1.159 | 1.130 | 1.102 | 5.3% |
| J/27 / Sonar | 1.133 | 1.110 | 1.092 | 3.7% |
| Swan 57 / Sonar | 1.339 | 1.339 | 1.312 | 2.1% |
| C&C 29-2 / Sonar | 1.070 | 1.041 | 1.012 | 5.7% |
| C&C 25 / Sonar | 0.996 | 0.969 | 0.935 | 6.6% |

**Interpretation** (all figures from the tables above):

- **Sonar vs J/105 drift is 1.5%** (ratio 0.825–0.837). The pairing behind most winner changes barely depends on the band, so shifting the wind cannot undo the proxy certs' fixed Sonar offset.
- **Winner changes move 12 → 13 → 12 → 12** across shifts of +0, +3, +5, +7 kt, although 28 of 29 races are in a different band at +7 kt.
- **Most band-sensitive pairs:** J/92 / Sonar 7.2%, C&C 25 / Sonar 6.6%, J/105 / J/92 5.8%. Results between these classes would move if the real wind differed from the Open-Meteo estimate.
- **Flattest pairs:** J/100 / Sonar 0.8%, Sonar / J/105 1.5%, J/105 / J/100 1.9%.
