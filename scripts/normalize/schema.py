"""Normalized meeting record shared by every source-specific parser.

Field conventions follow the Meeting Guide format spec (code4recovery.org/docs)
where practical, since most upstream feeds already speak that dialect:
  - day: 0-6, Sunday=0 ... Saturday=6
  - time / end_time: "HH:MM" 24-hour, in the meeting's local (wall-clock) time
  - types: list of Meeting Guide type codes (e.g. "O" open, "C" closed,
    "D" discussion, "BB" Big Book, "SP" speaker, "ONL" online, ...)

Deliberately excluded: any contact-person name/phone/email. AA's anonymity
tradition means we only publish meeting logistics, never who runs a meeting.
Source parsers must drop those fields even if the upstream feed includes them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict


@dataclass
class Meeting:
    source_id: str
    name: str
    day: int | None          # 0=Sunday..6=Saturday, None if "by appointment" / unscheduled
    time: str | None         # "HH:MM" 24hr local, None if unscheduled
    end_time: str | None = None
    types: list[str] = field(default_factory=list)
    location_name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = None
    last_updated: str | None = None  # ISO date this record was fetched/normalized

    @property
    def id(self) -> str:
        """Stable id so re-running the build doesn't reshuffle identity."""
        key = "|".join(
            str(v) for v in (
                self.source_id, self.name, self.day, self.time, self.address,
            )
        )
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    def to_geojson_feature(self) -> dict:
        props = asdict(self)
        lat, lon = props.pop("latitude"), props.pop("longitude")
        props["id"] = self.id
        geometry = None
        if lat is not None and lon is not None:
            geometry = {"type": "Point", "coordinates": [lon, lat]}
        return {"type": "Feature", "geometry": geometry, "properties": props}
