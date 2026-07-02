"""Tests for Aircraft Window pure aircraft logic."""

from __future__ import annotations

import sys
import unicodedata
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

    def assert_tts_has_no_latin(self, text: str) -> None:
        """Verify a spoken announcement will not send Latin letters to TTS."""
        latin = [
            char for char in text if char.isalpha() and "LATIN" in unicodedata.name(char, "")
        ]
        self.assertEqual(latin, [])

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
                "aircraft_model_speech": "Боинг семьсот тридцать семь Макс восемь",
                "built_year": 2019,
                "built_year_speech": "две тысячи девятнадцатого года",
                "spoken_flight": "один семь один один",
            },
        )

        self.assertEqual(candidate.phase, "positioned_landing")
        self.assertIn("Флай Дубай", candidate.announcement)
        self.assertIn("Из Дубая", candidate.announcement)
        self.assertIn("Боинг семьсот тридцать семь Макс восемь", candidate.announcement)
        self.assertIn("две тысячи девятнадцатого года", candidate.announcement)
        self.assert_tts_has_no_latin(candidate.announcement)

    def test_jazeera_kuwait_announcement_uses_speech_mappings(self) -> None:
        aircraft = {
            "hex": "706131",
            "flight": "JZR615",
            "lat": 41.62,
            "lon": 41.60,
            "alt_baro": 1400,
            "baro_rate": -640,
            "gs": 160,
            "seen": 0.2,
            "seen_pos": 0.2,
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
                "airline_name": "JAZEERA AİRWAYS",
                "origin_speech": "Кувейта",
                "origin_name": "Kuwait (KWI)",
                "destination_speech": "Батуми",
                "destination_name": "Batumi (BUS)",
                "origin_iata": "KWI",
                "destination_iata": "BUS",
                "route_summary": "KWI → BUS",
                "route_source": "test",
                "aircraft_model_speech": "Аэробус триста двадцать",
                "spoken_flight": logic.spoken_flight("JZR615", airline_icao="JZR"),
            },
        )

        self.assertEqual(candidate.phase, "positioned_landing")
        self.assertIn("Джазира", candidate.announcement)
        self.assertIn("Из Кувейта", candidate.announcement)
        self.assertNotIn("джей эй зет", candidate.announcement)
        self.assert_tts_has_no_latin(candidate.announcement)

    def test_no_position_candidate_with_route_context_can_announce(self) -> None:
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
                "origin_name": "Sochi",
                "destination_speech": "Батуми",
                "destination_name": "Batumi (BUS)",
                "origin_iata": "AER",
                "destination_iata": "BUS",
                "route_summary": "AER → BUS",
                "route_source": "test",
                "aircraft_model": "Tupolev Tu-214",
                "aircraft_type": "T214",
                "aircraft_model_speech": "Ту-двести четырнадцать",
                "built_year": 2008,
                "built_year_speech": "две тысячи восьмого года",
                "spoken_flight": "пять пять три",
            },
        )

        self.assertEqual(candidate.phase, "no_position_nearby")
        self.assertIn("Приёмник видит прилёт без координат", candidate.announcement)
        self.assertIn("Ред Вингс", candidate.announcement)
        self.assertIn("Сочи - Батуми", candidate.announcement)
        self.assertFalse(candidate.announcement_suppressed)

    def test_high_altitude_no_position_aircraft_is_not_candidate(self) -> None:
        candidate = logic.pick_candidate(
            [
                {
                    "hex": "151d89",
                    "flight": "AFL426",
                    "alt_baro": 36000,
                    "seen": 0.3,
                    "rssi": -5.2,
                    "messages": 268,
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
                "airline_name": "Aeroflot Russian Airlines",
                "origin_iata": "SVO",
                "origin_name": "Moscow (SVO)",
                "destination_name": "Sharm El Sheikh",
                "aircraft_model": "Boeing 737-800",
                "aircraft_type": "B738",
            },
        )

        self.assertEqual(candidate.phase, "idle")
        self.assertEqual(candidate.announcement, "")

    def test_no_position_candidate_without_route_context_is_silent(self) -> None:
        candidate = logic.pick_candidate(
            [
                {
                    "hex": "152559",
                    "flight": "VLK559",
                    "alt_baro": 1800,
                    "seen": 0.4,
                    "rssi": -4,
                    "messages": 559,
                }
            ],
            home_latitude=41.62,
            home_longitude=41.62,
            max_positioned_distance_km=8,
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
            max_no_position_seen_seconds=4,
            source="test",
            enrich=lambda _aircraft: {"spoken_flight": "пять пять девять"},
        )

        self.assertEqual(candidate.phase, "no_position_nearby")
        self.assertEqual(candidate.announcement, "")
        self.assertTrue(candidate.announcement_suppressed)
        self.assertIn("receiver-only", candidate.announcement_suppression_reason)

    def test_far_descending_aircraft_is_approach_watch_candidate(self) -> None:
        candidate = logic.pick_candidate(
            [
                {
                    "hex": "738286",
                    "flight": "ISR890",
                    "lat": 41.8,
                    "lon": 41.2,
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
                "origin_speech": "Бен Гуриона",
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
        self.assertIn("Из Бен Гуриона", candidate.announcement)

    def test_approach_uses_geometric_window_view(self) -> None:
        visible = logic.pick_candidate(
            [
                {
                    "hex": "abc123",
                    "flight": "TST123",
                    "lat": 41.8,
                    "lon": 41.2,
                    "alt_baro": 2000,
                    "baro_rate": -500,
                    "gs": 160,
                    "track": 300,
                    "seen": 0,
                    "seen_pos": 0,
                }
            ],
            home_latitude=41.62121824843062,
            home_longitude=41.59068703651429,
            max_positioned_distance_km=8,
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
            max_no_position_seen_seconds=4,
            source="test",
        )

        self.assertEqual(visible.phase, "positioned_approach")
        self.assertTrue(visible.window_visible)
        self.assertTrue(visible.window_preopen_needed)
        self.assertIn("inside window view polygon", visible.window_view_reason)

        outside_window = logic.pick_candidate(
            [
                {
                    "hex": "abc124",
                    "flight": "TST124",
                    "lat": 41.8,
                    "lon": 41.8,
                    "alt_baro": 2000,
                    "baro_rate": -500,
                    "gs": 160,
                    "track": 90,
                    "seen": 0,
                    "seen_pos": 0,
                }
            ],
            home_latitude=41.62121824843062,
            home_longitude=41.59068703651429,
            max_positioned_distance_km=8,
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
            max_no_position_seen_seconds=4,
            source="test",
        )

        self.assertEqual(outside_window.phase, "idle")
        self.assertIn("no nearby landing/takeoff candidate", outside_window.confidence_reason)

    def test_projected_window_view_sets_preopen_without_current_visibility(self) -> None:
        candidate = logic.pick_candidate(
            [
                {
                    "hex": "abc125",
                    "flight": "TST125",
                    "lat": 41.8,
                    "lon": 41.8,
                    "alt_baro": 2000,
                    "baro_rate": -500,
                    "gs": 160,
                    "track": 250,
                    "seen": 0,
                    "seen_pos": 0,
                }
            ],
            home_latitude=41.62121824843062,
            home_longitude=41.59068703651429,
            max_positioned_distance_km=8,
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
            max_no_position_seen_seconds=4,
            source="test",
        )

        self.assertEqual(candidate.phase, "positioned_approach")
        self.assertFalse(candidate.window_visible)
        self.assertTrue(candidate.window_preopen_needed)
        self.assertIn("projected into window view", candidate.window_view_reason)
        self.assertEqual(candidate.window_view_lead_seconds, 225.0)

    def test_runway_staging_sets_preopen_phase(self) -> None:
        candidate = logic.pick_candidate(
            [
                {
                    "hex": "abc126",
                    "flight": "TST126",
                    "lat": 41.6103,
                    "lon": 41.6004,
                    "alt_baro": "ground",
                    "gs": 5,
                    "seen": 0,
                    "seen_pos": 0,
                }
            ],
            home_latitude=41.62121824843062,
            home_longitude=41.59068703651429,
            max_positioned_distance_km=8,
            max_approach_distance_km=60,
            max_approach_altitude_ft=10000,
            max_no_position_seen_seconds=4,
            source="test",
        )

        self.assertEqual(candidate.phase, "positioned_runway_staging")
        self.assertFalse(candidate.window_visible)
        self.assertTrue(candidate.window_preopen_needed)
        self.assertTrue(candidate.window_runway_staging)

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
        self.assertIn("Нью Экзампл Эйр", text)
        self.assert_tts_has_no_latin(text)

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

    def test_routine_route_omits_flight_number_when_airline_and_route_are_known(self) -> None:
        text = logic.build_announcement(
            {"hex": "14fc25", "flight": "RWZ550"},
            "positioned_takeoff",
            0.75,
            {
                "airline_name": "RED WINGS AIRLINES",
                "destination_iata": "ZIA",
                "destination_speech": "подмосковный Жуковский",
                "spoken_flight": "пять пять ноль",
                "service_type": "passenger",
                "service_type_confidence": 0.74,
            },
        )

        self.assertIn("Вылетает пассажирский рейс Ред Вингс.", text)
        self.assertIn("В подмосковный Жуковский", text)
        self.assertNotIn("пять пять ноль", text)

    def test_routine_aircraft_without_context_is_silent(self) -> None:
        self.assertEqual(
            logic.build_announcement(
                {"hex": "155bf7", "flight": "AZO7053"},
                "positioned_approach",
                0.58,
                {"spoken_flight": "семь ноль пять три"},
            ),
            "",
        )

    def test_routine_aircraft_with_only_model_is_silent(self) -> None:
        self.assertEqual(
            logic.build_announcement(
                {"hex": "504e65", "flight": "504E65"},
                "positioned_takeoff",
                0.92,
                {
                    "aircraft_model_speech": "Аэробус триста двадцать",
                    "spoken_flight": "504E65",
                },
            ),
            "",
        )

    def test_routine_hex_fallback_uses_owner_not_raw_address(self) -> None:
        text = logic.build_announcement(
            {"hex": "504e65", "flight": "504E65"},
            "positioned_takeoff",
            0.92,
            {
                "registered_owner": "Fly One",
                "aircraft_model_speech": "Аэробус триста двадцать",
                "spoken_flight": "504E65",
            },
        )

        self.assertEqual(
            text,
            "Вылетает самолёт Флай Уан. Аэробус триста двадцать.",
        )
        self.assertNotIn("504E65", text)

    def test_routine_private_numbered_flight_keeps_owner_and_flight(self) -> None:
        text = logic.build_announcement(
            {"hex": "424242", "flight": "001"},
            "positioned_approach",
            0.73,
            {
                "registered_owner": "Example Jet Holdings",
                "aircraft_model_speech": "Гольфстрим",
                "spoken_flight": "ноль ноль один",
            },
        )

        self.assertIn("экзампл джет холдингс", text.lower())
        self.assertIn("ноль ноль один", text)
        self.assertIn("Гольфстрим", text)
        self.assert_tts_has_no_latin(text)

    def test_partial_route_arrival_says_origin_is_unknown(self) -> None:
        text = logic.build_announcement(
            {"hex": "155c60", "flight": "RWZ1565"},
            "positioned_approach",
            0.8,
            {
                "airline_name": "Red Wings",
                "destination_speech": "Батуми",
                "spoken_flight": "один пять шесть пять",
            },
        )

        self.assertIn("В Батуми, откуда летит, пока не определено", text)

    def test_partial_route_takeoff_says_destination_is_unknown(self) -> None:
        text = logic.build_announcement(
            {"hex": "155c60", "flight": "RWZ1566"},
            "positioned_takeoff",
            0.8,
            {
                "airline_name": "Red Wings",
                "origin_speech": "Батуми",
                "spoken_flight": "один пять шесть шесть",
            },
        )

        self.assertIn("Из Батуми, куда летит, пока не определено", text)

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

        azimuth = {
            "airline_name": "Azimuth Airlines",
            "origin_iata": "VKO",
            "destination_iata": "BUS",
            "route_summary": "VKO → BUS",
        }
        self.assertEqual(logic.classify_service_type(azimuth)[0], "passenger")

        cargo = {
            "airline_name": "DHL Aviation",
            "aircraft_model": "Boeing 757 Freighter",
            "aircraft_type": "B752",
        }
        self.assertEqual(logic.classify_service_type(cargo)[0], "cargo")
        cargo["service_type"] = "cargo"
        cargo["service_type_confidence"] = 0.78
        self.assertEqual(logic.service_object_word(cargo), "грузовой самолёт")

        business_jet = {
            "registered_owner": "Bonair Havacilik",
            "aircraft_model": "125 850XP",
            "aircraft_type": "H25B",
        }
        service_type, confidence, _reason = logic.classify_service_type(business_jet)
        business_jet["service_type"] = service_type
        business_jet["service_type_confidence"] = confidence
        self.assertEqual(service_type, "business_jet")
        self.assertEqual(logic.service_object_word(business_jet), "бизнес-джет")

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

    def test_service_type_metadata_tokens_require_boundaries(self) -> None:
        self.assertEqual(
            logic.classify_service_type(
                {"airline_name": "Upsilon Air", "aircraft_type": "A320"}
            )[0],
            "unknown",
        )
        self.assertFalse(logic.is_military_aircraft({"registered_owner": "Pharmacy Air"}))
        self.assertFalse(
            logic.is_business_jet(
                {"registered_owner": "Globalair", "aircraft_model": "Globalair 900"}
            )
        )

        self.assertEqual(
            logic.classify_service_type({"airline_name": "UPS Airlines"})[0],
            "cargo",
        )
        self.assertTrue(logic.is_military_aircraft({"registered_owner": "Example Army"}))
        self.assertTrue(logic.is_business_jet({"aircraft_model": "Global 6000"}))

    def test_followup_announcement_suppresses_callsign_only_update(self) -> None:
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
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year=2016,
            built_year_speech="две тысячи шестнадцатого года",
        )

        self.assertEqual(logic.build_followup_announcement(previous, current), "")

    def test_positioned_hawker_takeoff_says_business_jet(self) -> None:
        text = logic.build_announcement(
            {"hex": "4bcd05", "flight": "TCSHE"},
            "positioned_takeoff",
            0.92,
            {
                "registered_owner": "Bonair Havacilik",
                "aircraft_model": "125 850XP",
                "aircraft_type": "H25B",
                "aircraft_model_speech": logic.spoken_model("125 850XP", "H25B"),
                "spoken_flight": "TCSHE",
                "service_type": "business_jet",
                "service_type_confidence": 0.72,
            },
        )

        self.assertIn("Вылетает бизнес-джет Бонэйр Хаваджылык.", text)
        self.assertNotIn("ти си эс эйч и", text)
        self.assertIn("Хокер восемьсот пятьдесят икс пи", text)
        self.assertNotIn("125 850XP", text)
        self.assert_tts_has_no_latin(text)

    def test_positioned_pegasus_mixed_callsign_has_no_latin_for_tts(self) -> None:
        text = logic.build_announcement(
            {"hex": "4bb862", "flight": "PGT48DK"},
            "positioned_takeoff",
            0.87,
            {
                "registered_owner": "Pegasus Airlines",
                "aircraft_model": "A320 251NSL",
                "aircraft_type": "A20N",
                "aircraft_model_speech": logic.spoken_model("A320 251NSL", "A20N"),
                "operator_flag_code": "PGT",
                "spoken_flight": logic.spoken_flight("PGT48DK", airline_icao="PGT"),
            },
        )

        self.assertIn("Вылетает самолёт Пегасус четыре восемь ди кей.", text)
        self.assertIn("Аэробус триста двадцать", text)
        self.assertNotIn("PGT48DK", text)
        self.assert_tts_has_no_latin(text)

    def test_positioned_global_6000_hyp001_says_business_jet(self) -> None:
        enrichment = {
            "registered_owner": "Hyperion Aviation",
            "aircraft_model": "Global 6000",
            "aircraft_type": "GL6T",
            "aircraft_model_speech": logic.spoken_model("Global 6000", "GL6T"),
            "spoken_flight": "ноль ноль один",
        }
        service_type, confidence, _reason = logic.classify_service_type(enrichment)
        enrichment["service_type"] = service_type
        enrichment["service_type_confidence"] = confidence

        text = logic.build_announcement(
            {"hex": "4d206d", "flight": "HYP001"},
            "positioned_approach",
            0.72,
            enrichment,
        )

        self.assertEqual(service_type, "business_jet")
        self.assertIn("Заходит на посадку бизнес-джет Хайперион Авиэйшн ноль ноль один.", text)
        self.assertIn("Бомбардье Глобал шесть тысяч", text)
        self.assertNotIn("Global 6000", text)
        self.assertNotIn("самолёт ноль ноль один", text)
        self.assert_tts_has_no_latin(text)

    def test_positioned_challenger_gulf_wings_uses_clear_business_jet_speech(
        self,
    ) -> None:
        enrichment = {
            "registered_owner": "Gulf Wings",
            "aircraft_model": "Challenger 605",
            "aircraft_type": "CL65",
            "aircraft_model_speech": logic.spoken_model("Challenger 605", "CL65"),
            "operator_flag_code": "GWC",
            "spoken_flight": logic.spoken_flight("GWC2", airline_icao="GWC"),
        }
        service_type, confidence, _reason = logic.classify_service_type(enrichment)
        enrichment["service_type"] = service_type
        enrichment["service_type_confidence"] = confidence

        text = logic.build_announcement(
            {"hex": "8965f2", "flight": "GWC2"},
            "positioned_landing",
            0.87,
            enrichment,
        )

        self.assertEqual(service_type, "business_jet")
        self.assertIn("Заходит на посадку бизнес-джет Галф Вингс два.", text)
        self.assertIn("Бомбардье Челленджер шестьсот пятый", text)
        self.assertNotIn("Гулф", text)
        self.assertNotIn("Чалленгер", text)
        self.assertNotIn("Challenger", text)
        self.assertNotIn("Gulf", text)
        self.assert_tts_has_no_latin(text)

    def test_followup_announcement_omits_flight_number_when_route_is_new(self) -> None:
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
            destination_speech="Бен Гурион",
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year=2016,
            built_year_speech="две тысячи шестнадцатого года",
        )

        text = logic.build_followup_announcement(previous, current)

        self.assertEqual(
            text,
            "Дополнение: это Исра Эйр, в Бен Гурион.",
        )
        self.assertNotIn("Вылетает", text)
        self.assertNotIn("Аэробус", text)
        self.assertNotIn("шестнадцатого", text)

    def test_followup_announcement_rejects_arrival_to_departure_churn(self) -> None:
        previous = logic.AircraftCandidate(
            state="positioned_landing:155c66:RWZ567",
            phase="positioned_landing",
            event_key="positioned_landing:155c66:RWZ567",
            hex="155c66",
            flight="RWZ567",
            airline_name="RED WINGS AIRLINES",
            origin_speech="Сочи",
            destination_speech="Батуми",
        )
        current = logic.AircraftCandidate(
            state="positioned_takeoff:155c66:RWZ568",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:155c66:RWZ568",
            hex="155c66",
            flight="RWZ568",
            airline_name="RED WINGS AIRLINES",
            spoken_flight="пять шесть восемь",
            origin_speech="Батуми",
            destination_speech="Сочи",
        )

        self.assertEqual(logic.build_followup_announcement(previous, current), "")

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
        self.assertIn("си два девять пять эм", candidate.announcement)
        self.assert_tts_has_no_latin(candidate.announcement)

    def test_usaf_spar_huron_military_announcement_is_readable(self) -> None:
        enrichment = {
            "aircraft_model": "C-12C Huron",
            "aircraft_type": "C12C",
            "aircraft_model_speech": logic.spoken_model("C-12C Huron", "C12C"),
            "registered_owner": "United States Air Force",
            "spoken_flight": logic.spoken_flight("SPAR89"),
        }
        candidate = logic.interest_candidate(
            {
                "hex": "ae10e6",
                "flight": "SPAR89",
                "alt_baro": 15000,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment=enrichment,
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "military_visible")
        self.assertIn("ВВС США Спар восемь девять", candidate.announcement)
        self.assertIn("Си-двенадцать Хьюрон", candidate.announcement)
        self.assertNotIn("Унитед", candidate.announcement)
        self.assertNotIn("эс пи эй ар", candidate.announcement)
        self.assert_tts_has_no_latin(candidate.announcement)

    def test_french_air_force_hercules_announcement_is_readable(self) -> None:
        enrichment = {
            "aircraft_model": "C-130J-30 Hercules",
            "aircraft_type": "C30J",
            "aircraft_model_speech": logic.spoken_model("C-130J-30 Hercules", "C30J"),
            "registration": "5847",
            "registered_owner": "French Air Force",
            "operator_flag_code": "CTM",
            "spoken_flight": logic.spoken_flight("CTM2085", airline_icao="CTM"),
        }
        service_type, confidence, reason = logic.classify_service_type(enrichment)
        enrichment["service_type"] = service_type
        enrichment["service_type_confidence"] = confidence
        enrichment["service_type_reason"] = reason

        candidate = logic.interest_candidate(
            {
                "hex": "3b77e6",
                "flight": "CTM2085",
                "alt_baro": 15000,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment=enrichment,
        )

        assert candidate is not None
        self.assertEqual(service_type, "military")
        self.assertEqual(candidate.phase, "military_visible")
        self.assertIn("французские ВВС два ноль восемь пять", candidate.announcement)
        self.assertIn("Си-сто тридцать Геркулес", candidate.announcement)
        self.assertNotIn("Френч", candidate.announcement)
        self.assertNotIn("Форке", candidate.announcement)
        self.assert_tts_has_no_latin(candidate.announcement)

    def test_civil_silk_way_il76_is_cargo_not_military(self) -> None:
        enrichment = {
            "airline_name": "Silk Way Airlines",
            "aircraft_model": "IL-76 TD-90SW",
            "aircraft_model_speech": "Ил-семьдесят шесть",
            "aircraft_type": "IL76",
            "registration": "4K-AZ100",
            "registered_owner": "Silk Way Airlines",
            "operator_flag_code": "AZQ",
            "spoken_flight": "четыре три три один",
        }
        service_type, confidence, _reason = logic.classify_service_type(enrichment)
        enrichment["service_type"] = service_type
        enrichment["service_type_confidence"] = confidence

        self.assertEqual(service_type, "cargo")
        self.assertFalse(logic.is_military_aircraft(enrichment))
        self.assertEqual(logic.airline_speech("Silk Way Airlines"), "Силк Вей")

        candidate = logic.interest_candidate(
            {
                "hex": "600864",
                "flight": "AZQ4331",
                "alt_baro": 15000,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment=enrichment,
        )

        self.assertIsNone(candidate)
        announcement = logic.build_announcement(
            {"hex": "600864", "flight": "AZQ4331"},
            "positioned_low_nearby",
            0.7,
            enrichment,
        )
        self.assertIn("грузовой самолёт Силк Вей", announcement)
        self.assertNotIn("Военный", announcement)
        self.assertNotIn("Силк Ваи", announcement)
        self.assert_tts_has_no_latin(announcement)

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
        self.assertIn("Нештатная ситуация у самолёта", candidate.announcement)
        self.assertIn("аварийная ситуация", candidate.announcement)
        self.assertNotIn("сквок", candidate.announcement.lower())
        self.assertNotIn("транспондер", candidate.announcement.lower())
        self.assertNotIn("7700", candidate.announcement)

    def test_rapid_descent_on_batumi_arrival_is_not_special_interest(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "5140de",
                "flight": "4L112",
                "alt_baro": 4200,
                "baro_rate": -4200,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "airline_name": "OneClick Airways",
                "destination_iata": "BUS",
                "destination_name": "Batumi (BUS)",
                "destination_speech": "Батуми",
                "route_summary": "TLV → BUS",
                "service_type": "passenger",
            },
        )

        self.assertIsNone(candidate)

    def test_rapid_descent_without_arrival_context_stays_special_interest(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "abc123",
                "flight": "TST123",
                "alt_baro": 4200,
                "baro_rate": -4200,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment={"service_type": "unknown"},
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "special_interest")
        self.assertEqual(candidate.interest_type, "rapid_descent")

    def test_batumi_arrival_turn_is_not_orbit_special_interest(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "738285",
                "flight": "ISR885",
                "alt_baro": 5200,
                "track_rate": 3.1,
                "gs": 180,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "airline_name": "Israir Airlines",
                "origin_iata": "TLV",
                "origin_name": "Tel Aviv",
                "destination_iata": "BUS",
                "destination_name": "Batumi (BUS)",
                "destination_speech": "Батуми",
                "route_summary": "TLV → BUS",
                "service_type": "passenger",
            },
        )

        self.assertIsNone(candidate)

    def test_batumi_departure_turn_is_not_orbit_special_interest(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "738285",
                "flight": "ISR414",
                "alt_baro": 5200,
                "track_rate": -3.1,
                "gs": 180,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "airline_name": "Israir Airlines",
                "origin_iata": "BUS",
                "origin_name": "Batumi (BUS)",
                "origin_speech": "Батуми",
                "destination_iata": "TLV",
                "destination_name": "Tel Aviv",
                "route_summary": "BUS → TLV",
                "service_type": "passenger",
            },
        )

        self.assertIsNone(candidate)

    def test_non_batumi_turn_stays_orbit_special_interest(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "abc123",
                "flight": "TST123",
                "alt_baro": 5200,
                "track_rate": 3.1,
                "gs": 180,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment={"service_type": "unknown"},
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "special_interest")
        self.assertEqual(candidate.interest_type, "orbiting")

    def test_emergency_squawk_on_batumi_arrival_stays_special_interest(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "abc770",
                "flight": "TST7700",
                "squawk": "7700",
                "alt_baro": 4200,
                "baro_rate": -4200,
                "seen": 1.0,
                "messages": 100,
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "destination_iata": "BUS",
                "destination_name": "Batumi (BUS)",
                "destination_speech": "Батуми",
                "route_summary": "TLV → BUS",
                "service_type": "passenger",
            },
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "emergency_squawk")

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

    def test_watched_squawk_is_not_a_voice_candidate_by_itself(self) -> None:
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

        self.assertIsNone(candidate)

    def test_ident_is_not_a_voice_candidate_by_itself(self) -> None:
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

        self.assertIsNone(candidate)

    def test_altitude_hold_nav_mode_is_not_special_interest_candidate(self) -> None:
        for nav_modes in (["althold", "tcas"], ["autopilot", "althold", "tcas"], "alt hold"):
            with self.subTest(nav_modes=nav_modes):
                candidate = logic.interest_candidate(
                    {
                        "hex": "155c20",
                        "flight": "AZO3029",
                        "seen": 1.0,
                        "alt_baro": 34975,
                        "baro_rate": -128,
                        "gs": 452,
                        "track": 98.4,
                        "nav_modes": nav_modes,
                    },
                    source="test",
                    aircraft_count=1,
                    enrichment={
                        "airline_name": "Azimuth Airlines",
                        "origin_iata": "KRR",
                        "origin_name": "Krasnodar",
                        "destination_iata": "EVN",
                        "destination_speech": "Ереван",
                        "aircraft_model_speech": "Суперджет",
                        "route_summary": "KRR → EVN",
                        "service_type": "unknown",
                    },
                )

                self.assertIsNone(candidate)

    def test_real_hold_nav_mode_is_special_interest_candidate(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "49d570",
                "flight": "DFC8GP",
                "seen": 1.0,
                "alt_baro": 7000,
                "gs": 180,
                "nav_modes": ["hold"],
            },
            source="test",
            aircraft_count=1,
            enrichment={"service_type": "unknown"},
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "special_interest")
        self.assertEqual(candidate.interest_type, "holding_or_orbit")

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
                self.assertNotIn("борт", candidate.announcement.lower())

    def test_drone_metadata_does_not_override_airbus_model(self) -> None:
        candidate = logic.interest_candidate(
            {"hex": "abc319", "flight": "AW319", "seen": 1.0},
            source="test",
            aircraft_count=1,
            enrichment={
                "registered_owner": "Example UAV Leasing",
                "aircraft_model": "Airbus A319",
                "aircraft_type": "A319",
                "aircraft_model_speech": logic.spoken_model("Airbus A319", "A319"),
                "service_type": "unknown",
            },
        )

        self.assertIsNone(candidate)

    def test_drone_metadata_requires_standalone_token(self) -> None:
        self.assertIsNone(
            logic.classify_special_interest(
                {"hex": "4a0442", "flight": "KRP459", "seen": 1.0},
                {
                    "airline_name": "Carpatair",
                    "registered_owner": "Carpatair",
                    "service_type": "unknown",
                },
            )
        )

        self.assertEqual(
            logic.classify_special_interest(
                {"hex": "abc123", "flight": "DRN001", "seen": 1.0},
                {
                    "registered_owner": "Bayraktar TB2 UAV",
                    "aircraft_model": "Bayraktar TB2",
                    "service_type": "unknown",
                },
            )[0],
            "drone",
        )

    def test_special_interest_metadata_tokens_require_boundaries(self) -> None:
        false_positive_cases = [
            ("medevac", "BiomedEvacuation Tours"),
            ("police", "Policeair Charter"),
            ("calibration", "Calibrationist Research Flights"),
            ("helicopter", "Helicopterium Air"),
        ]
        for interest_type, owner in false_positive_cases:
            with self.subTest(interest_type=interest_type):
                self.assertIsNone(
                    logic.classify_special_interest(
                        {"hex": "abc123", "flight": "ABC123", "seen": 1.0},
                        {
                            "registered_owner": owner,
                            "aircraft_model": owner,
                            "service_type": "unknown",
                        },
                    )
                )

        positive_cases = [
            ("medevac", "medical rescue"),
            ("police", "state police"),
            ("calibration", "flight check calibration"),
            ("helicopter_no_callsign", "Airbus Helicopters"),
        ]
        for interest_type, owner in positive_cases:
            with self.subTest(interest_type=interest_type):
                aircraft = {"hex": "abc123", "flight": "", "seen": 1.0}
                candidate = logic.classify_special_interest(
                    aircraft,
                    {
                        "registered_owner": owner,
                        "aircraft_model": owner,
                        "service_type": "unknown",
                    },
                )
                assert candidate is not None
                self.assertEqual(candidate[0], interest_type)

    def test_hawker_icao_type_is_not_helicopter_interest(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "4bcd05",
                "flight": "",
                "seen": 1.0,
                "category": "A0",
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "registered_owner": "Bonair Havacilik",
                "aircraft_model": "125 850XP",
                "aircraft_type": "H25B",
                "aircraft_model_speech": "Хокер восемьсот пятьдесят икс пи",
                "service_type": "unknown",
            },
        )

        self.assertIsNone(candidate)
        self.assertFalse(
            logic.is_helicopter(
                {"category": "A0"},
                {"aircraft_model": "125 850XP", "aircraft_type": "H25B"},
            )
        )
        self.assertEqual(
            logic.spoken_model("125 850XP", "H25B"),
            "Хокер восемьсот пятьдесят икс пи",
        )

    def test_helicopter_without_coordinates_omits_hex_from_announcement(self) -> None:
        candidate = logic.interest_candidate(
            {
                "hex": "abc123",
                "flight": "",
                "seen": 1.0,
                "category": "A7",
            },
            source="test",
            aircraft_count=1,
            enrichment={
                "registered_owner": "Example Heli Ops",
                "aircraft_model": "Airbus H135",
                "aircraft_type": "H135",
                "aircraft_model_speech": "Эйрбас H135",
                "service_type": "unknown",
            },
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "special_interest")
        self.assertEqual(candidate.interest_type, "helicopter_no_callsign")
        self.assertIn("Вертолёт без координат и без позывного", candidate.announcement)
        self.assertNotIn("вертолёт без позывного,", candidate.announcement.lower())
        self.assertNotIn("abc123", candidate.announcement.lower())
        self.assertNotIn("unknown", candidate.announcement.lower())

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
                "origin_iata": "LCA",
                "origin_name": "Larnaca (LCA)",
                "origin_speech": "Ларнаки",
                "destination_iata": "KUT",
                "destination_name": "Kopitnari (KUT)",
                "destination_speech": "Кутаиси",
                "spoken_flight": "один два три",
            },
        )

        assert candidate is not None
        self.assertEqual(candidate.phase, "kutaisi_route")
        self.assertIn("рейс на Кутаиси", candidate.announcement)
        self.assertIn("Ларнака - Кутаиси", candidate.announcement)
        self.assertNotIn("Ларнаки - Кутаиси", candidate.announcement)
        self.assertFalse(candidate.unusual_aircraft)

    def test_speech_helpers(self) -> None:
        self.assertEqual(logic.spoken_flight("RWZ553", airline_icao="RWZ"), "пять пять три")
        self.assertEqual(
            logic.spoken_flight("VAA020", airline_icao="VAA"),
            "ноль два ноль",
        )
        self.assertEqual(
            logic.spoken_flight("PGT48DK", airline_icao="PGT"),
            "четыре восемь ди кей",
        )
        self.assertEqual(
            logic.spoken_flight("TCSHE"),
            "ти си эс эйч и",
        )
        self.assertEqual(logic.spoken_flight("SPAR89"), "Спар восемь девять")
        self.assertTrue(logic.has_callsign_prefix_speech_mapping("SPAR89"))
        self.assertFalse(logic.has_callsign_prefix_speech_mapping("ABCD89"))
        cyrillic = logic.tts_cyrillic_text(
            "Кутаиси - Wrocław, Gökçen, Arnavutköy, Istanbul."
        )
        self.assertIn("Кутаиси - Вроклав", cyrillic)
        self.assert_tts_has_no_latin(cyrillic)
        self.assertEqual(
            logic.known_airline_for_callsign("VAA020"),
            ("Van Air Europe", "VAA"),
        )
        self.assertEqual(
            logic.known_airline_for_callsign("JZR615"),
            ("Jazeera Airways", "JZR"),
        )
        self.assertEqual(
            logic.known_airline_for_callsign("4L112"),
            ("OneClick Airways", "4L"),
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
            logic.known_route_for_callsign("VAA021")["route_source"],
            "vanilla_sky_schedule",
        )
        self.assertEqual(
            logic.known_route_for_callsign("VAA021")["scheduled_departure_local"],
            "14:00",
        )
        self.assertEqual(logic.airline_speech("Aeroflot Russian Airlines"), "Аэрофлот")
        self.assertEqual(logic.airline_speech("Rossiya - Russian Airlines"), "Россия")
        self.assertEqual(logic.airline_speech("Belavia Belarusian Airlines"), "Белавиа")
        self.assertEqual(logic.airline_speech("KLM Royal Dutch Airlines"), "Кей-Эл-Эм")
        self.assertEqual(logic.airline_speech("S7 Airlines (Siberia Airlines)"), "Эс-семь")
        self.assertEqual(logic.airline_speech("RED WINGS AIRLINES"), "Ред Вингс")
        self.assertEqual(logic.airline_speech("GEORGIAN AIRWAYS"), "Джорджиан Эйрвейз")
        self.assertEqual(logic.airline_speech("SCAT AIR COMPANY"), "Скат")
        self.assertEqual(logic.airline_speech("Jordanian Aviation"), "Джорданиан Авиейшен")
        self.assertEqual(logic.airline_speech("Genel Havacilik"), "Генел Хаваджылык")
        self.assertEqual(logic.airline_speech("Silk Way Airlines"), "Силк Вей")
        self.assertEqual(logic.airline_speech("JAZEERA AİRWAYS"), "Джазира")
        self.assertEqual(
            logic.airline_speech("Atlantis European Airways"),
            "Атлантис Европиан Эйрвейз",
        )
        self.assertEqual(logic.airline_speech("Austrian Airlines"), "Австрийские авиалинии")
        self.assertEqual(logic.airline_speech("Virgin Atlantic Airways"), "Вёрджин Атлантик")
        self.assertEqual(logic.airline_speech("South West Air Corporation"), "Саутвест Эйр")
        self.assertEqual(logic.airline_speech("Air Cairo"), "Эйр Каиро")
        self.assertEqual(logic.airline_speech("China Southern Airlines"), "Чайна Саузерн")
        self.assertEqual(logic.airline_speech("Swiss International Air Lines"), "Свисс")
        self.assertEqual(logic.airline_speech("Cathay Pacific"), "Катай Пасифик")
        self.assertEqual(
            logic.airline_speech("Scandinavian Airlines System"),
            "Скандинавские авиалинии",
        )
        self.assertEqual(logic.airline_speech("Asiana Airlines"), "Азиана")
        self.assertEqual(logic.airline_speech("Korean Air"), "Кореан Эйр")
        self.assertEqual(logic.airline_speech("Oneclick"), "УанКлик")
        self.assertEqual(logic.airline_speech("OneClick Airways"), "УанКлик")
        self.assertTrue(logic.has_airline_speech_mapping("JAZEERA AİRWAYS"))
        self.assertEqual(logic.airline_speech("Carpatair"), "Карпатэйр")
        self.assertEqual(
            logic.airline_speech("Turkmenistan Airlines"),
            "Туркменистанские авиалинии",
        )
        self.assertEqual(logic.airline_speech("Tarkim Havacilik"), "Тарким Хаваджылык")
        self.assertEqual(logic.airline_speech("Iraqi Airways"), "Иракские авиалинии")
        self.assertEqual(
            logic.airline_speech("Speedwings Executive Jet Gmbh"),
            "Спидвингс Экзекьютив Джет",
        )
        self.assertEqual(
            logic.military_operator_speech({"registered_owner": "Romanian Air Force"}),
            "ВВС Румынии",
        )
        self.assertEqual(
            logic.military_operator_speech({"registered_owner": "Turkish Air Force"}),
            "ВВС Турции",
        )

    def test_georgian_airways_followup_does_not_spell_airline_letters(self) -> None:
        previous = logic.AircraftCandidate(
            state="no_position_nearby:51403f:TGZ506",
            phase="no_position_nearby",
            hex="51403f",
            flight="TGZ506",
            spoken_flight="пять ноль шесть",
            event_key="no_position_nearby:51403f:TGZ506",
        )
        current = logic.AircraftCandidate(
            state="no_position_nearby:51403f:TGZ506",
            phase="no_position_nearby",
            hex="51403f",
            flight="TGZ506",
            spoken_flight="пять ноль шесть",
            airline_name="GEORGIAN AIRWAYS",
            origin_iata="BUS",
            origin_name="Batumi",
            origin_speech="Батуми",
            destination_iata="TBS",
            destination_name="Tbilisi",
            destination_speech="Тбилиси",
            event_key="no_position_nearby:51403f:TGZ506",
        )

        announcement = logic.build_followup_announcement(previous, current)

        self.assertIn("Джорджиан Эйрвейз", announcement)
        self.assertNotIn("джи и оу", announcement)
        self.assert_tts_has_no_latin(announcement)

    def test_oneclick_numeric_prefix_special_interest_avoids_letter_soup(self) -> None:
        text = logic.build_announcement(
            {"hex": "5140de", "flight": "4L112"},
            "special_interest",
            0.74,
            {
                "airline_name": "OneClick Airways",
                "aircraft_model_speech": logic.spoken_model("737", "B738"),
                "spoken_flight": logic.spoken_flight("4L112", airline_icao="4L"),
                "interest_type": "rapid_descent",
                "interest_label": "резкое снижение",
                "service_type": "unknown",
            },
        )

        self.assertIn(
            "Интересный самолёт в зоне видимости: УанКлик один один два.",
            text,
        )
        self.assertIn("резкое снижение", text)
        self.assertNotIn("четыре эл", text)
        self.assert_tts_has_no_latin(text)

    def test_known_airline_names_do_not_spell_company_words(self) -> None:
        scat = logic.build_announcement(
            {"hex": "abc123", "flight": "SCT123"},
            "positioned_approach",
            0.58,
            {
                "airline_name": "SCAT AIR COMPANY",
                "origin_speech": "Астаны",
                "aircraft_model_speech": "Боинг семьсот тридцать семь",
                "spoken_flight": "один два три",
            },
        )
        jordanian = logic.build_announcement(
            {"hex": "abc124", "flight": "JAV123"},
            "positioned_approach",
            0.58,
            {
                "airline_name": "Jordanian Aviation",
                "origin_speech": "Аммана",
                "aircraft_model_speech": "Боинг семьсот тридцать семь",
                "spoken_flight": "один два три",
            },
        )

        self.assertIn("Скат", scat)
        self.assertIn("Джорданиан Авиейшен", jordanian)
        self.assertNotIn("эс си эй ти", scat)
        self.assertNotIn("эй ви ай", jordanian)
        self.assert_tts_has_no_latin(scat)
        self.assert_tts_has_no_latin(jordanian)

    def test_unhelpful_registration_like_flight_label_is_not_spoken(self) -> None:
        business = logic.build_announcement(
            {"hex": "4b1818", "flight": "TCNYK"},
            "positioned_approach",
            0.58,
            {
                "airline_name": "Genel Havacilik",
                "service_type": "business_jet",
                "service_type_confidence": 0.9,
                "aircraft_model_speech": "Хокер восемьсот пятьдесят икс пи",
                "spoken_flight": logic.spoken_flight("TCNYK"),
            },
        )
        hex_like = logic.build_announcement(
            {"hex": "4caebb", "flight": "4CAEBB"},
            "positioned_takeoff",
            0.92,
            {
                "airline_name": "FlyArystan",
                "aircraft_model_speech": "Аэробус триста двадцать",
                "spoken_flight": logic.spoken_flight("4CAEBB"),
            },
        )
        military = logic.build_announcement(
            {"hex": "ae146a", "flight": "PAID16"},
            "military_visible",
            0.9,
            {
                "registered_owner": "United States Air Force",
                "aircraft_model": "C-146A",
                "aircraft_model_speech": logic.spoken_model("C-146A", "C146"),
                "spoken_flight": logic.spoken_flight("PAID16"),
            },
        )

        self.assertIn("Генел Хаваджылык", business)
        self.assertNotIn("ти си эн уай кей", business)
        self.assertIn("Флай Арыстан", hex_like)
        self.assertNotIn("четыре си эй", hex_like)
        self.assertIn("ВВС США", military)
        self.assertNotIn("пи эй ай ди", military)
        self.assertIn("Си-сто сорок шесть", military)
        self.assert_tts_has_no_latin(business)
        self.assert_tts_has_no_latin(hex_like)
        self.assert_tts_has_no_latin(military)
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "ATH",
                    "municipality": "Athens",
                    "name": "Athens International Airport",
                },
                direction="from",
            ),
            "Афин",
        )
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "ATH",
                    "municipality": "Athens",
                    "name": "Athens International Airport",
                },
                direction="to",
            ),
            "Афины",
        )
        self.assertEqual(
            logic.airport_route_speech(
                {
                    "iata_code": "ATH",
                    "municipality": "Athens",
                    "name": "Athens International Airport",
                },
            ),
            "Афины",
        )
        self.assertEqual(
            logic.airport_speech(
                {"iata_code": "KTW", "municipality": "Katowice", "name": "Katowice"},
                direction="to",
            ),
            "Катовице",
        )
        self.assertEqual(
            logic.airport_speech(
                {"iata_code": "SKX", "municipality": "Saransk", "name": "Saransk"},
                direction="from",
            ),
            "Саранска",
        )
        self.assertEqual(
            logic.airport_route_speech(
                {"iata_code": "BJV", "municipality": "Bodrum", "name": "Bodrum"}
            ),
            "Бодрум",
        )
        self.assertEqual(
            logic.airport_route_speech(
                {"iata_code": "ASB", "municipality": "Ashgabat", "name": "Ashgabat"}
            ),
            "Ашхабад",
        )
        self.assertEqual(
            logic.airport_route_speech(
                {"iata_code": "BRQ", "municipality": "Brno", "name": "Brno"}
            ),
            "Брно",
        )
        self.assertEqual(
            logic.airport_speech(
                {"iata_code": "KWI", "municipality": "Kuwait", "name": "Kuwait"},
                direction="from",
            ),
            "Кувейта",
        )
        self.assertEqual(
            logic.airport_route_speech(
                {"iata_code": "KWI", "municipality": "Kuwait", "name": "Kuwait"}
            ),
            "Кувейт",
        )
        live_gap_airports = [
            ("PVG", "Shanghai (Pudong)", "Шанхая, Пудун", "Шанхай, Пудун", "Шанхай, Пудун"),
            ("ULN", "Ulaanbaatar", "Улан-Батора", "Улан-Батор", "Улан-Батор"),
            (
                "CDG",
                "Paris",
                "Парижа, Шарль-де-Голль",
                "Париж, Шарль-де-Голль",
                "Париж, Шарль-де-Голль",
            ),
            (
                "MRV",
                "Mineralnyye Vody",
                "Минеральных Вод",
                "Минеральные Воды",
                "Минеральные Воды",
            ),
            ("UFA", "Ufa", "Уфы", "Уфу", "Уфа"),
            ("ICN", "Seoul", "Сеула", "Сеул", "Сеул"),
            ("CPH", "Copenhagen", "Копенгагена", "Копенгаген", "Копенгаген"),
            ("TIA", "Tirana", "Тираны", "Тирану", "Тирана"),
            ("EIN", "Eindhoven", "Эйндховена", "Эйндховен", "Эйндховен"),
            ("STR", "Stuttgart", "Штутгарта", "Штутгарт", "Штутгарт"),
            ("SCO", "Aktau", "Актау", "Актау", "Актау"),
            ("SGN", "Ho Chi Minh City", "Хошимина", "Хошимин", "Хошимин"),
            ("MUC", "Munich", "Мюнхена", "Мюнхен", "Мюнхен"),
            ("CGK", "Jakarta", "Джакарты", "Джакарту", "Джакарта"),
            ("BEY", "Beirut", "Бейрута", "Бейрут", "Бейрут"),
            ("PKX", "Beijing", "Пекина, Дасин", "Пекин, Дасин", "Пекин, Дасин"),
            ("ZRH", "Zurich", "Цюриха", "Цюрих", "Цюрих"),
            ("HKG", "Kowloon City, Kowloon", "Гонконга", "Гонконг", "Гонконг"),
            ("MAN", "Manchester", "Манчестера", "Манчестер", "Манчестер"),
            ("CAN", "Guangzhou", "Гуанчжоу", "Гуанчжоу", "Гуанчжоу"),
            ("GNY", "Şanlıurfa", "Шанлыурфы", "Шанлыурфу", "Шанлыурфа"),
            ("OSL", "Oslo", "Осло", "Осло", "Осло"),
            ("TIV", "Tivat", "Тивата", "Тиват", "Тиват"),
            ("VOG", "Volgograd", "Волгограда", "Волгоград", "Волгоград"),
            ("OGU", "Ordu", "Орду", "Орду", "Орду"),
            ("LHE", "Lahore", "Лахора", "Лахор", "Лахор"),
            ("ISB", "Islamabad", "Исламабада", "Исламабад", "Исламабад"),
            ("KEJ", "Kemerovo", "Кемерова", "Кемерово", "Кемерово"),
            ("LHR", "London", "Лондона, Хитроу", "Лондон, Хитроу", "Лондон, Хитроу"),
            ("CIT", "Shymkent", "Шымкента", "Шымкент", "Шымкент"),
            ("VIE", "Vienna", "Вены", "Вену", "Вена"),
        ]
        for code, city, from_speech, to_speech, route_speech in live_gap_airports:
            with self.subTest(code=code):
                airport = {"iata_code": code, "municipality": city, "name": city}
                self.assertEqual(logic.airport_speech(airport, direction="from"), from_speech)
                self.assertEqual(logic.airport_speech(airport, direction="to"), to_speech)
                self.assertEqual(logic.airport_route_speech(airport), route_speech)
        chisinau_airport = {
            "iata_code": "KIV",
            "municipality": "Chisinau",
            "name": "Chișinău International Airport",
        }
        self.assertEqual(
            logic.airport_speech(chisinau_airport, direction="from"),
            "Кишинёва",
        )
        self.assertEqual(
            logic.airport_speech(chisinau_airport, direction="to"),
            "Кишинёв",
        )
        self.assertEqual(logic.airport_route_speech(chisinau_airport), "Кишинёв")
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "KIV",
                    "origin_name": "Chisinau (KIV)",
                    "destination_iata": "BUS",
                    "destination_name": "Batumi (BUS)",
                }
            ),
            "Кишинёв - Батуми",
        )
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "",
                    "origin_name": "Chișinău (KIV)",
                    "destination_iata": "BUS",
                    "destination_name": "Batumi (BUS)",
                }
            ),
            "Кишинёв - Батуми",
        )
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "",
                    "origin_name": "Chişinău (KIV)",
                    "destination_iata": "BUS",
                    "destination_name": "Batumi (BUS)",
                }
            ),
            "Кишинёв - Батуми",
        )
        self.assertTrue(
            logic.has_airport_speech_mapping(
                {
                    "iata_code": "ATH",
                    "municipality": "Athens",
                    "name": "Athens International Airport",
                },
                direction="from",
            )
        )
        self.assertFalse(
            logic.has_airport_speech_mapping(
                {
                    "iata_code": "XYZ",
                    "municipality": "New Place",
                    "name": "New Place International Airport",
                },
                direction="to",
            )
        )
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "SAW",
                    "municipality": "Pendik, Istanbul",
                    "name": "Istanbul Sabiha Gökçen International Airport",
                },
                direction="from",
            ),
            "Стамбула, Сабиха Гёкчен",
        )
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "LCA",
                    "origin_name": "Larnaca (LCA)",
                    "origin_speech": "Ларнаки",
                    "destination_iata": "KUT",
                    "destination_name": "Kopitnari (KUT)",
                    "destination_speech": "Кутаиси",
                }
            ),
            "Ларнака - Кутаиси",
        )
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "SVO",
                    "origin_name": "Moscow (SVO)",
                    "destination_iata": "",
                    "destination_name": "Sharm El Sheikh",
                }
            ),
            "Москва, Шереметьево - Шарм-эш-Шейх",
        )
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "",
                    "origin_name": "Sok Son, Hanoi",
                    "destination_iata": "IST",
                    "destination_name": "Istanbul (IST)",
                }
            ),
            "Ханой - Стамбул",
        )
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "WRO",
                    "origin_name": "Wrocław",
                    "destination_iata": "KUT",
                    "destination_name": "Kopitnari (KUT)",
                }
            ),
            "Вроцлав - Кутаиси",
        )
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "KUT",
                    "origin_name": "Kopitnari (KUT)",
                    "destination_iata": "FCO",
                    "destination_name": "Rome",
                }
            ),
            "Кутаиси - Рим",
        )
        self.assertEqual(
            logic.route_pair_speech(
                {
                    "origin_iata": "SVX",
                    "origin_name": "Yekaterinburg",
                    "destination_iata": "BUS",
                    "destination_name": "Batumi (BUS)",
                }
            ),
            "Екатеринбург - Батуми",
        )
        self.assertEqual(
            logic.airport_speech({"municipality": "Moscow Zhukovsky"}, direction="to"),
            "подмосковный Жуковский",
        )
        self.assertEqual(
            logic.airport_speech({"municipality": "Moscow-Zhukovsky"}, direction="from"),
            "подмосковного Жуковского",
        )
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "ZIA",
                    "municipality": "Moscow Zhukovsky",
                    "name": "Zhukovsky International Airport",
                },
                direction="from",
            ),
            "подмосковного Жуковского",
        )
        self.assertEqual(
            logic.airport_route_speech(
                {
                    "iata_code": "ZIA",
                    "municipality": "Moscow Zhukovsky",
                    "name": "Zhukovsky International Airport",
                },
            ),
            "подмосковный Жуковский",
        )
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "VKO",
                    "municipality": "Moscow",
                    "name": "Vnukovo International Airport",
                },
                direction="from",
            ),
            "Москвы, Внуково",
        )
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "VKO",
                    "municipality": "Moscow",
                    "name": "Vnukovo International Airport",
                },
                direction="to",
            ),
            "Москву, Внуково",
        )
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "EVN",
                    "municipality": "Yerevan",
                    "name": "Zvartnots International Airport",
                },
                direction="to",
            ),
            "Ереван, Звартноц",
        )
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "TLV",
                    "municipality": "Tel Aviv",
                    "name": "Ben Gurion International Airport",
                },
                direction="from",
            ),
            "Бен Гуриона",
        )
        self.assertEqual(
            logic.airport_speech(
                {
                    "iata_code": "TLV",
                    "municipality": "Tel Aviv",
                    "name": "Ben Gurion International Airport",
                },
                direction="to",
            ),
            "Бен Гурион",
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
            logic.spoken_model("A350 1041 A35K", "A35K"),
            "Аэробус триста пятьдесят",
        )
        self.assertEqual(
            logic.spoken_model("BOEING 737-800", "B738"),
            "Боинг семьсот тридцать семь",
        )
        self.assertEqual(
            logic.spoken_model("BOEING 777-200LR", "B77L"),
            "Боинг семьсот семьдесят семь",
        )
        self.assertEqual(
            logic.spoken_model("C-12C Huron", "C12C"),
            "Си-двенадцать Хьюрон",
        )
        self.assertEqual(logic.spoken_model("PA-46-500TP M500", ""), "Пайпер M500")
        self.assertEqual(logic.spoken_model("1125 Astra SPX", ""), "Астра эс-пи-икс")
        self.assertEqual(
            logic.spoken_model("Falcon 2000EX EASy", "F2TH"),
            "Дассо Фалькон две тысячи",
        )
        self.assertEqual(
            logic.spoken_model("Boeing 787-10", "B78X"),
            "Боинг семьсот восемьдесят семь",
        )
        self.assertEqual(logic.spoken_model("AEROPRO Eurofox", ""), "Еврофокс")
        self.assertEqual(logic.spoken_model("IL-76TD", "IL76"), "Ил-семьдесят шесть")
        self.assertEqual(
            logic.spoken_model("Boeing 737 MAX 8", "B38M"),
            "Боинг семьсот тридцать семь Макс восемь",
        )
        self.assertEqual(
            logic.spoken_model("Challenger 605", "CL65"),
            "Бомбардье Челленджер шестьсот пятый",
        )
        self.assertEqual(
            logic.spoken_model("Gulfstream G650", "GLF6"),
            "Гольфстрим Джи-шестьсот пятьдесят",
        )
        self.assertEqual(
            logic.extract_airport_data_year("<b>Year built:</b></td><td>2012</td>"),
            2012,
        )
        self.assertEqual(
            logic.extract_airport_data_year(
                "Year built</td>\n                            <td>2021"
            ),
            2021,
        )
        self.assertEqual(
            logic.extract_airport_data_year(
                "<title>Aircraft Data TC-NCU, 2021 Airbus A320-251N</title>"
            ),
            2021,
        )
        self.assertEqual(logic.KNOWN_BUILT_YEAR_BY_REGISTRATION["EP-VAI"], 1997)
        self.assertEqual(
            logic.spoken_year(logic.KNOWN_BUILT_YEAR_BY_REGISTRATION["EP-VAI"]),
            "тысяча девятьсот девяносто седьмого года",
        )
        self.assertEqual(logic.spoken_year(1990), "тысяча девятьсот девяностого года")


if __name__ == "__main__":
    unittest.main()
