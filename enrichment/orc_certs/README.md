# ORC Certificate Cache

Cached ORC certificate data used as proxies for LYC-fleet boats. Each LYC class
maps to a same-class boat elsewhere in the world that has a published cert.

## Files

- `boats.csv` — registry mapping LYC boats → cert refs
- `<orc_ref>.json` — one canonical JSON per cert (fetched or transcribed)
- `manual_*.json` — manually-transcribed data (no fetchable URL)

## Fetcher

```
python scraper/fetch_orc_certs.py                  # fetch all from boats.csv
python scraper/fetch_orc_certs.py NL00015566 ...   # fetch specific refs
```

The fetcher hits `https://data.orc.org/public/WPub.dll/CC/<ref>` and parses
both HTML and PDF response formats. Output goes to `<ref>.json`.

Refs prefixed with `manual_` are skipped (transcribed by hand).

## Coverage of 2025 LYC fleet

| LYC class | Boats | Cert ref | Source boat | Polars | Time allowances |
|---|---|---|---|---|---|
| J/92 | Poohsticks | `03360002EWV` | J3M (FRA) | ✓ | ✓ |
| J/29 O/B | Scotch Mist | `03880001H3B` | Koloa | ✓ | ✓ |
| J/105 | Mojo | `03420002E4P` | Enjoy (GRE) | ✓ | ✓ |
| J/27 | Buzz | `03880001PIR` | Junior | ✓ | ✓ |
| J/70 | Boost | `03190004L8K` | FREE FUN (ITA) | ✓ | ✓ |
| J/100 | Moxie, Second Shift | `030200040L7` | NINJO (AUS) | ✓ | ✓ |
| Sonar | Echo, Pi, Ping, Barbarian, SOT After, Martha Jane, Toad's | `043900036AB` | Tamar (ISR) | ✓ | ✓ |
| Swan 57 | Odyssey | `03860003TQ2` | MATCHLESS (GBR) | ✓ | ✓ |
| C&C 29 | Second Chance | `CAN00000067` | (CAN, PDF) | — | ✓ |
| C&C 25 | Enchantress | `NL00015566` | Twenty Five (NED) | — | ✓ |

## Known gaps

- **C&C 29** + **C&C 25** PDF certs have time allowances but no polar table
  (older cert format). Single + Triple Number scoring is available, which
  is sufficient for ToT/ToD scoring — only PCS would need the polars.
- **J/100** — NINJO is a *current* (2025) cert but has multiple rig
  configuration options; worth checking that the LYC boats' rigs match.
- **Nonsuch 36** (Captain Haddock) — no ORC cert exists; cat-rigged hull.
- **Frers Cat/Ketch** (Wandrian) — no ORC cert exists; ketch rig.

## Important caveats

These are **proxy certificates** — same class as the LYC boat, but a
different hull elsewhere in the world. Same class can vary materially
by sails, rigging, age. Useful for what-if analysis; not authoritative
for actual racing scoring.

For a real ORC-scored season, LYC boats would need to commission their
own measurements (ORC Club tier is the cheapest, ~5 measurements).
