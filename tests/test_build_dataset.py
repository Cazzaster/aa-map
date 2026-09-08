"""Regression tests for cross-feed meeting deduplication."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_dataset import dedup_meetings
from normalize.schema import Meeting


def _meeting(source_id, name="Group", address="123 Main St", day=1, time="19:00"):
    return Meeting(source_id=source_id, name=name, day=day, time=time, address=address)


class DedupMeetingsTests(unittest.TestCase):
    def test_drops_exact_duplicate_across_feeds(self):
        a = _meeting("ny_intergroup_nyc")
        b = _meeting("queens_aa")
        result = dedup_meetings([a, b])
        self.assertEqual(len(result), 1)

    def test_keeps_distinct_meetings(self):
        a = _meeting("ny_intergroup_nyc", name="Group A")
        b = _meeting("ny_intergroup_nyc", name="Group B")
        result = dedup_meetings([a, b])
        self.assertEqual(len(result), 2)

    def test_whitespace_and_case_insensitive_match(self):
        a = _meeting("ny_intergroup_nyc", name="Monday  Night  Group", address="123 Main St")
        b = _meeting("queens_aa", name="monday night group", address="123  main st")
        result = dedup_meetings([a, b])
        self.assertEqual(len(result), 1)

    def test_different_day_or_time_not_deduped(self):
        a = _meeting("ny_intergroup_nyc", day=1)
        b = _meeting("queens_aa", day=2)
        result = dedup_meetings([a, b])
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
