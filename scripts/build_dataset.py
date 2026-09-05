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

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "sources" / "ny_sources.yaml"
OUTPUT_PATH = ROOT / "docs" / "data" / "meetings.geojson"  # docs/ is the GitHub Pages root
_HEADERS = {"User-Agent": "aa-map/0.1 (public-service meeting finder)"}


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


def main() -> None:
    sources = load_sources()
    all_meetings = []
    skipped = []

    for src in sources:
        feed_type = src.get("feed_type")
        feed_url = src.get("feed_url")
        parser = PARSERS.get(feed_type)

        if not parser or not feed_url:
            skipped.append((src["id"], "no verified feed — needs custom scraping"))
            continue

        try:
            raw = fetch_feed(feed_url)
            meetings = parser(raw, source_id=src["id"])
        except Exception as exc:  # noqa: BLE001 — one bad source shouldn't kill the build
            skipped.append((src["id"], f"fetch/parse failed: {exc}"))
            continue

        all_meetings.extend(meetings)
        print(f"  {src['id']}: {len(meetings)} meetings")

    print(f"\nTotal meetings before geocoding: {len(all_meetings)}")
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
