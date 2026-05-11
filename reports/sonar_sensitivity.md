# Sonar-Proxy Sensitivity Analysis

How much does the choice of Sonar proxy certificate change the PHRF-vs-ORC comparison? Same races, same wind data, same J/105/J/92/J/27/etc certs — only the Sonar cert changes.

## The three Sonar proxies

| Cert | Year | GPH | Coastal Low ToT | Coastal Med ToT | Coastal High ToT |
|---|---|---|---|---|---|
| Tamar (ISR-113, baseline) | 2024 | 746.5 | 0.6994 | 0.9069 | 1.0328 |
| UN MAR SIN BARRERAS 2023 | 2023 | 736.3 | 0.7114 | 0.9175 | 1.0490 |
| UN MAR SIN BARRERAS 2021 | 2021 | 724.0 | 0.7241 | 0.9322 | 1.0657 |

Lower GPH = faster boat. Lower ToT = more time-allowance credit.
**The two UN MAR SIN BARRERAS entries are the same physical boat — only the ORC VPP model version changed between 2021 and 2023, shifting the rating by ~1.7%.**

## Headline impact across 29 races

| Sonar proxy | GPH | Races with rank changes | Races with winner flips |
|---|---|---|---|
| Tamar (ISR-113, baseline) | 746.5 | 19 / 29 | 12 / 26 |
| UN MAR SIN BARRERAS 2023 | 736.3 | 18 / 29 | 12 / 26 |
| UN MAR SIN BARRERAS 2021 | 724.0 | 18 / 29 | 11 / 26 |

## Races where the Sonar proxy choice changes the ORC winner

Below: races where at least one of the three proxies produces a different ORC winner. If all three proxies agree on the winner, the row is omitted.

| Year | Course | Date | Wind (kt) | Band | PHRF winner | Tamar | SBT-2023 | SBT-2021 |
|---|---|---|---|---|---|---|---|---|
| 2014 | Boland's Cup | 27/07/14 | 12.6 | medium | Shenanagans | Shenanagans | Shenanagans | Gosling |
| 2016 | Boland's Cup | 21/08/16 | 9.2 | medium | Mojo | Echo | Echo | Mojo |
| 2017 | Leeward Island | 30/07/17 | 7.8 | low | Mojo | SOT After | SOT After | Mojo |
| 2017 | RG Smith (Tancook) | 03/09/17 | 9.1 | medium | Mojo | Echo | Buzz | Buzz |

**4 of 29 races are sensitive to the Sonar proxy choice** — the ORC winner depends on which Sonar cert we use.

## How to interpret this

**The systematic finding is robust to proxy choice.** Headline winner-flips barely move across the three proxies (12 → 12 → 11). The macro story — Sonars often beat J/105s under ORC in light air — holds regardless of which Sonar cert we use.

**Where the proxy DOES matter is at the boundary cases.** Four races out of 29 have different ORC winners depending on which Sonar cert we apply. In two of those (2016 Boland's, 2017 Leeward), switching to the fastest Sonar proxy flips the result *back* to the PHRF winner — suggesting the Tamar proxy may be over-allocating credit to Sonars in those specific cases.

**Practical implication.** The ORC vs PHRF disagreement isn't an artifact of a single bad proxy — it's a structural difference between how the two systems handle wind banding. But if LYC ever switches scoring methods for real, the choice of which Sonar cert to use as the class default (or even better, having actual measured certs for individual boats) would only swing a handful of marginal race outcomes per season, not the majority.

**The only way to settle which proxy is most accurate** is to log actual race-day winds and finish times across a season, then back-fit which proxy's polars best match LYC Sonar performance.
