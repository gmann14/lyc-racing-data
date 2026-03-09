# Human Questions / Club Follow-up

## Ownership / Skipper / Helm

- Which boats have known long-term owners/skippers that should be attached historically?
--good question, we probably need to look at a list. Poohsticks and Scotch Mist have been the same forever, for example. Slyfox owner is Jim Mosher who moved on to Mojo (maybe even one in between I'm forgetting). 
- For helm-only regattas, do we want to treat the helm as the canonical participant and leave boat ownership blank?
--good question, helm/skipper/owner is probably going to be the same for the purposes of what we track
- Are there club rosters, regatta notices, or spreadsheets that list skippers/owners for older handicap races?
--i don't think so, but there might be that we could dig out from somewhere. if not we could crowdsource a list i'm sure

## Boat Identity

- Which names represent true successor boats vs the same boat renamed (for example `Awesome` vs `Awesome 2.0`)?
--often "2.0" or a number designates a successor boat, but it may not always be true
- When the same sail number maps to different names, is that a rename, sail transfer, or bad source data?
--good question, probably bad source data (often handwritten by the dock boy or whatever) but may have to evaluate case-by-case (if there's one instance of a wrong one sandwiched between the same right one, that's obvious, but if there's an actual change at some point it may bear further investigation)
- Should placeholder sail numbers like `999`, `???`, `xxxxxx` be treated as unknowns rather than true identifiers?
--999 might be real, but yeah the others are placeholders, again likely just handwritten by someone

## Class / Rating Band

- Do values like `A3/15`, `D3/19`, etc. represent race bands rather than boat designs in the source system?
--yeah race bands. you could always check common boat models if unsure, or can usually manually correct
- Should the public site expose both boat design and race band, or only one by default?
--race bands frequently change, while boat designs do not, so that should be considered

## Missing / Suspicious Events

- Are empty events / races-without-results legitimate placeholders, or did the parser miss attached result rows?
--not sure, all should be investigated though
- Are titles like `Lunenburg Race??` and `Womens Keelboat Championship by Bow ##` source artifacts that should be cleaned manually?
--probably yeah

## Analytics / UX

- For public stats, should helm-only one-design events be mixed into all-time leaderboards with boat events, or separated?
--separated as special events
- Which suggested `special_local` events should still be highlighted prominently even if excluded from handicap leaderboards?
--not sure, going to have to see
- Which metrics matter most to club members first: participation, wins, attendance, rivalries, trophy history, or race durations?
--good question, i think participation is nice, then more performance stuff probably. should be fun-first
