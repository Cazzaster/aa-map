"""Parser for BMLT (Basic Meeting List Toolbox) semantic-API results.

BMLT's GetSearchResults JSON uses its own field names/conventions, notably
weekday_tinyint = 1..7 for Sunday..Saturday (one-based), which we convert to
our 0..6 Sunday-based convention.

Some root servers expose format codes (open/closed/etc.) via a separate
GetFormats lookup keyed by id; for the pilot we just pass through whatever
format key/world_id strings BMLT gives us in the "formats" list, since most
root servers already include human-readable keys there.
"""

from __future__ import annotations

from datetime import date

from .sanitize import sanitize_notes
from .schema import Meeting

_CONTACT_FIELDS = {
    "email_contact_1", "email_contact_2",
    "phone_contact_1", "phone_contact_2",
    "contact_name_1", "contact_name_2",
}


def parse(raw_meetings: list[dict], source_id: str) -> list[Meeting]:
    today = date.today().isoformat()
    out = []
    for m in raw_meetings:
        for f in _CONTACT_FIELDS:
            m.pop(f, None)

        weekday = m.get("weekday_tinyint")
        day = int(weekday) - 1 if weekday not in (None, "") else None

        start_time = (m.get("start_time") or "")[:5] or None  # "HH:MM:SS" -> "HH:MM"
        duration = m.get("duration_time")
        end_time = None
        if start_time and duration:
            end_time = _add_duration(start_time, duration)

        formats = m.get("formats") or m.get("format_shared_id_list") or []
        if isinstance(formats, str):
            formats = [f.strip() for f in formats.split(",") if f.strip()]

        lat = m.get("latitude")
        lon = m.get("longitude")

        out.append(Meeting(
            source_id=source_id,
            name=m.get("meeting_name") or "Unnamed Meeting",
            day=day,
            time=start_time,
            end_time=end_time,
            types=formats,
            location_name=m.get("location_text"),
            address=m.get("location_street"),
            city=m.get("location_municipality"),
            state=m.get("location_province"),
            postal_code=m.get("location_postal_code_1"),
            latitude=float(lat) if lat not in (None, "") else None,
            longitude=float(lon) if lon not in (None, "") else None,
            notes=sanitize_notes(m.get("comments")),
            last_updated=today,
        ))
    return out


def _add_duration(start_hhmm: str, duration_hhmmss: str) -> str | None:
    try:
        sh, sm = (int(x) for x in start_hhmm.split(":")[:2])
        dh, dm = (int(x) for x in duration_hhmmss.split(":")[:2])
    except (ValueError, AttributeError):
        return None
    total = (sh * 60 + sm + dh * 60 + dm) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"
