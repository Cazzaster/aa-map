"""Parser for feeds that already speak the Meeting Guide JSON spec.

This covers both:
  - feed_type: meeting_guide_json  (a site publishing the spec directly)
  - feed_type: tsml                (the TSML WordPress plugin's
    /wp-json/tsml/v1/meetings endpoint, which is spec-compliant JSON)

Spec reference: https://github.com/code4recovery/spec
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from .schema import Meeting

# Meeting Guide spec sometimes uses "day" as a 0-6 int already matching our
# convention (Sunday=0); some older TSML installs emit weekday names instead.
_WEEKDAY_NAMES = {
    "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3,
    "thursday": 4, "friday": 5, "saturday": 6,
}

_CONTACT_FIELDS = {
    "contact_name", "contact_email", "contact_phone",
    "conference_url_notes", "conference_phone_notes",
}

# This pilot is in-person-only (a deliberate v1 scope decision). TSML feeds
# tag every meeting with attendance_option: "in_person" | "online" | "hybrid"
# | "inactive". "online" meetings carry no real address — TSML gives them an
# "approximate" placeholder lat/lon (often just the entity's general area)
# which would otherwise show up on the map as a fake in-person location.
# "inactive" meetings aren't currently running. Keep in_person + hybrid only,
# since hybrid meetings do have a real physical location.
_EXCLUDED_ATTENDANCE = {"online", "inactive"}


def _parse_day(raw) -> int | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        if raw.isdigit():
            return int(raw)
        return _WEEKDAY_NAMES.get(raw.strip().lower())
    return None


def _parse_time(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    # Spec allows "HH:MM" already; some feeds emit "H:MM AM/PM".
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(raw, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return raw  # last resort: pass through as-is rather than dropping data


def parse(raw_meetings: list[dict], source_id: str) -> list[Meeting]:
    today = date.today().isoformat()
    out = []
    for m in raw_meetings:
        if m.get("attendance_option") in _EXCLUDED_ATTENDANCE:
            continue

        types = m.get("types") or []
        if isinstance(types, str):
            types = [t.strip() for t in types.split(",") if t.strip()]

        lat = m.get("latitude")
        lon = m.get("longitude")

        notes = m.get("notes")
        # Strip any contact-person fields the upstream feed may include —
        # never republish who runs a meeting, only meeting logistics.
        for f in _CONTACT_FIELDS:
            m.pop(f, None)

        out.append(Meeting(
            source_id=source_id,
            name=m.get("name") or m.get("group") or "Unnamed Meeting",
            day=_parse_day(m.get("day")),
            time=_parse_time(m.get("time")),
            end_time=_parse_time(m.get("end_time")),
            types=types,
            location_name=m.get("location"),
            address=m.get("formatted_address") or m.get("address"),
            city=m.get("city"),
            # NOTE: real TSML feeds don't send separate city/state/postal_code
            # fields — everything's bundled into formatted_address above. Do
            # NOT fall back to m.get("region"): that's a neighborhood/area
            # label (e.g. "02 Greenwich Village & East Village"), not a state.
            state=m.get("state"),
            postal_code=m.get("postal_code") or m.get("zip"),
            latitude=float(lat) if lat not in (None, "") else None,
            longitude=float(lon) if lon not in (None, "") else None,
            notes=notes,
            last_updated=today,
        ))
    return out
