"""Regression tests for the shared HH:MM time parser."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from normalize.timeparse import parse_time


class ParseTimeTests(unittest.TestCase):
    def test_24_hour(self):
        self.assertEqual(parse_time("19:00"), "19:00")

    def test_12_hour_with_space(self):
        self.assertEqual(parse_time("7:00 PM"), "19:00")

    def test_12_hour_no_space(self):
        self.assertEqual(parse_time("7:00PM"), "19:00")

    def test_noon(self):
        self.assertEqual(parse_time("Noon"), "12:00")
        self.assertEqual(parse_time("noon"), "12:00")

    def test_midnight(self):
        self.assertEqual(parse_time("Midnight"), "00:00")

    def test_unparseable_returns_none(self):
        self.assertIsNone(parse_time("whenever"))

    def test_none_and_empty(self):
        self.assertIsNone(parse_time(None))
        self.assertIsNone(parse_time(""))


if __name__ == "__main__":
    unittest.main()
