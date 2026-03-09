# Human Questions / Club Follow-up

## Ownership / Skipper / Helm

- Which boats have known long-term owners/skippers that should be attached historically?
- For helm-only regattas, do we want to treat the helm as the canonical participant and leave boat ownership blank?
- Are there club rosters, regatta notices, or spreadsheets that list skippers/owners for older handicap races?

## Boat Identity

- Which names represent true successor boats vs the same boat renamed (for example `Awesome` vs `Awesome 2.0`)?
- When the same sail number maps to different names, is that a rename, sail transfer, or bad source data?
- Should placeholder sail numbers like `999`, `???`, `xxxxxx` be treated as unknowns rather than true identifiers?

## Class / Rating Band

- Do values like `A3/15`, `D3/19`, etc. represent race bands rather than boat designs in the source system?
- Should the public site expose both boat design and race band, or only one by default?

## Missing / Suspicious Events

- Are empty events / races-without-results legitimate placeholders, or did the parser miss attached result rows?
- Are titles like `Lunenburg Race??` and `Womens Keelboat Championship by Bow ##` source artifacts that should be cleaned manually?

## Analytics / UX

- For public stats, should helm-only one-design events be mixed into all-time leaderboards with boat events, or separated?
- Which suggested `special_local` events should still be highlighted prominently even if excluded from handicap leaderboards?
- Which metrics matter most to club members first: participation, wins, attendance, rivalries, trophy history, or race durations?
