"""Tests for Aircraft Window pure aircraft logic."""

from __future__ import annotations

import sys
import unittest
from importlib import util
from pathlib import Path

LOGIC_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "aircraft_window"
    / "logic.py"
)
SPEC = util.spec_from_file_location("aircraft_window_logic", LOGIC_PATH)
assert SPEC is not None and SPEC.loader is not None
logic = util.module_from_spec(SPEC)
sys.modules[SPEC.name] = logic
SPEC.loader.exec_module(logic)


class AircraftWindowLogicTest(unittest.TestCase):
    """Verify the logic that does not need Home Assistant."""

    def test_landing_announcement_contains_route_model_and_year(self) -> None:
        aircraft = {
            "hex": "4BCE01",
            "flight": "FDB1711",
            "lat": 41.61,
            "lon": 41.62,
            "alt_baro": 950,
            "baro_rate": -512,
            "gs": 145,
            "seen": 0.2,
            "seen_pos": 0.3,
            "rssi": -6,
        }

        candidate = logic.pick_candidate(
            [aircraft],
            home_latitude=41.62,
            home_longitude=41.62,
            max_positioned_distance_km=8,
            max_no_position_seen_seconds=4,
            source="test",
            enrich=lambda _aircraft: {
                "airline_name": "Flydubai",
                "origin_speech": "Дубая",
                "destination_speech": "Батуми",
                "aircraft_model": "Boeing 737 MAX 8",
                "aircraft_type": "B38M",
                "aircraft_model_speech": "Боинг семьсот тридцать семь MAX восемь",
                "built_year": 2019,
                "built_year_speech": "две тысячи девятнадцатого года",
                "spoken_flight": "один семь один один",
            },
        )

        self.assertEqual(candidate.phase, "positioned_landing")
        self.assertIn("Флай Дубай", candidate.announcement)
        self.assertIn("Из Дубая", candidate.announcement)
        self.assertIn("Боинг семьсот тридцать семь MAX восемь", candidate.announcement)
        self.assertIn("две тысячи девятнадцатого года", candidate.announcement)

    def test_no_position_candidate_uses_enrichment_and_mentions_missing_coordinates(self) -> None:
        candidate = logic.pick_candidate(
            [
                {
                    "hex": "152052",
                    "flight": "RWZ553",
                    "alt_baro": 1800,
                    "seen": 0.4,
                    "rssi": -4,
                    "messages": 42,
                }
            ],
            home_latitude=41.62,
            home_longitude=41.62,
            max_positioned_distance_km=8,
            max_no_position_seen_seconds=4,
            source="test",
            enrich=lambda _aircraft: {
                "airline_name": "Red Wings",
                "origin_speech": "Сочи",
                "destination_speech": "Батуми",
                "aircraft_model": "Tupolev Tu-214",
                "aircraft_type": "T214",
                "aircraft_model_speech": "Ту-двести четырнадцать",
                "built_year": 2008,
                "built_year_speech": "две тысячи восьмого года",
                "spoken_flight": "пять пять три",
            },
        )

        self.assertEqual(candidate.phase, "no_position_nearby")
        self.assertIn("без координат", candidate.announcement)
        self.assertIn("Ред Вингс", candidate.announcement)
        self.assertIn("Сочи - Батуми", candidate.announcement)
        self.assertIn("Ту-двести четырнадцать", candidate.announcement)
        self.assertIn("две тысячи восьмого года", candidate.announcement)

    def test_unmapped_airline_and_model_are_marked_unusual(self) -> None:
        text = logic.build_announcement(
            {"hex": "abc123", "flight": "ZZZ404"},
            "positioned_takeoff",
            0.8,
            {
                "airline_name": "New Example Air",
                "destination_speech": "Тбилиси",
                "aircraft_model": "Mystery Jet 9000",
                "aircraft_model_speech": "Mystery Jet 9000",
                "spoken_flight": "четыре ноль четыре",
            },
        )

        self.assertTrue(text.startswith("Необычное."))
        self.assertIn("New Example Air", text)

    def test_followup_announcement_adds_new_callsign_without_repeating_model(self) -> None:
        previous = logic.AircraftCandidate(
            state="positioned_takeoff:738286:738286",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:738286:738286",
            hex="738286",
            flight="738286",
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year=2016,
            built_year_speech="две тысячи шестнадцатого года",
        )
        current = logic.AircraftCandidate(
            state="positioned_takeoff:738286:ISR890",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:738286:ISR890",
            hex="738286",
            flight="ISR890",
            airline_name="Israir",
            spoken_flight="восемь девять ноль",
            destination_speech="Тель-Авив",
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year=2016,
            built_year_speech="две тысячи шестнадцатого года",
        )

        text = logic.build_followup_announcement(previous, current)

        self.assertEqual(text, "Уточнение: это Исра Эйр восемь девять ноль, в Тель-Авив.")
        self.assertNotIn("Самолёт. Взлёт", text)
        self.assertNotIn("Аэробус", text)
        self.assertNotIn("шестнадцатого", text)

    def test_speech_helpers(self) -> None:
        self.assertEqual(logic.spoken_flight("RWZ553", airline_icao="RWZ"), "пять пять три")
        self.assertEqual(
            logic.spoken_model("Airbus A320-232", "A320"),
            "Аэробус триста двадцать",
        )
        self.assertEqual(
            logic.extract_airport_data_year("<b>Year built:</b></td><td>2012</td>"),
            2012,
        )


if __name__ == "__main__":
    unittest.main()
