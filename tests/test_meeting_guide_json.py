"""Regression tests for the Meeting Guide / TSML JSON normalizer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from normalize.meeting_guide_json import parse


class ParseTests(unittest.TestCase):
    def test_unparseable_time_becomes_none(self):
        raw = [{"name": "Test", "day": "monday", "time": "not-a-time", "attendance_option": "in_person"}]
        meetings = parse(raw, source_id="test")
        self.assertIsNone(meetings[0].time)

    def test_parses_12_hour_time(self):
        raw = [{"name": "Test", "day": 1, "time": "7:00 PM", "attendance_option": "in_person"}]
        meetings = parse(raw, source_id="test")
        self.assertEqual(meetings[0].time, "19:00")

    def test_excludes_online_only_meetings(self):
        raw = [{"name": "Online", "day": 1, "attendance_option": "online"}]
        meetings = parse(raw, source_id="test")
        self.assertEqual(meetings, [])

    def test_includes_hybrid_meetings(self):
        raw = [{"name": "Hybrid", "day": 1, "attendance_option": "hybrid"}]
        meetings = parse(raw, source_id="test")
        self.assertEqual(len(meetings), 1)

    def test_strips_contact_fields(self):
        raw = [{
            "name": "Test", "day": 1, "attendance_option": "in_person",
            "contact_name": "Jane Doe", "contact_phone": "555-1234",
        }]
        meetings = parse(raw, source_id="test")
        # Meeting dataclass has no contact_name/contact_phone attributes at all
        self.assertFalse(hasattr(meetings[0], "contact_name"))
        self.assertFalse(hasattr(meetings[0], "contact_phone"))


if __name__ == "__main__":
    unittest.main()
