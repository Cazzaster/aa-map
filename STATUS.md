# AA Meeting Finder (NY Pilot) — Status

**Repo:** https://github.com/Cazzaster/aa-map (**public**, Pages enabled)
**Last session:** September 7, 2026
**Live:** https://cazzaster.github.io/aa-map/

## What this is

Free, public "enter your location, find nearby AA meetings" map for New York
State. A pilot before nationwide expansion — built to give away for free
(your partner's "pay it forward" goal) and to double as a GeoAI portfolio
piece. No backend: a nightly GitHub Actions job rebuilds a GeoJSON file that
a static MapLibre frontend reads directly.

## Current state (all done this session)

- [x] Source registry (`sources/ny_sources.yaml`): **8 verified** NY
      Area/Intergroup feeds (~4,900 in-person/hybrid meetings after
      filtering out online-only/inactive), **Westchester already covered**
      by the existing NYC feed (no separate source needed), **2
      known-restricted** (Buffalo, Rockland — feed exists but returns
      `feed_restricted`, a deliberate site-owner choice, don't bypass),
      **2 remaining gaps** (Binghamton, Elmira — small hand-maintained
      sites with no structured feed at all)
- [x] Normalizer + build pipeline (`scripts/`) — tested end-to-end against
      the real feeds, produces `docs/data/meetings.geojson`
- [x] Static MapLibre frontend (`docs/`) — address/ZIP or geolocation
      search, radius + day/time filters, green pushpin markers for results,
      red pushpin for the searched location
- [x] Nightly GitHub Actions rebuild (`.github/workflows/update-meetings.yml`)
- [x] Pushed to GitHub (private repo, initial commit `d29ba80`)
- [x] Functionality code review completed (high effort) — 6 findings,
      **all 6 fixed this session** (see below), verified with a real
      build run and a live browser check (50-mile NYC search)

## Code review findings — all fixed

1. **`scripts/geocode.py`** — response parsing (Census + Nominatim) now
   lives inside the try/except, with `KeyError`/`IndexError`/`TypeError`
   added so a malformed response can no longer crash the nightly build.
2. **`scripts/geocode.py`** — failed geocode lookups are no longer cached;
   they're retried on every build instead of being silently and
   permanently dropped from the map after one transient API hiccup.
3. **`docs/app.js`** — `loadMeetings()` now wraps the fetch in try/catch
   and shows an error status instead of hanging forever on "Loading
   meeting data…".
4. **`docs/app.js`** — map markers are capped at `MAX_MAP_MARKERS` (300);
   the status line tells the user when results were truncated on the map
   (results list itself still shows everything). Verified live: a 50-mile
   NYC search returned 429 meetings and showed "Showing the nearest 300
   on the map — narrow your search to see the rest there too."
5. **`scripts/normalize/meeting_guide_json.py`** — an unparseable time
   string now becomes `None` (renders as "Time varies") instead of
   passing through and showing "NaN:NaN AM".
6. **`scripts/build_dataset.py`** — added `dedup_meetings()`, keyed on
   normalized name+address+day+time. A real build run removed 126
   duplicates between the NYC and Queens feeds (4,709 → 4,583 meetings
   written to `docs/data/meetings.geojson`).

## Privacy audit — personal info found and scrubbed

A repo-wide check for API keys/secrets found none. But the free-text
`notes` field (unlike the dedicated contact fields, which were already
stripped) was passing upstream feed text through verbatim, and it
contained real personal info already committed in `d29ba80`: a named
individual's personal cell phone number (City Island Beach Group, NYC
feed), a personal PayPal handle tied to a first name + last initial, and
a Zelle email/account number (Capital District and Queens feeds).

Fixed with a new `scripts/normalize/sanitize.py::sanitize_notes()`,
wired into both `meeting_guide_json.py` and `bmlt.py`: drops any sentence
mentioning Venmo/Zelle/PayPal/CashApp/Apple Pay, drops any sentence that
pairs a call/text/contact verb with a phone number, redacts bare email
addresses, and — belt-and-suspenders per your request — redacts *any*
remaining phone-shaped number in a note unless the note is clearly about
remote-meeting access (Zoom/Webex/dial-in/passcode/etc., needed to
actually join a hybrid meeting). Rebuilt the dataset and verified by
scanning every note for phone/email/payment patterns: zero personal
matches remain; all ~105 remaining phone-shaped strings are confirmed
Zoom/meeting-ID logistics.

**Git history rewrite:** the original personal info was already committed
in `d29ba80`. Since the repo had only 2 commits and your partner had just
accepted the collaboration invite, we rewrote history (via
`git filter-branch` with a tree-filter running the same scrub logic) to
remove it retroactively, then force-pushed. Old commit hashes
`d29ba80`/`1bcd658` no longer exist on `main`; the equivalent clean
commits are new hashes. **Your partner needs to re-clone the repo (or
`git fetch && git reset --hard origin/main`)** rather than pull, since
this was a forced history rewrite.

## Test suite + additional improvements (this session)

Went through the post-review improvement list and knocked out the quick,
safe ones:

- **Tests** (`tests/`, new): 16 unit tests (stdlib `unittest`, no new
  dependency) covering the notes sanitizer, cross-feed dedup, and the
  TSML/Meeting Guide time parser + attendance filtering. Wired into a new
  `.github/workflows/tests.yml` so every push/PR runs them.
- **Results list capped** (`docs/app.js`): a pathological huge-radius
  query now caps the sidebar list at `MAX_LIST_RESULTS` (1000), same idea
  as the earlier map-marker cap but a higher ceiling since list items are
  far cheaper to render than map markers.
- **Instant search feedback** (`docs/app.js`): `runSearch()` now sets
  "Searching…" immediately instead of only showing status once geocoding
  finishes.
- **By-appointment meetings surfaced** (`docs/app.js`): "Today"/"Today,
  starting from now" filters exclude meetings with no fixed day/time by
  design (nothing to compare against), but that used to look
  indistinguishable from "no meetings nearby." The status line now says
  e.g. "3 by-appointment meeting(s) nearby not shown — search 'Any time'
  to see them."

Not done (need more time/research or your decision, not code changes):
emailing Buffalo/Rockland intergroups, and nightly-build failure
monitoring (GitHub already emails repo owners on failed Actions runs by
default, so this is likely a non-issue as long as those notifications
are on).

All of the above, plus the 6 code-review fixes and the privacy fixes, are
committed and pushed to `main`.

## New coverage: Rochester added, Westchester was already covered

You asked what geographic areas could still be added. Investigated all
four open regions:

- **Rochester — added.** `/wp-json/tsml/meetings` is disabled outright
  (404, not a permissions block), but the human-facing meeting-finder
  page (`?post_type=tsml_meeting&tsml-day=N`) embeds the full dataset —
  name/time/day/types plus location name/address/lat/lon, and unlike
  every JSON feed, **no free-text notes field at all** — as a
  `var locations = {...}` JS blob, one weekday per request. The earlier
  "WAF-blocked" finding turned out to be a burst-rate rule, not a hard
  block: a single isolated request succeeds fine. New
  `scripts/normalize/rochester.py` fetches all 7 days, 3 seconds apart
  (once a night — nowhere near burst territory), extracts that blob, and
  filters out the "Online" placeholder location the same way the other
  feeds filter `attendance_option: online`. Added **319 meetings**,
  confirmed live in the browser (Rochester search: 106 meetings within 5
  miles) and via a real build run with zero errors.
- **Westchester — no work needed.** westchesternyaa.org has no feed of
  its own; its own "Westchester Meetings" button links straight to
  `nyintergroup.org/meetings/?region=westchester-county` — the *same*
  feed already registered as `ny_intergroup_nyc`, which we already pull
  in full. Confirmed ~130 meetings in the dataset already match
  Westchester towns (White Plains, Yonkers, New Rochelle, etc). Updated
  the registry notes to record this so nobody re-investigates it later.
- **Binghamton and Elmira — still gaps, deprioritized.** Both are small,
  hand-maintained sites with meeting times written as prose in a normal
  HTML page (Binghamton) or behind ordinary site navigation with no
  feed we could find in a quick pass (Elmira) — no TSML/BMLT/JSON
  anywhere. Scraping either would mean parsing free-text layout that
  breaks the moment the site gets redesigned, for a much smaller area
  than Rochester. Lowest priority of what's left; a direct email asking
  for a data export is probably more durable than a scraper here.

Also added: a shared `scripts/normalize/timeparse.py` (extracted from
the Meeting Guide parser, now also handles "Noon"/"Midnight" literals
which Rochester's feed uses), plus tests for both new modules (9 more
tests, 25 total). Full rebuild verified clean: 4,902 meetings, zero PII
matches on a full rescan, all tests passing.

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

- [x] Fix the 6 code review findings — done, committed, pushed
- [x] Privacy audit: scrub personal info from notes field + rewrite git
      history to remove it retroactively — done, committed, pushed
- [x] Tests + a few frontend UX improvements — done, committed, pushed
- [x] Flip repo to public + enable GitHub Pages — done, live at
      https://cazzaster.github.io/aa-map/
- [x] Rochester feed added, Westchester confirmed already covered —
      done, committed, pushed
- [ ] Binghamton, Elmira: no structured feed found; would need a custom
      scraper (fragile) or a direct data-export request — deprioritized
- [ ] Consider emailing Buffalo/Rockland intergroups directly about
      getting their restricted feeds included

## Resume prompt (paste into a new session)

> Continue the aa-map project (`~/ai-projects/aa-map`, private GitHub repo
> `Cazzaster/aa-map`). Read `STATUS.md` for full context. Last session: built
> and pushed the NY pilot end-to-end, tested it live in a browser, added
> pushpin markers, and ran a functionality code review that surfaced 6 open
> findings (listed in STATUS.md). Next I want to: [fill in]
