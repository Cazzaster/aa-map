# AA Meeting Finder (NY Pilot) — Status

**Repo:** https://github.com/Cazzaster/aa-map (currently **private** — flip to public when ready, then enable Pages)
**Last session:** September 5, 2026
**Live preview:** none yet — Pages not enabled while repo is private

## What this is

Free, public "enter your location, find nearby AA meetings" map for New York
State. A pilot before nationwide expansion — built to give away for free
(your partner's "pay it forward" goal) and to double as a GeoAI portfolio
piece. No backend: a nightly GitHub Actions job rebuilds a GeoJSON file that
a static MapLibre frontend reads directly.

## Current state (all done this session)

- [x] Source registry (`sources/ny_sources.yaml`): **7 verified** NY
      Area/Intergroup TSML feeds (~4,700 in-person/hybrid meetings after
      filtering out online-only/inactive), **2 known-restricted**
      (Buffalo, Rockland — feed exists but returns `feed_restricted`, a
      deliberate site-owner choice, don't bypass), **4 needing manual
      follow-up** (Rochester — WAF-blocked, likely TSML; Westchester;
      Binghamton; Elmira)
- [x] Normalizer + build pipeline (`scripts/`) — tested end-to-end against
      the real feeds, produces `docs/data/meetings.geojson`
- [x] Static MapLibre frontend (`docs/`) — address/ZIP or geolocation
      search, radius + day/time filters, green pushpin markers for results,
      red pushpin for the searched location
- [x] Nightly GitHub Actions rebuild (`.github/workflows/update-meetings.yml`)
- [x] Pushed to GitHub (private repo, initial commit `d29ba80`)
- [x] Functionality code review completed (high effort) — 6 findings,
      **none fixed yet** (see below)

## Open findings from code review — not yet fixed

Ranked most-severe first:

1. **`scripts/geocode.py:53`** — geocoder response parsing sits outside the
   try/except; a malformed Census/Nominatim response can crash the entire
   nightly build silently (no `meetings.geojson` written, no visible error).
2. **`scripts/geocode.py:93`** — a failed geocode lookup is cached as `None`
   forever with no retry — one transient API hiccup permanently and
   silently drops that meeting from the map.
3. **`docs/app.js:49`** — `loadMeetings()` has no error handling; a
   failed/missing data fetch leaves the UI stuck on "Loading meeting
   data…" forever. (This is hit exactly as described if you preview
   `docs/index.html` before ever running the build script — worth fixing
   before anyone else tries the README's own local-preview steps.)
4. **`docs/app.js:220`** — no cap on rendered markers; a 50-mile search
   near NYC could render thousands of DOM markers/popups in one tick and
   freeze the tab. Known tradeoff from switching to pushpins over
   clustering — a result cap would be a cheap safety valve.
5. **`scripts/normalize/meeting_guide_json.py:61`** — an unparseable time
   string passes through as-is instead of becoming `None`, so the UI can
   show a garbled "NaN:NaN AM" instead of the intended "Time varies" text.
6. **`sources/ny_sources.yaml`** — no dedup between overlapping NYC/Queens
   feeds; a meeting near that border can show up twice. Already flagged as
   a TODO in the registry's own notes, not yet implemented.

## Key decisions made this session

- Pilot scope: **New York State only** (nationwide is a later phase)
- **In-person + hybrid meetings only** — online-only meetings excluded
  (they have no real location; TSML gives them a fake "approximate" pin,
  which we filter out)
- **AA only** for now — NA/other 12-step programs flagged as a later to-do
- Fully **static hosting**: GitHub Pages + nightly Actions rebuild, $0
  backend, reusing the MapLibre pattern from `gis-data-aggregator`
- **Pushpins over clustering** for markers, per explicit request — accepted
  tradeoff: no grouping at large radius / in dense areas (see finding #4)

## Next steps — pick up here

- [ ] Decide which of the 6 code review findings to fix (all, or a subset)
- [ ] Flip repo to public + enable GitHub Pages (`main:/docs`) once ready
      — I can do this via the GitHub API once told to proceed
- [ ] Chase down remaining NY regions: Rochester, Westchester, Binghamton,
      Elmira
- [ ] Consider emailing Buffalo/Rockland intergroups directly about
      getting their restricted feeds included

## Resume prompt (paste into a new session)

> Continue the aa-map project (`~/ai-projects/aa-map`, private GitHub repo
> `Cazzaster/aa-map`). Read `STATUS.md` for full context. Last session: built
> and pushed the NY pilot end-to-end, tested it live in a browser, added
> pushpin markers, and ran a functionality code review that surfaced 6 open
> findings (listed in STATUS.md). Next I want to: [fill in]
