# AA Meeting Finder — New York State (pilot)

A free, public "enter your location, find nearby A.A. meetings" map.
Not affiliated with or endorsed by A.A. World Services — an independent tool
built to make existing public meeting data easier to search.

## Why this exists / the data problem

There is no single national database of A.A. meetings. A.A.'s own "Meeting
Guide" app solves this by syncing ~400+ independent Area/Intergroup/Central
Office websites twice a day. Those sites publish their meeting lists in one
of a small number of standard formats:

- **Meeting Guide JSON spec** ([code4recovery/spec](https://github.com/code4recovery/spec)) — a directly fetchable JSON feed.
- **TSML** (the "12 Step Meeting List" WordPress plugin) — exposes a
  spec-compliant feed at `<site>/wp-json/tsml/meetings` (NOT `/tsml/v1/meetings` —
  that's a commonly-assumed path that 404s on every real install checked so far).
- **BMLT** (Basic Meeting List Toolbox) — a semantic JSON API, more common
  for NA but used by some AA areas too.
- Some smaller intergroups have no machine-readable feed at all — just an
  HTML page — and need one-off scraping (out of scope for the pilot).

So "efficient" here means: register each source site once (tagged by feed
type), write **one normalizer per feed type** (not per site), and treat
no-feed holdouts as a manual backlog rather than blocking on them.

## Architecture

```
sources/ny_sources.yaml   → registry of NY Area/Intergroup sites + feed type/URL
scripts/build_dataset.py  → fetches every source, normalizes, geocodes gaps,
                             writes docs/data/meetings.geojson
.github/workflows/        → nightly GitHub Actions job runs the build and
  update-meetings.yml       commits the refreshed GeoJSON
docs/                     → static frontend (GitHub Pages root): MapLibre GL
                             map + address search + radius/time filters,
                             reads docs/data/meetings.geojson directly
```

Everything is static after the nightly build — **no backend server, $0
hosting**. The frontend does geocoding (via Nominatim, one lookup per
visitor search — fine under Nominatim's usage policy at this scale) and
distance/time filtering entirely client-side in the browser.

Privacy note: normalizers deliberately strip any contact-person name/phone/
email fields some upstream feeds include. Only meeting logistics (name, day,
time, location, format) are ever published, out of respect for A.A.'s
anonymity tradition.

## Current data coverage

As of this pilot's initial research (see `sources/ny_sources.yaml` for full detail):

- **8 verified, working feeds**: NYC (New York Intergroup), Queens, Nassau
  County, Suffolk County, Capital District/Albany, Syracuse, Jefferson
  County/North Country, and Rochester — roughly **4,900 in-person/hybrid
  meetings** after filtering out online-only and inactive listings.
  Rochester's REST API is disabled, so its meetings come from
  `scripts/normalize/rochester.py`, which reads the same data out of the
  site's own day-filtered HTML pages instead.
- **Westchester County is already covered** — westchesternyaa.org has no
  feed of its own; its "Find a Meeting" link points straight at the NYC
  Intergroup feed above, which we already pull in full.
- **2 feeds exist but are access-restricted** by the site owner (Buffalo,
  Rockland County) — both return an explicit `feed_restricted` response.
  This is a deliberate choice by those intergroups, not a bug; don't try to
  bypass it. Contact the intergroup directly to ask about inclusion.
- **Not yet found / needs manual follow-up**: Binghamton and Elmira
  (Southern Tier — small hand-maintained sites with no TSML/BMLT/JSON of
  any kind, just unstructured prose-style HTML; would need a bespoke,
  fragile scraper).
- No BMLT-based AA source was found for NY — BMLT is far more common for NA.

## Adding a new NY source

Add an entry to `sources/ny_sources.yaml`:

```yaml
  - id: some_intergroup_slug
    name: "Some County Intergroup"
    region: "Human-readable area description"
    website: "https://example.org"
    feed_type: meeting_guide_json   # or: tsml | bmlt | none_found
    feed_url: "https://example.org/wp-json/tsml/meetings"
    verified: true   # only set true once you've actually fetched feed_url and confirmed it returns real meeting data
    notes: "..."
```

`feed_type` selects which parser in `scripts/normalize/` handles it
(`meeting_guide_json` and `tsml` share a parser since TSML's feed is spec-
compliant JSON). Entries with `feed_type: none_found` are skipped by the
build and logged, so they're visible as a backlog rather than silently
dropped.

## Running the build locally

```bash
pip install -r requirements.txt
python scripts/build_dataset.py
```

This writes `docs/data/meetings.geojson`. Open `docs/index.html` with any
static file server (e.g. `python -m http.server` from `docs/`) to preview
the map against freshly built data.

## Deploying (one-time setup)

1. Push this repo to GitHub.
2. Settings → Pages → **Deploy from a branch** → branch `main`, folder `/docs`.
3. The nightly workflow (`.github/workflows/update-meetings.yml`) keeps
   `docs/data/meetings.geojson` current; Pages redeploys automatically on
   every push to `main`, including the bot's nightly commit.

## Known limitations / next steps

- **Geographic scope**: NY State pilot only, but the pilot is done and
  live — **nationwide expansion is the active next phase** (see
  `STATUS.md`). Growing coverage means researching each new state's
  Area/Intergroup feeds the same way `sources/ny_sources.yaml` was built
  (most run the same TSML WordPress plugin), then deciding whether the
  registry becomes one YAML per state or a single file with a `state`
  field per source.
- **Program scope**: AA only for now. Adding NA/other 12-step programs later
  is straightforward since BMLT sources often carry both — tracked as a
  follow-up, not done here to keep the initial product focused.
- **Online/virtual meetings**: excluded from this pilot (in-person, mappable
  meetings only). Virtual meetings have no location and would need separate
  UI treatment (a list rather than a map).
- **Timezone**: the build/frontend assume America/New_York throughout, which
  is safe for a single-state NY pilot but would need per-meeting timezone
  handling before going nationwide.
- **BMLT field names**: `scripts/normalize/bmlt.py` is written against BMLT's
  documented semantic-API field names but has not yet been tested against a
  live NY-area root server response — verify field names once a real BMLT
  source is confirmed in the registry.
- **Nominatim at scale**: client-side geocoding of visitor searches is fine
  at pilot traffic levels; if this gets real public traffic, consider a
  self-hosted geocoder or a paid provider to stay comfortably within usage
  policies.
