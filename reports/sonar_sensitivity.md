# Sonar-Proxy Sensitivity Analysis

> **Proxy-certificate simulation** — see `phrf_vs_orc_fixed_course.md`.

How much does the choice of Sonar proxy certificate change the PHRF-vs-ORC comparison? Same races, same wind data, same J/105/J/92/J/27/etc certs — only the Sonar cert changes.

## The three Sonar proxies

| Cert | Issued | GPH | Coastal Low ToT | Coastal Med ToT | Coastal High ToT | Sonar/J/105 ratio (low/med/high) |
|---|---|---|---|---|---|---|
| Tamar (ISR-113, baseline) | 2024 | 746.5 | 0.6994 | 0.9069 | 1.0328 | 0.826 / 0.825 / 0.837 |
| UN MAR SIN BARRERAS 2023 | 2023 | 736.3 | 0.7114 | 0.9175 | 1.0490 | 0.840 / 0.834 / 0.850 |
| UN MAR SIN BARRERAS 2021 | 2021 | 724.0 | 0.7241 | 0.9322 | 1.0657 | 0.855 / 0.848 / 0.864 |
| *PHRF (published)* | — | — | — | — | — | 0.879 in every race |

Lower GPH = faster boat. Lower ToT = more time-allowance credit.

**The two UN MAR SIN BARRERAS entries are the same physical boat** — only the ORC VPP model changed between 2021 and 2023, moving GPH from 724.0 to 736.3 (1.7%). The proxy certs used across the fleet were issued in different years (see `phrf_vs_orc_fixed_course.md`), so part of any class difference is model-year drift.

## Headline impact across 29 races

| Sonar proxy | GPH | Races with rank changes | Races with winner flips |
|---|---|---|---|
| Tamar (ISR-113, baseline) | 746.5 | 19 / 29 | 12 / 26 |
| UN MAR SIN BARRERAS 2023 | 736.3 | 18 / 29 | 12 / 26 |
| UN MAR SIN BARRERAS 2021 | 724.0 | 18 / 29 | 11 / 26 |

## Races where the Sonar proxy choice changes the ORC winner

Below: races where at least one of the three proxies produces a different ORC winner. If all three proxies agree on the winner, the row is omitted.

| Year | Course | Date | Wind (kt) | Band | PHRF winner | Tamar | UMSB-2023 | UMSB-2021 |
|---|---|---|---|---|---|---|---|---|
| 2014 | Boland's Cup | 27/07/14 | 12.6 | medium | Shenanagans | Shenanagans | Shenanagans | Gosling |
| 2016 | Boland's Cup | 21/08/16 | 9.2 | medium | Mojo | Echo | Echo | Mojo |
| 2017 | Leeward Island | 30/07/17 | 7.8 | low | Mojo | SOT After | SOT After | Mojo |
| 2017 | RG Smith (Tancook) | 03/09/17 | 9.1 | medium | Mojo | Echo | Buzz | Buzz |

**4 of 29 races are sensitive to the Sonar proxy choice** — the ORC winner depends on which Sonar cert we use.

## How to interpret this

**Stable to small proxy changes — which is all this tests.** Winner flips move 12 → 12 → 11 across the three proxies. But the proxies are close to each other (GPH within 3.1%) and all three rate the Sonar below PHRF's Sonar/J/105 ratio of 0.879, by 1.7–6.2%. That shared offset is what drives most winner changes (`phrf_vs_orc_fixed_course.md` shows most of them disappear when it is removed), so agreement among these proxies says nothing about whether the offset itself is right for LYC Sonars.

**Where the proxy does matter is at the boundary cases.** 4 of 29 races have different ORC winners depending on which Sonar cert we apply. In 2 of them (2016 Boland's Cup, 2017 Leeward Island), the proxy that gives the Sonar the least credit (UN MAR SIN BARRERAS 2021) hands the win back to the PHRF winner.

**Practical implication.** Choosing between similar published Sonar certs swings only a few marginal results. The open question is the level of the Sonar rating relative to the J/105 (and the other classes), which no proxy can answer.

**The only way to settle it** is measured certificates for LYC boats, or logging actual race-day winds and finish times across a season and back-fitting which ratings match LYC performance.
