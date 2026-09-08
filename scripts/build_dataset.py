#!/usr/bin/env python3
"""Fetch every registered source feed, normalize to one schema, geocode
whatever's missing coordinates, and write data/meetings.geojson.

Run manually with:  python scripts/build_dataset.py
Run nightly by:      .github/workflows/update-meetings.yml
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geocode import geocode_missing
from normalize import PARSERS
from normalize import rochester

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "sources" / "ny_sources.yaml"
OUTPUT_PATH = ROOT / "docs" / "data" / "meetings.geojson"  # docs/ is the GitHub Pages root
_HEADERS = {"User-Agent": "aa-map/0.1 (public-service meeting finder)"}

# Sources whose data can't be fetched as one JSON GET + generic parse (e.g.
# Rochester needs 7 day-scoped HTML page fetches). These own their fetching
# entirely and just hand back finished Meeting objects.
SELF_FETCHING = {
    "rochester_html": rochester.fetch_meetings,
}


def load_sources() -> list[dict]:
    doc = yaml.safe_load(SOURCES_PATH.read_text())
    return doc.get("sources", [])


def fetch_feed(url: str) -> list[dict]:
    r = requests.get(url, headers=_HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    # Some feeds (BMLT especially) wrap the list; most Meeting Guide feeds
    # are a bare array.
    if isinstance(data, dict):
        for key in ("meetings", "data", "results"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return []
    return data


def _dedup_key(m) -> tuple:
    """Identity for a meeting independent of which source feed reported it.

    Overlapping regions (e.g. NYC/Queens border) can have the same physical
    meeting listed in two intergroups' feeds. Normalize name/address so
    whitespace/case differences between feeds don't defeat the match.
    """
    norm = lambda s: " ".join((s or "").split()).lower()
    return (norm(m.name), norm(m.address), m.day, m.time)


def dedup_meetings(meetings: list) -> list:
    seen = set()
    out = []
    for m in meetings:
        key = _dedup_key(m)
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def main() -> None:
    sources = load_sources()
    all_meetings = []
    skipped = []

    for src in sources:
        feed_type = src.get("feed_type")
        feed_url = src.get("feed_url")
        self_fetch = SELF_FETCHING.get(feed_type)
        parser = PARSERS.get(feed_type)

        if not (self_fetch or parser) or not feed_url:
            skipped.append((src["id"], "no verified feed — needs custom scraping"))
            continue

        try:
            if self_fetch:
                meetings = self_fetch(src["id"], feed_url)
            else:
                raw = fetch_feed(feed_url)
                meetings = parser(raw, source_id=src["id"])
        except Exception as exc:  # noqa: BLE001 — one bad source shouldn't kill the build
            skipped.append((src["id"], f"fetch/parse failed: {exc}"))
            continue

        all_meetings.extend(meetings)
        print(f"  {src['id']}: {len(meetings)} meetings")

    before_dedup = len(all_meetings)
    all_meetings = dedup_meetings(all_meetings)
    print(f"\nTotal meetings: {before_dedup} ({before_dedup - len(all_meetings)} duplicate(s) removed across overlapping feeds)")
    geocode_missing(all_meetings)

    features = [m.to_geojson_feature() for m in all_meetings]
    geojson = {"type": "FeatureCollection", "features": features}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(geojson, indent=2))
    print(f"Wrote {len(features)} meetings to {OUTPUT_PATH}")

    if skipped:
        print(f"\n{len(skipped)} source(s) skipped:")
        for source_id, reason in skipped:
            print(f"  - {source_id}: {reason}")


if __name__ == "__main__":
    main()
