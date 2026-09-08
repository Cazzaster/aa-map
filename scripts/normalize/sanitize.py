"""Scrub personal info out of free-text fields upstream feeds don't structure.

Dedicated contact fields (contact_name, contact_email, ...) are already
dropped by each source parser. The `notes` field is different: it's free
text meant for meeting logistics ("enter through the side door"), but in
practice some feeds also use it for a member's personal cell number
("call Jason Fisher: 917-555-0100") or a 7th Tradition donation handle
(Venmo/Zelle/PayPal/CashApp, tied to a name or email). AA's anonymity
tradition means we republish meeting logistics only, never who runs or
funds a meeting — so that gets stripped rather than passed through
verbatim. Zoom/dial-in IDs and passcodes are left alone since they're
needed to actually attend a hybrid meeting.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PAYMENT_RE = re.compile(r"\b(venmo|zelle|cash\s?app|paypal|apple\s?pay)\b", re.I)
_PHONE_RE = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_CONTACT_VERB_RE = re.compile(r"\b(call|text|contact)\b", re.I)
# Any of these appearing anywhere in a note means the numbers in it are
# remote-meeting access info (Zoom ID, dial-in, passcode), not a personal
# phone number -- leave the whole note's numbers alone in that case.
_MEETING_ACCESS_RE = re.compile(
    r"\bzoom\b|\bwebex\b|\bgoogle\s*meet\b|\bmicrosoft\s*teams\b|"
    r"\bmeetings?\s*id\b|\bdial[- ]?in\b|\bconference\s*(line|call)?\b|"
    r"\bpasscode\b|\bpin\s*[:#]|\bcall[- ]?in\b|\bvirtual\b|\bonline\s*meeting\b",
    re.I,
)
# Split into sentence-ish chunks on ./!/? only when followed by whitespace
# and then a capital letter, digit, or opening paren -- avoids false splits
# on things like "PayPal.me/..." where the period isn't a sentence boundary.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")


def _is_personal_sentence(sentence: str) -> bool:
    if _PAYMENT_RE.search(sentence):
        return True
    return bool(_CONTACT_VERB_RE.search(sentence) and _PHONE_RE.search(sentence))


def sanitize_notes(text: str | None) -> str | None:
    if not text:
        return text

    text = _EMAIL_RE.sub("[redacted]", text)

    # Drop whole sentences that are clearly a payment ask, or a "call/text/
    # contact <someone> at <number>" instruction.
    out_lines = []
    for line in text.split("\n"):
        sentences = _SENTENCE_SPLIT_RE.split(line)
        kept = [s.strip() for s in sentences if s.strip() and not _is_personal_sentence(s)]
        out_lines.append(" ".join(kept))
    text = "\n".join(l for l in out_lines if l.strip())
    if not text:
        return None

    # Belt-and-suspenders: redact any phone number still left, unless this
    # note is clearly about remote-meeting access (Zoom ID, dial-in,
    # passcode, ...), in which case its numbers are meeting logistics, not
    # a personal contact number.
    if not _MEETING_ACCESS_RE.search(text):
        text = _PHONE_RE.sub("[number redacted]", text)

    return text.strip() or None
