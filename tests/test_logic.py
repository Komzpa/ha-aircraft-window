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
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
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
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
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

    def test_far_descending_aircraft_is_approach_watch_candidate(self) -> None:
        candidate = logic.pick_candidate(
            [
                {
                    "hex": "738286",
                    "flight": "ISR890",
                    "lat": 41.98,
                    "lon": 41.92,
                    "alt_baro": 9200,
                    "baro_rate": -700,
                    "gs": 260,
                    "seen": 0.2,
                    "seen_pos": 0.3,
                    "rssi": -18,
                }
            ],
            home_latitude=41.62,
            home_longitude=41.62,
            max_positioned_distance_km=8,
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
            max_no_position_seen_seconds=4,
            source="test",
            enrich=lambda _aircraft: {
                "airline_name": "Israir",
                "origin_speech": "Тель-Авива",
                "destination_speech": "Батуми",
                "aircraft_model_speech": "Аэробус триста двадцать",
                "spoken_flight": "восемь девять ноль",
                "service_type": "passenger",
                "service_type_confidence": 0.74,
            },
        )

        self.assertEqual(candidate.phase, "positioned_approach")
        self.assertGreaterEqual(candidate.confidence, 0.55)
        self.assertIn("Заходит на посадку пассажирский рейс", candidate.announcement)
        self.assertIn("Исра Эйр", candidate.announcement)
        self.assertIn("Из Тель-Авива", candidate.announcement)

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

        self.assertTrue(text.startswith("Особое объявление."))
        self.assertIn("New Example Air", text)

    def test_positioned_unknown_route_says_aircraft_not_flight(self) -> None:
        text = logic.build_announcement(
            {"hex": "49d2d6", "flight": "VAA020"},
            "positioned_landing",
            0.8,
            {
                "airline_name": "Van Air Europe",
                "aircraft_model_speech": (
                    "Лет четыреста десять Турболет, небольшой двухмоторный турбовинтовой"
                ),
                "built_year_speech": "тысяча девятьсот девяностого года",
                "spoken_flight": "ноль два ноль",
            },
        )

        self.assertIn("Заходит на посадку самолёт Ван Эйр ноль два ноль.", text)
        self.assertNotIn("Заходит на посадку рейс", text)

    def test_service_type_classification_is_conservative(self) -> None:
        passenger = {
            "airline_name": "Flydubai",
            "origin_iata": "DXB",
            "destination_iata": "BUS",
            "route_summary": "DXB → BUS",
        }
        service_type, confidence, reason = logic.classify_service_type(passenger)
        passenger["service_type"] = service_type
        passenger["service_type_confidence"] = confidence
        passenger["service_type_reason"] = reason
        self.assertEqual(service_type, "passenger")
        self.assertEqual(logic.service_object_word(passenger), "пассажирский рейс")

        cargo = {
            "airline_name": "DHL Aviation",
            "aircraft_model": "Boeing 757 Freighter",
            "aircraft_type": "B752",
        }
        self.assertEqual(logic.classify_service_type(cargo)[0], "cargo")
        cargo["service_type"] = "cargo"
        cargo["service_type_confidence"] = 0.78
        self.assertEqual(logic.service_object_word(cargo), "грузовой самолёт")

        mixed = {
            "airline_name": "Van Air Europe",
            "aircraft_model": "L-410 UVP-E4",
            "aircraft_type": "L410",
            "adsb_category": "A1",
        }
        self.assertEqual(logic.classify_service_type(mixed)[0], "unknown")
        self.assertEqual(logic.service_object_word(mixed), "самолёт")

        express_passenger = {
            "airline_name": "Air India Express",
            "origin_iata": "DXB",
            "destination_iata": "BOM",
            "route_summary": "DXB → BOM",
        }
        self.assertEqual(logic.classify_service_type(express_passenger)[0], "unknown")

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

        self.assertEqual(
            text,
            "Дополнение: это Исра Эйр восемь девять ноль, в Тель-Авив.",
        )
        self.assertNotIn("Вылетает", text)
        self.assertNotIn("Аэробус", text)
        self.assertNotIn("шестнадцатого", text)

    def test_visible_military_aircraft_is_special_interest_candidate(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "48d841",
                "flight": "PLF033",
                "alt_baro": 15000,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "aircraft_model": "C-295 M",
                "aircraft_type": "C295",
                "aircraft_model_speech": "C-295 M",
                "registration": "012",
                "registered_owner": "Polish Air Force",
                "operator_flag_code": "PLF",
                "built_year_speech": "две тысячи третьего года",
                "spoken_flight": "ноль три три",
            },
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "military_visible")
        self.assertIn("Военный самолёт", candidate.announcement)
        self.assertIn("Польские ВВС", candidate.announcement)
        self.assertIn("C-295 M", candidate.announcement)

    def test_emergency_squawk_is_special_interest_candidate(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "abc770",
                "flight": "TST7700",
                "squawk": "7700",
                "alt_baro": 12000,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "airline_name": "Flydubai",
                "spoken_flight": "семь семь ноль ноль",
                "service_type": "unknown",
            },
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "emergency_squawk")
        self.assertEqual(candidate.squawk, "7700")
        self.assertEqual(candidate.event_key, "emergency_squawk:abc770:TST7700:7700")
        self.assertIn("Особый код транспондера", candidate.announcement)
        self.assertIn("сквок 7700: аварийная ситуация", candidate.announcement)

    def test_common_squawk_is_not_special_by_itself(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "abc700",
                "flight": "TST7000",
                "squawk": "7000",
                "alt_baro": 12000,
                "seen": 1.0,
            },
            source="test",
            aircraft_count=1,
            enrichment={"service_type": "unknown"},
        )

        self.assertIsNone(candidate)

    def test_watched_squawk_is_special_interest_candidate(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "abc777",
                "flight": "TST7777",
                "squawk": "7777",
                "alt_baro": 12000,
                "seen": 1.0,
            },
            source="test",
            aircraft_count=1,
            enrichment={"service_type": "unknown"},
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "special_interest")
        self.assertEqual(candidate.interest_type, "watched_squawk")
        self.assertEqual(candidate.squawk_label, "особый код транспондера, возможно военный")
        self.assertIn("Интересный самолёт", candidate.announcement)
        self.assertIn("сквок 7777", candidate.announcement)

    def test_ident_is_special_interest_candidate(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "abc123",
                "flight": "TST123",
                "spi": True,
                "seen": 1.0,
            },
            source="test",
            aircraft_count=1,
            enrichment={"service_type": "unknown"},
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "special_interest")
        self.assertEqual(candidate.interest_type, "ident")
        self.assertIn("самолёт нажал IDENT", candidate.announcement)

    def test_operational_metadata_interest_candidates(self) -> None:
        cases = [
            ("MED001", "medical helicopter", "medevac"),
            ("POL001", "police air support", "police"),
            ("CAL001", "flight check calibration", "calibration"),
            ("DRN001", "Bayraktar TB2 UAV", "drone"),
        ]
        for flight, owner, interest_type in cases:
            with self.subTest(interest_type=interest_type):
                candidate = logic.interest_candidate(
                    {"hex": "abc123", "flight": flight, "seen": 1.0},
                    source="test",
                    aircraft_count=1,
                    enrichment={
                        "registered_owner": owner,
                        "aircraft_model": owner,
                        "service_type": "unknown",
                    },
                )

                assert candidate is not None
                self.assertEqual(candidate.phase, "special_interest")
                self.assertEqual(candidate.interest_type, interest_type)

    def test_military_tanker_gets_specific_visible_label(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "ae0123",
                "flight": "RCH135",
                "seen": 1.0,
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "operator_flag_code": "RCH",
                "aircraft_type": "K35R",
                "aircraft_model": "KC-135R Stratotanker",
                "service_type": "military",
                "spoken_flight": "один три пять",
            },
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "military_visible")
        self.assertEqual(candidate.interest_type, "military_tanker")
        self.assertIn("военный самолёт-заправщик", candidate.announcement)

    def test_history_position_backfill_can_promote_no_position_candidate(self) -> None:
        aircraft = {
            "hex": "48d841",
            "flight": "PLF033",
            "alt_baro": 1800,
            "baro_rate": -500,
            "seen": 1.0,
            "rssi": -4,
            "messages": 50,
        }
        backfilled = logic.backfill_position_from_history(
            aircraft,
            [
                {
                    "now": 1000.0,
                    "aircraft": [
                        {
                            "hex": "48d841",
                            "lat": 41.62,
                            "lon": 41.61,
                            "seen_pos": 8.0,
                        }
                    ],
                }
            ],
        )

        candidate = logic.pick_candidate(
            [backfilled],
            home_latitude=41.62,
            home_longitude=41.62,
            max_positioned_distance_km=8,
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
            max_no_position_seen_seconds=4,
            source="test",
        )

        self.assertEqual(candidate.phase, "positioned_landing")
        self.assertEqual(candidate.position_source, "skyaware_history")
        self.assertEqual(candidate.position_age_seconds, 8.0)

    def test_kutaisi_route_is_special_interest_candidate(self) -> None:
        candidate = logic.interest_candidate(
            {"hex": "abc123", "flight": "WZZ123", "seen": 1.0},
            source="test",
            aircraft_count=1,
            enrichment={
                "airline_name": "Wizz Air",
                "origin_iata": "KUT",
                "origin_speech": "Кутаиси",
                "destination_iata": "RIX",
                "destination_speech": "Ригу",
                "spoken_flight": "один два три",
            },
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "kutaisi_route")
        self.assertIn("рейс из Кутаиси", candidate.announcement)
        self.assertIn("Кутаиси - Ригу", candidate.announcement)
        self.assertFalse(candidate.unusual_aircraft)

    def test_speech_helpers(self) -> None:
        self.assertEqual(logic.spoken_flight("RWZ553", airline_icao="RWZ"), "пять пять три")
        self.assertEqual(
            logic.spoken_flight("VAA020", airline_icao="VAA"),
            "ноль два ноль",
        )
        self.assertEqual(
            logic.known_airline_for_callsign("VAA020"),
            ("Van Air Europe", "VAA"),
        )
        self.assertEqual(
            logic.known_route_for_callsign("VAA021")["route_summary"],
            "BUS → Natakhtari",
        )
        self.assertEqual(
            logic.known_route_for_callsign("VAA021")["airline_name"],
            "Vanilla Sky",
        )
        self.assertEqual(
            logic.spoken_model("L-410 UVP-E4", "L410"),
            "Лет четыреста десять Турболет, небольшой двухмоторный турбовинтовой",
        )
        self.assertEqual(
            logic.spoken_model("Airbus A320-232", "A320"),
            "Аэробус триста двадцать",
        )
        self.assertEqual(
            logic.extract_airport_data_year("<b>Year built:</b></td><td>2012</td>"),
            2012,
        )
        self.assertEqual(logic.spoken_year(1990), "тысяча девятьсот девяностого года")


if __name__ == "__main__":
    unittest.main()
