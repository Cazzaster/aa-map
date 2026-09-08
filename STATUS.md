# AA Meeting Finder — Status

**Repo:** https://github.com/Cazzaster/aa-map (public, Pages enabled)
**Live:** https://cazzaster.github.io/aa-map/
**Last session:** September 7, 2026
**Status:** NY pilot is functionally complete and live. Waiting on your
partner's review before deciding next moves.

## What this is

Free, public "enter your location, find nearby AA meetings" map. Built to
give away for free (your partner's "pay it forward" goal) and to double as
a GeoAI portfolio piece. No backend: a nightly GitHub Actions job rebuilds
a GeoJSON file that a static MapLibre frontend reads directly.

## Current state

- **Data**: 8 verified NY Area/Intergroup feeds, ~4,900 in-person/hybrid
  meetings, deduped across overlapping feeds (see `sources/ny_sources.yaml`
  for the full registry and per-source notes).
  - Gaps: Buffalo and Rockland deliberately restrict their feeds (don't
    bypass — contact them directly if inclusion matters). Binghamton and
    Elmira have no structured feed of any kind, just prose-style HTML —
    would need a fragile custom scraper or a direct data-export request.
- **Pipeline** (`scripts/`): fetches every registered feed, normalizes to
  one schema, strips personal info from free-text notes
  (`normalize/sanitize.py`), geocodes what's missing coordinates, dedupes,
  writes `docs/data/meetings.geojson`. Runs nightly via
  `.github/workflows/update-meetings.yml`; tests run via
  `.github/workflows/tests.yml` on every push.
- **Frontend** (`docs/`): static MapLibre map, address/ZIP or geolocation
  search, radius + day/time filters, pushpin markers, result/marker caps
  for huge-radius searches.
- **Tests** (`tests/`): 25 unit tests (stdlib `unittest`, no extra deps)
  covering the sanitizer, dedup, time parsing, and the Rochester scraper.
- Repo is public, GitHub Pages is live, code review findings are fixed,
  a privacy audit ran and git history was rewritten to remove PII that
  had been committed early on (see "Things worth knowing" below).

## Things worth knowing (non-obvious, don't re-derive)

- **Notes field is sanitized on purpose.** Upstream feeds sometimes put a
  member's personal phone number or a Venmo/Zelle/PayPal handle in the
  free-text notes field. `normalize/sanitize.py` strips that (but leaves
  Zoom/dial-in info intact) before it ever reaches the output. If a new
  source parser is added later, run its `notes` field through
  `sanitize_notes()` too.
- **Git history was rewritten once**, early in the project, to remove PII
  that had been committed before the sanitizer existed. If your partner
  cloned before that rewrite, they need `git fetch && git reset --hard
  origin/main` (not a plain pull) to pick up the clean history.
- **Rochester has no JSON API** — its feed comes from scraping the site's
  own day-filtered HTML pages (`normalize/rochester.py`), 7 requests a
  night, spaced out to avoid its rate-limiting WAF. If that source ever
  stops working, check whether the site changed its page structure before
  assuming the WAF fully blocked us — a single isolated request has
  always succeeded in testing; only rapid bursts got blocked.
- **Westchester needs no separate source** — westchesternyaa.org's own
  "meetings" link points at the NYC Intergroup feed we already pull, so
  it's already covered.

## Next steps — pick up here

- [ ] **Scope nationwide expansion.** This was always the plan after the
      NY pilot proved out (see README's "Known limitations / next steps").
      Concretely this means: pick which state(s) to add next, research
      that state's Area/Intergroup feeds the same way `ny_sources.yaml`
      was built (most run the same TSML WordPress plugin —
      `/wp-json/tsml/meetings`), and decide whether the registry becomes
      one YAML per state or one file with a `state` field per source.
      Also worth deciding then: multi-state UI (state picker? auto-detect
      from search location?) and whether the timezone assumption
      (`America/New_York` is hardcoded throughout) needs to become
      per-meeting before a second state ships.
- [ ] Binghamton, Elmira: still no structured feed — custom scraper
      (fragile) or a direct data-export request, if pursued at all.
- [ ] Consider emailing Buffalo/Rockland intergroups about their
      restricted feeds.
- [ ] NA/other 12-step programs — flagged as a later phase, AA only so far.

## Key decisions so far

- **In-person + hybrid meetings only** — online-only meetings excluded
  (no real location to map).
- **AA only** for now — other programs are a later phase.
- Fully **static hosting**: GitHub Pages + nightly Actions rebuild, $0
  backend.
- **Pushpins over clustering** for markers, per explicit request — result
  and marker counts are capped on huge-radius searches instead.

## Resume prompt (paste into a new session)

> Continue the aa-map project (`~/ai-projects/aa-map`, public GitHub repo
> `Cazzaster/aa-map`, live at cazzaster.github.io/aa-map). Read `STATUS.md`
> for full context — the NY pilot is done and live, waiting on partner
> review. Next phase is nationwide expansion (see "Next steps" in
> STATUS.md). I want to: [fill in]
