"""Regression tests for the Rochester fetch+parse module.

Mocks requests.get so these run offline and don't hit the real site.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from normalize import rochester


def _page(locations: dict) -> str:
    return f"<html><script>var locations = {json.dumps(locations)};</script></html>"


def _response(text, status=200):
    class FakeResponse:
        def __init__(self, text, status):
            self.text = text
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                import requests
                raise requests.HTTPError(f"{self.status_code}")

    return FakeResponse(text, status)


class RochesterFetchTests(unittest.TestCase):
    def test_extracts_meetings_and_excludes_online_location(self):
        page = _page({
            "1": {
                "name": "Some Church",
                "latitude": 43.1,
                "longitude": -77.6,
                "formatted_address": "1 Main St, Rochester, NY 14604, USA",
                "meetings": [
                    {"time": "7:00 pm", "day": 2, "name": "Tuesday Group", "types": ["D", "O"]},
                ],
            },
            "2": {
                "name": "Online",
                "latitude": 43.0,
                "longitude": -77.0,
                "formatted_address": "Rochester, NY, USA",
                "meetings": [
                    {"time": "8:00 pm", "day": 2, "name": "Online Only Group", "types": ["ONL"]},
                ],
            },
        })

        with patch("normalize.rochester.requests.get", return_value=_response(page)), \
             patch("normalize.rochester.time.sleep"):
            meetings = rochester.fetch_meetings("rochester_area_intergroup", "https://example.test/")

        # 7 days fetched, each returning the same fixture -> 7x the real meeting
        names = [m.name for m in meetings]
        self.assertIn("Tuesday Group", names)
        self.assertNotIn("Online Only Group", names)
        real = next(m for m in meetings if m.name == "Tuesday Group")
        self.assertEqual(real.latitude, 43.1)
        self.assertEqual(real.longitude, -77.6)
        self.assertEqual(real.time, "19:00")
        self.assertEqual(real.day, 2)
        self.assertEqual(real.address, "1 Main St, Rochester, NY 14604, USA")

    def test_one_bad_day_does_not_drop_the_others(self):
        good_page = _page({
            "1": {
                "name": "Some Church",
                "latitude": 43.1,
                "longitude": -77.6,
                "formatted_address": "1 Main St, Rochester, NY 14604, USA",
                "meetings": [{"time": "7:00 pm", "day": 0, "name": "Sunday Group", "types": []}],
            },
        })

        call_count = {"n": 0}

        def fake_get(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _response("", status=406)
            return _response(good_page)

        with patch("normalize.rochester.requests.get", side_effect=fake_get), \
             patch("normalize.rochester.time.sleep"):
            meetings = rochester.fetch_meetings("rochester_area_intergroup", "https://example.test/")

        self.assertTrue(any(m.name == "Sunday Group" for m in meetings))
        self.assertEqual(call_count["n"], 7)


if __name__ == "__main__":
    unittest.main()
