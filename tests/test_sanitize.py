"""Regression tests for notes-field PII scrubbing.

Run with: python3 -m unittest discover -s tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from normalize.sanitize import sanitize_notes


class SanitizeNotesTests(unittest.TestCase):
    def test_drops_call_someone_at_phone_number(self):
        text = (
            "We meet at the church. In case of inclement weather (call Jason "
            "Fisher for verification: 917-496-9615) we meet indoors instead."
        )
        result = sanitize_notes(text)
        self.assertNotIn("Jason Fisher", result)
        self.assertNotIn("917-496-9615", result)
        self.assertIn("We meet at the church.", result)

    def test_drops_payment_app_sentences(self):
        text = "Hybrid meeting - For 7th Tradition send to PayPal.me/5thTraditionGroup - Karina C."
        result = sanitize_notes(text)
        self.assertIsNone(result)

    def test_redacts_zelle_email(self):
        text = "Zoom ID: 128 188 894\nDigital 7th Tradition Zelle: HandInHand11054@gmail.com"
        result = sanitize_notes(text)
        self.assertNotIn("HandInHand11054@gmail.com", result)
        self.assertIn("128 188 894", result)  # legit meeting id kept

    def test_keeps_zoom_meeting_id_and_passcode(self):
        text = "Zoom meeting information:\nMeeting ID:\n684 502 4754\nPassword:\nGWLAA"
        result = sanitize_notes(text)
        self.assertIn("684 502 4754", result)
        self.assertIn("GWLAA", result)

    def test_redacts_standalone_phone_number_with_no_meeting_context(self):
        text = "Group secretary: 555-123-4567"
        result = sanitize_notes(text)
        self.assertNotIn("555-123-4567", result)

    def test_passes_through_plain_logistics_note(self):
        text = "Enter through the side door. Masks optional."
        self.assertEqual(sanitize_notes(text), text)

    def test_none_and_empty_are_passthrough(self):
        self.assertIsNone(sanitize_notes(None))
        self.assertFalse(sanitize_notes(""))


if __name__ == "__main__":
    unittest.main()
