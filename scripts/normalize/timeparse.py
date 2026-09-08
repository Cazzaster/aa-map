"""Shared "HH:MM" time-string parsing for source parsers.

Different feeds spell the same time differently: 24-hour "HH:MM", 12-hour
"H:MM AM/PM", or informal words like "Noon"/"Midnight" (seen in Rochester's
feed). Normalize all of them to 24-hour "HH:MM", local wall-clock time.
"""

from __future__ import annotations

from datetime import datetime

_WORDS = {"noon": "12:00", "midnight": "00:00"}


def parse_time(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    word = _WORDS.get(raw.lower())
    if word:
        return word
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(raw, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None  # unparseable — treat as unscheduled rather than showing garbage
