# PHRF vs ORC: Fixed-Course Sunday Trophy Races (2014–2025)

> **This is a proxy-certificate simulation, not an ORC result.** No LYC boat holds an ORC certificate. Each boat is scored with a *proxy* cert — a same-class boat measured elsewhere (see `enrichment/orc_certs/`) — so every ORC number below says what this simulation produces, not what ORC would have scored. ORC cannot be retrofitted to past seasons; this is a what-if to inform the 2026 decision.

Re-scoring published PHRF results with Coastal/Long Distance Triple Number ToT (random-leg coastal courses).

## Headline numbers (proxy-certificate simulation)

- **29 races** (2014–2025) across 3 fixed courses (Boland's Cup, Leeward Island, RG Smith (Tancook)); 7 course-years have no usable results (see *Data notes*).
- **114/155** boat-results covered by a proxy ORC cert (74%). All comparisons rank covered boats only; PHRF is re-ranked within the same subset.
- **19/29** races have at least one rank change between PHRF and the simulation.
- **12/26** races with 2+ covered boats where the simulated ORC winner differs from the PHRF winner. In 10 of them a Sonar takes the win.
- **9 of those 12** disappear when only the Sonar proxy is re-scaled to PHRF's Sonar/J/105 ratio; 3 persist and 1 new one appears (4/26 in total). The disagreement is mostly one class-level rating offset — see below.

## Why the disagreements? A fixed Sonar rating offset, not wind

**Coastal Triple Number ToT for the proxy certs** (lower ToT = more time credit):

| LYC class | Proxy cert | Issued | Low (≤9 kt) | Medium (9–14) | High (≥14) |
|---|---|---|---|---|---|
| J/105 | Enjoy (`03420002E4P`) | 2023 | 0.8465 | 1.0998 | 1.2334 |
| J/92 | J3M (`03360002EWV`) | 2023 | 0.8479 | 1.0560 | 1.1678 |
| J/29 O/B | Koloa (`03880001H3B`) | 2021 | 0.8109 | 1.0246 | 1.1377 |
| J/27 | Junior (`03880001PIR`) | 2022 | 0.7924 | 1.0070 | 1.1280 |
| Swan 57 | MATCHLESS (`03860003TQ2`) | 2025 | 0.9363 | 1.2147 | 1.3550 |
| C&C 29-2 | Predictable (`CAN00000067`) | 2017 | 0.7486 | 0.9443 | 1.0455 |
| C&C 25 | Twenty Five (`NL00015566`) | 2019 | 0.6969 | 0.8786 | 0.9657 |
| Sonar | Tamar (`043900036AB`) | 2024 | 0.6994 | 0.9069 | 1.0328 |

**Sonar / J/105 time-correction ratio** (below 1 = the Sonar gets time credit against the J/105):

| System | Low | Medium | High |
|---|---|---|---|
| ORC proxy certs | 0.826 | 0.825 | 0.837 |
| PHRF (published, corrected ÷ elapsed) | 0.879 | 0.879 | 0.879 |

PHRF's ratio is 0.879 in the 12 races where a Sonar and a J/105 both sailed (2016–2025; identical in each). The proxy certs put the Sonar 4.8–6.2% lower in every band: about 5.7% more time credit against the J/105 regardless of wind (roughly 10 minutes over a 3-hour race). The ORC ratio itself moves only 1.5% between bands, so wind banding is not what flips these races; the level of the Sonar proxy relative to the J/105 proxy is.

| PHRF winner class → simulated ORC winner class | Races |
|---|---|
| J/105 → Sonar | 7 |
| J/29 O/B → Sonar | 3 |
| C&C 29-2 → J/105 | 1 |
| J/105 → J/92 | 1 |

**Test of that explanation.** Re-scaling only the Sonar proxy so Sonar/J/105 equals PHRF's 0.879 in each band (every other cert unchanged) removes 9 of the 12 winner changes († = see *Data notes*). Still different: 2017 RG Smith (Tancook) (Mojo → Buzz); 2021 RG Smith (Tancook) (Second Chance → Mojo); 2025 Leeward Island † (Mojo → Poohsticks). Newly different once the Sonar loses its extra credit: 2014 Boland's Cup (Shenanagans → Gosling).

**Caveat — proxy cert reality check.** The J/105 proxy is Enjoy (GRE-1146) and the Sonar proxy is Tamar (ISR-113), both European boats; LYC boats differ in sails, bottom and crew. Whether the ~6% Sonar/J/105 gap is real for LYC boats or an artifact of these two certs cannot be settled from this data — only measured certificates for LYC boats (or a season of logged ORC-style results) can. The other Sonar certs used in `sonar_sensitivity.md` also rate the Sonar below PHRF's ratio (by 1.7–5.1%), so swapping Sonar proxies does not test this.

**What this supports:** under these proxy certs the scoring method changes outcomes in a material share of races, and most of that comes from one class-level rating difference (Sonar vs J/105). It does not show that either system is "right", and it does not show a wind-dependent effect.

## By wind band

| Band | Races | Races with rank changes | Winner changes (2+ covered) |
|---|---|---|---|
| low | 17 | 10 | 6 / 16 |
| medium | 12 | 9 | 6 / 10 |
| high | 0 | 0 | 0 / 0 |

Band counts are small and confounded with which boats turned up, so differences between bands are not evidence of a wind effect. Rank correlation by band is in `phrf_vs_orc_spread.md`.

## Data notes

**Course-years with no usable results** (not in any number above):

- 2021 Boland's Cup: no event in the DB
- 2023 Boland's Cup: event in the DB has no race results
- 2024 Boland's Cup: event in the DB has no race results
- 2023 Leeward Island: no event in the DB
- 2024 Leeward Island: no event in the DB
- 2023 RG Smith (Tancook): no event in the DB
- 2024 RG Smith (Tancook): no event in the DB

**Races with caveats:**

- 2022 Leeward Island (21/08/22): pursuit race: the published rank is the finish order (staggered PHRF starts, no published corrected times), so it has no PHRF spread
- 2025 Leeward Island (no date): no race date in the DB, so no wind: Medium band assumed
- 2025 RG Smith (Tancook) (30/08/25): raced on a Saturday; the Sunday 13:00–17:00 wind window was applied anyway

**Certificate model years.** The proxy certs in use were issued 2017–2025 (2017–2026 across the whole registry) under different ORC VPP versions. VPP updates alone move ratings (UN MAR SIN BARRERAS, one hull: GPH 724.0 in 2021 → 736.3 in 2023, +1.7%), so classes are not rated on a common model year. See `sonar_sensitivity.md`.

**Cert scale.** The C&C 25 and C&C 29-2 proxies are older PDF certs whose Triple Number ToT was printed on a 675 base; they are rescaled to the standard ToD × ToT = 600 (see `enrichment/orc_certs/README.md`).

## Methodology

- Wind from Open-Meteo hourly archive, averaged over 13:00–17:00 (Sunday race window).
- Classify wind into Low (≤9 kt) / Medium / High (≥14 kt). Band determines which Triple Number ToT applies.
- Look up boat's proxy ORC cert (registry name + sail, then class) and pick the matching ToT coefficient.
- ORC corrected time = elapsed × ToT_band.
- Rank within the covered subset (boats lacking a cert excluded from both orderings).

## Open-Meteo wind data per race

13:00–17:00 average at LYC coordinates (44.37°N, 64.31°W).

| Date | Race | Afternoon avg (kt) | Gust max (km/h) | Band | Daily-avg comparison |
|---|---|---|---|---|---|
| 27/07/14 | Boland's Cup | 12.6 | 39 | medium | 11.8 (+0.8) |
| 22/06/14 | Leeward Island | 4.7 | 16 | low | 4.5 (+0.2) |
| 31/08/14 | RG Smith (Tancook) | 11.9 | 38 | medium | 11.5 (+0.4) |
| 26/07/15 | Boland's Cup | 9.6 | 30 | medium | 9.1 (+0.5) |
| 05/07/15 | Leeward Island | 5.7 | 23 | low | 4.4 (+1.3) |
| 30/08/15 | RG Smith (Tancook) | 7.3 | 24 | low | 8.7 (-1.4) |
| 21/08/16 | Boland's Cup | 9.2 | 31 | medium | 8.0 (+1.2) |
| 24/07/16 | Leeward Island | 5.1 | 20 | low | 4.3 (+0.8) |
| 04/09/16 | RG Smith (Tancook) | 8.4 | 33 | low | 5.3 (+3.1) |
| 27/08/17 | Boland's Cup | 2.8 | 27 | low | 2.8 (+0.0) |
| 30/07/17 | Leeward Island | 7.8 | 39 | low | 8.1 (-0.3) |
| 03/09/17 | RG Smith (Tancook) | 9.1 | 41 | medium | 6.2 (+2.9) |
| 26/08/18 | Boland's Cup | 9.0 | 43 | low | 6.9 (+2.1) |
| 22/07/18 | Leeward Island | 9.6 | 45 | medium | 8.9 (+0.7) |
| 02/09/18 | RG Smith (Tancook) | 9.3 | 44 | medium | 5.6 (+3.7) |
| 11/08/19 | Boland's Cup | 10.4 | 50 | medium | 9.6 (+0.8) |
| 23/06/19 | Leeward Island | 13.6 | 66 | medium | 9.7 (+3.9) |
| 01/09/19 | RG Smith (Tancook) | 2.4 | 20 | low | 4.3 (-1.9) |
| 09/08/20 | Boland's Cup | 6.4 | 31 | low | 5.9 (+0.5) |
| 26/07/20 | Leeward Island | 7.3 | 43 | low | 9.0 (-1.7) |
| 06/09/20 | RG Smith (Tancook) | 7.9 | 38 | low | 4.5 (+3.4) |
| 25/07/21 | Leeward Island | 9.6 | 45 | medium | 8.6 (+1.0) |
| 05/09/21 | RG Smith (Tancook) | 5.4 | 28 | low | 1.7 (+3.7) |
| 24/07/22 | Boland's Cup | 8.4 | 38 | low | 7.2 (+1.2) |
| 21/08/22 | Leeward Island | 5.9 | 29 | low | 5.8 (+0.1) |
| 04/09/22 | RG Smith (Tancook) | 6.1 | 32 | low | 3.3 (+2.8) |
| 20/07/25 | Boland's Cup | 10.2 | 48 | medium | 8.0 (+2.2) |
| — | Leeward Island | — | — | medium (assumed) | — |
| 30/08/25 | RG Smith (Tancook) | 8.7 | 45 | low | 4.7 (+4.0) |

## Race-by-race summary

PHRF winner = best published finish among covered boats. † = see *Data notes*.

| Year | Course | Date | Wind avg (kt) | Gust (km/h) | Band | Boats | Covered | Δrank | Max swap | PHRF winner | ORC winner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2014 | Boland's Cup | 27/07/14 | 12.6 | 39 | medium | 9 | 5 | 3 | 2 | Shenanagans | Shenanagans |
| 2014 | Leeward Island | 22/06/14 | 4.7 | 16 | low | 4 | 2 | 0 | 0 | Shenanagans | Shenanagans |
| 2014 | RG Smith (Tancook) | 31/08/14 | 11.9 | 38 | medium | 4 | 1 | 0 | 0 | Scotch Mist | Scotch Mist |
| 2015 | Boland's Cup | 26/07/15 | 9.6 | 30 | medium | 3 | 1 | 0 | 0 | Shenanagans | Shenanagans |
| 2015 | Leeward Island | 05/07/15 | 5.7 | 23 | low | 12 | 9 | 8 | 5 | Scotch Mist | Ping 🔁 |
| 2015 | RG Smith (Tancook) | 30/08/15 | 7.3 | 24 | low | 9 | 5 | 4 | 2 | Scotch Mist | Ping 🔁 |
| 2016 | Boland's Cup | 21/08/16 | 9.2 | 31 | medium | 8 | 7 | 6 | 4 | Mojo | Echo 🔁 |
| 2016 | Leeward Island | 24/07/16 | 5.1 | 20 | low | 7 | 7 | 2 | 1 | Shenanagans | Shenanagans |
| 2016 | RG Smith (Tancook) | 04/09/16 | 8.4 | 33 | low | 10 | 6 | 0 | 0 | Ping | Ping |
| 2017 | Boland's Cup | 27/08/17 | 2.8 | 27 | low | 2 | 1 | 0 | 0 | Mojo | Mojo |
| 2017 | Leeward Island | 30/07/17 | 7.8 | 39 | low | 10 | 8 | 6 | 4 | Mojo | SOT After 🔁 |
| 2017 | RG Smith (Tancook) | 03/09/17 | 9.1 | 41 | medium | 5 | 4 | 2 | 2 | Mojo | Echo 🔁 |
| 2018 | Boland's Cup | 26/08/18 | 9.0 | 43 | low | 5 | 4 | 2 | 1 | Buzz 105 | Echo 🔁 |
| 2018 | Leeward Island | 22/07/18 | 9.6 | 45 | medium | 5 | 4 | 4 | 1 | Mojo | So-Gnarly 🔁 |
| 2018 | RG Smith (Tancook) | 02/09/18 | 9.3 | 44 | medium | 4 | 4 | 3 | 2 | Mojo | Mojo |
| 2019 | Boland's Cup | 11/08/19 | 10.4 | 50 | medium | 6 | 5 | 4 | 2 | Ping | Ping |
| 2019 | Leeward Island | 23/06/19 | 13.6 | 66 | medium | 4 | 3 | 0 | 0 | Buzz 105 | Buzz 105 |
| 2019 | RG Smith (Tancook) | 01/09/19 | 2.4 | 20 | low | 4 | 3 | 0 | 0 | Paradigm Shift | Paradigm Shift |
| 2020 | Boland's Cup | 09/08/20 | 6.4 | 31 | low | 5 | 4 | 2 | 1 | Mojo | Mojo |
| 2020 | Leeward Island | 26/07/20 | 7.3 | 43 | low | 6 | 5 | 2 | 1 | Mojo | Mojo |
| 2020 | RG Smith (Tancook) | 06/09/20 | 7.9 | 38 | low | 7 | 4 | 2 | 1 | Paradigm Shift | Paradigm Shift |
| 2021 | Leeward Island | 25/07/21 | 9.6 | 45 | medium | 4 | 3 | 3 | 2 | Mojo | SOT After 🔁 |
| 2021 | RG Smith (Tancook) | 05/09/21 | 5.4 | 28 | low | 3 | 3 | 2 | 1 | Second Chance | Mojo 🔁 |
| 2022 | Boland's Cup | 24/07/22 | 8.4 | 38 | low | 4 | 3 | 0 | 0 | Mojo | Mojo |
| 2022 | Leeward Island † | 21/08/22 | 5.9 | 29 | low | 5 | 5 | 4 | 1 | Paradigm Shift | Shenanagans 🔁 |
| 2022 | RG Smith (Tancook) | 04/09/22 | 6.1 | 32 | low | 3 | 2 | 0 | 0 | Mojo | Mojo |
| 2025 | Boland's Cup | 20/07/25 | 10.2 | 48 | medium | 2 | 2 | 2 | 1 | Mojo | Echo 🔁 |
| 2025 | Leeward Island † | — | — | — | medium | 2 | 2 | 2 | 1 | Mojo | Poohsticks 🔁 |
| 2025 | RG Smith (Tancook) † | 30/08/25 | 8.7 | 45 | low | 3 | 2 | 0 | 0 | Mojo | Mojo |

## Races where ORC vs PHRF disagreed

### 2014 Boland's Cup (27/07/14)

Wind 12.6 kt (medium band) — course 16.7 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Shenanagans | Sonar | 2:58:24 | 2:58:55 | 2:41:47 | 1 |
| 2 | Gosling | J/29 O/B | 2:41:57 | 2:58:57 | 2:45:56 | 4 |
| 3 | Ping | Sonar | 2:58:52 | 2:59:23 | 2:42:13 | 2 |
| 4 | Echo | Sonar | 3:02:27 | 3:02:59 | 2:45:28 | 3 |
| 5 | Scotch Mist | J/29 O/B | 2:46:59 | 3:03:55 | 2:51:05 | 5 |

### 2015 Leeward Island (05/07/15)

Wind 5.7 kt (low band) — course 14.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Scotch Mist | J/29 O/B | 2:45:18 | 3:00:55 | 2:14:03 | 6 |
| 2 | Ping | Sonar | 3:02:10 | 3:03:29 | 2:07:24 | 1 |
| 3 | SOT After | Sonar | 3:02:24 | 3:03:43 | 2:07:34 | 2 |
| 4 | Pi | Sonar | 3:04:57 | 3:06:17 | 2:09:21 | 3 |
| 5 | Shenanagans | Sonar | 3:05:33 | 3:06:54 | 2:09:46 | 4 |
| 6 | Echo | Sonar | 3:05:42 | 3:07:03 | 2:09:53 | 5 |
| 7 | Paradigm Shift | J/29 O/B | 2:54:31 | 3:13:45 | 2:21:31 | 8 |
| 8 | Fighting Haddock | Sonar | 3:12:46 | 3:14:10 | 2:14:49 | 7 |
| 9 | So Nar So Good | Sonar | 3:22:40 | 3:24:08 | 2:21:45 | 9 |

### 2015 RG Smith (Tancook) (30/08/15)

Wind 7.3 kt (low band) — course 22.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Scotch Mist | J/29 O/B | 4:32:03 | 4:57:45 | 3:40:36 | 3 |
| 2 | Ping | Sonar | 5:03:38 | 5:05:50 | 3:32:22 | 1 |
| 3 | Poohsticks | J/92 | 4:37:30 | 5:10:04 | 3:55:18 | 4 |
| 4 | Martha Jane | Sonar | 5:14:15 | 5:16:32 | 3:39:47 | 2 |
| 5 | Odyssey | Swan 57 | 4:31:22 | 5:32:38 | 4:14:05 | 5 |

### 2016 Boland's Cup (21/08/16)

Wind 9.2 kt (medium band) — course 16.7 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 2:21:12 | 2:40:21 | 2:35:18 | 4 |
| 2 | Poohsticks | J/92 | 2:29:44 | 2:46:46 | 2:38:07 | 6 |
| 3 | Paradigm Shift | J/29 O/B | 2:34:24 | 2:47:56 | 2:38:12 | 7 |
| 4 | Echo | Sonar | 2:48:20 | 2:48:05 | 2:32:40 | 1 |
| 5 | Scotch Mist | J/29 O/B | 2:33:56 | 2:49:01 | 2:37:43 | 5 |
| 6 | SOT After | Sonar | 2:50:52 | 2:50:37 | 2:34:58 | 2 |
| 7 | Shenanagans | Sonar | 2:51:04 | 2:50:49 | 2:35:08 | 3 |

### 2016 Leeward Island (24/07/16)

Wind 5.1 kt (low band) — course 14.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Shenanagans | Sonar | 3:16:02 | 3:15:45 | 2:17:06 | 1 |
| 2 | Echo | Sonar | 3:19:43 | 3:19:26 | 2:19:41 | 2 |
| 3 | Ping | Sonar | 3:21:46 | 3:21:29 | 2:21:07 | 3 |
| 4 | Buzz | J/27 | 3:10:52 | 3:21:54 | 2:31:15 | 4 |
| 5 | Poohsticks | J/92 | 3:02:15 | 3:22:59 | 2:34:32 | 6 |
| 6 | Mojo | J/105 | 3:01:57 | 3:26:38 | 2:34:01 | 5 |
| 7 | Scotch Mist | J/29 O/B | 3:15:22 | 3:34:30 | 2:38:25 | 7 |

### 2017 Leeward Island (30/07/17)

Wind 7.8 kt (low band) — course 14.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 2:36:53 | 2:58:10 | 2:12:48 | 5 |
| 2 | Scotch Mist | J/29 O/B | 2:46:37 | 3:02:56 | 2:15:07 | 6 |
| 3 | SOT After | Sonar | 3:04:20 | 3:04:04 | 2:08:55 | 1 |
| 4 | Echo | Sonar | 3:05:03 | 3:04:47 | 2:09:25 | 2 |
| 5 | Barbarian | Sonar | 3:07:04 | 3:06:48 | 2:10:50 | 3 |
| 6 | Model T | Sonar | 3:07:32 | 3:07:16 | 2:11:10 | 4 |
| 7 | Buzz | J/27 | 3:02:45 | 3:13:19 | 2:24:49 | 7 |
| 8 | Poohsticks | J/92 | 3:01:01 | 3:21:37 | 2:33:29 | 8 |

### 2017 RG Smith (Tancook) (03/09/17)

Wind 9.1 kt (medium band) — course 22.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 3:53:14 | 4:24:52 | 4:16:31 | 3 |
| 2 | Buzz | J/27 | 4:13:24 | 4:28:03 | 4:15:10 | 2 |
| 3 | Echo | Sonar | 4:38:28 | 4:38:04 | 4:12:32 | 1 |
| 4 | Odyssey | Swan 57 | 3:52:08 | 4:44:32 | 4:41:58 | 4 |

### 2018 Boland's Cup (26/08/18)

Wind 9.0 kt (low band) — course 16.7 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Buzz 105 | J/105 | 2:38:09 | 2:59:36 | 2:13:52 | 2 |
| 2 | Echo | Sonar | 3:00:46 | 3:00:30 | 2:06:26 | 1 |
| 3 | Mojo | J/105 | 2:40:12 | 3:01:56 | 2:15:37 | 3 |
| 4 | Paradigm Shift | J/29 O/B | 2:50:22 | 3:05:18 | 2:18:09 | 4 |

### 2018 Leeward Island (22/07/18)

Wind 9.6 kt (medium band) — course 14.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 2:20:27 | 2:39:30 | 2:34:28 | 2 |
| 2 | So-Gnarly | Sonar | 2:44:10 | 2:43:56 | 2:28:53 | 1 |
| 3 | Buzz 105 | J/105 | 2:29:50 | 2:50:09 | 2:44:47 | 4 |
| 4 | Poohsticks | J/92 | 2:32:55 | 2:50:19 | 2:41:29 | 3 |

### 2018 RG Smith (Tancook) (02/09/18)

Wind 9.3 kt (medium band) — course 22.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 3:21:08 | 3:48:25 | 3:41:12 | 1 |
| 2 | Odyssey | Swan 57 | 3:08:32 | 3:51:06 | 3:49:01 | 4 |
| 3 | Buzz 105 | J/105 | 3:26:01 | 3:53:57 | 3:46:35 | 2 |
| 4 | Enchantress | C&C 25 | 4:18:20 | 3:59:23 | 3:46:58 | 3 |

### 2019 Boland's Cup (11/08/19)

Wind 10.4 kt (medium band) — course 16.7 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Ping | Sonar | 2:47:18 | 2:47:04 | 2:31:43 | 1 |
| 2 | Buzz 105 | J/105 | 2:29:22 | 2:49:37 | 2:44:16 | 4 |
| 3 | Mojo | J/105 | 2:29:58 | 2:50:18 | 2:44:56 | 5 |
| 4 | So-Gnarly | Sonar | 2:53:38 | 2:53:23 | 2:37:28 | 2 |
| 5 | Echo | Sonar | 2:57:57 | 2:57:42 | 2:41:23 | 3 |

### 2020 Boland's Cup (09/08/20)

Wind 6.4 kt (low band) — course 16.7 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 2:41:56 | 3:03:54 | 2:17:05 | 1 |
| 2 | Buzz 105 | J/105 | 2:46:30 | 3:09:05 | 2:20:57 | 2 |
| 3 | Paradigm Shift | J/29 O/B | 3:04:59 | 3:21:12 | 2:30:00 | 4 |
| 4 | Model T | Sonar | 3:26:10 | 3:25:52 | 2:24:12 | 3 |

### 2020 Leeward Island (26/07/20)

Wind 7.3 kt (low band) — course 14.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 3:25:09 | 3:52:58 | 2:53:40 | 1 |
| 2 | Buzz 105 | J/105 | 3:29:18 | 3:57:41 | 2:57:10 | 3 |
| 3 | Ping | Sonar | 4:10:22 | 4:10:00 | 2:55:06 | 2 |
| 4 | So-Gnarly | Sonar | 4:19:47 | 4:19:25 | 3:01:42 | 4 |
| 5 | Model T | Sonar | 4:33:45 | 4:33:21 | 3:11:28 | 5 |

### 2020 RG Smith (Tancook) (06/09/20)

Wind 7.9 kt (low band) — course 22.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Paradigm Shift | J/29 O/B | 4:02:20 | 4:23:34 | 3:16:30 | 1 |
| 2 | Poohsticks | J/92 | 3:56:22 | 4:24:32 | 3:20:25 | 3 |
| 3 | Mojo | J/105 | 3:53:13 | 4:24:51 | 3:17:25 | 2 |
| 4 | Enchantress | C&C 25 | 5:00:40 | 4:38:37 | 3:29:32 | 4 |

### 2021 Leeward Island (25/07/21)

Wind 9.6 kt (medium band) — course 14.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 2:11:13 | 2:29:01 | 2:24:19 | 3 |
| 2 | SOT After | Sonar | 2:34:45 | 2:34:32 | 2:20:21 | 1 |
| 3 | Shenanagans | Sonar | 2:38:21 | 2:38:07 | 2:23:36 | 2 |

### 2021 RG Smith (Tancook) (05/09/21)

Wind 5.4 kt (low band) — course 22.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Second Chance | C&C 29-2 | 5:12:46 | 5:07:01 | 3:54:08 | 2 |
| 2 | Mojo | J/105 | 4:31:35 | 5:08:25 | 3:49:54 | 1 |
| 3 | Odyssey | Swan 57 | 4:33:02 | 5:34:40 | 4:15:38 | 3 |

### 2022 Leeward Island (21/08/22)

Wind 5.9 kt (low band) — course 14.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Paradigm Shift | J/29 O/B | 2:43:19 | — | 2:12:26 | 2 |
| 2 | Shenanagans | Sonar | 3:00:18 | — | 2:06:06 | 1 |
| 3 | Mojo | J/105 | 2:40:36 | — | 2:15:57 | 3 |
| 4 | Second Chance | C&C 29-2 | 3:17:26 | — | 2:27:48 | 5 |
| 5 | Enchantress | C&C 25 | 3:27:51 | — | 2:24:51 | 4 |

### 2025 Boland's Cup (20/07/25)

Wind 10.2 kt (medium band) — course 16.7 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 2:44:55 | 3:07:17 | 3:01:23 | 2 |
| 2 | Echo | Sonar | 3:13:07 | 3:12:50 | 2:55:08 | 1 |

### 2025 Leeward Island (no date)

Wind unknown wind (medium band) — course 14.2 nm

| PHRF rank (covered) | Boat | Class | Elapsed | PHRF corrected | ORC corrected | ORC rank |
|---|---|---|---|---|---|---|
| 1 | Mojo | J/105 | 2:04:28 | 2:21:21 | 2:16:53 | 2 |
| 2 | Poohsticks | J/92 | 2:07:27 | 2:22:38 | 2:14:35 | 1 |
