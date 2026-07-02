"""Tests for coordinator helpers that do not need a running Home Assistant."""

from __future__ import annotations

import sys
import types
import unittest
from dataclasses import replace
from datetime import datetime
from importlib import util
from pathlib import Path
from typing import Any
from unittest.mock import patch

COMPONENT_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "aircraft_window"


def _stub_homeassistant_modules() -> None:
    """Install tiny Home Assistant stubs for importing the coordinator module."""
    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    storage = types.ModuleType("homeassistant.helpers.storage")
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class ConfigEntry:
        pass

    class HomeAssistant:
        pass

    class Store:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, _item: object) -> type[DataUpdateCoordinator]:
            return cls

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

    def async_get_clientsession(_hass: HomeAssistant) -> None:
        return None

    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    aiohttp_client.async_get_clientsession = async_get_clientsession
    storage.Store = Store
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.config_entries", config_entries)
    sys.modules.setdefault("homeassistant.core", core)
    sys.modules.setdefault("homeassistant.helpers", helpers)
    sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aiohttp_client)
    sys.modules.setdefault("homeassistant.helpers.storage", storage)
    sys.modules.setdefault("homeassistant.helpers.update_coordinator", update_coordinator)


def _load_component_module(name: str) -> types.ModuleType:
    """Load an aircraft_window module under a package name for relative imports."""
    package = sys.modules.get("aircraft_window")
    if package is None:
        package = types.ModuleType("aircraft_window")
        package.__path__ = [str(COMPONENT_ROOT)]  # type: ignore[attr-defined]
        sys.modules["aircraft_window"] = package

    spec = util.spec_from_file_location(
        f"aircraft_window.{name}",
        COMPONENT_ROOT / f"{name}.py",
    )
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_stub_homeassistant_modules()
_load_component_module("const")
settings = _load_component_module("settings")
_load_component_module("logic")
coordinator = _load_component_module("coordinator")


class PrefetchSelectionTest(unittest.TestCase):
    """Verify background enrichment warms useful receiver rows first."""

    def test_prefetch_limit_zero_selects_all_airborne_rows(self) -> None:
        rows = [
            {"hex": "aaaaaa", "flight": "AAA123", "alt_baro": 32000, "seen": 1},
            {"hex": "bbbbbb", "flight": "BBB123", "alt_baro": "ground", "seen": 1},
            {"hex": "", "flight": "CCC123", "alt_baro": 7000, "seen": 1},
            {"hex": "dddddd", "flight": "", "alt_baro": 7000, "seen": 1},
        ]

        selected = coordinator._select_prefetch_rows(rows, 0)

        self.assertEqual([row["hex"] for row in selected], ["aaaaaa", "dddddd"])

    def test_prefetch_limited_rows_are_prioritized_not_first_n(self) -> None:
        rows = [
            {"hex": "111111", "flight": "", "alt_baro": 39000, "seen": 40, "messages": 1},
            {
                "hex": "222222",
                "flight": "PGT48DK",
                "alt_baro": 5200,
                "lat": 41.6,
                "lon": 41.4,
                "seen": 0.2,
                "seen_pos": 0.5,
                "messages": 900,
                "rssi": -8,
            },
            {"hex": "333333", "flight": "AFL2147", "alt_baro": 33000, "seen": 0.5},
        ]

        selected = coordinator._select_prefetch_rows(rows, 1)

        self.assertEqual(selected[0]["hex"], "222222")


class CachePruneTest(unittest.TestCase):
    """Verify persistent cache TTLs also clean old entries from disk."""

    def test_prune_expired_known_cache_entries(self) -> None:
        now = 10_000_000
        cache: dict[str, Any] = {
            "batumi-airport-board:01.01.2026:departure": {
                "fetched_at": now - coordinator.AIRPORT_BOARD_CACHE_SECONDS - 1,
                "payload": {},
            },
            "callsign:PGT48DK": {
                "fetched_at": now - coordinator.ROUTE_CACHE_SECONDS + 1,
                "payload": {"ok": True},
            },
            "aircraft:4BB875": {
                "fetched_at": now - coordinator.AIRCRAFT_CACHE_SECONDS - 1,
                "payload": {"ok": True},
            },
            "airport-data-year:TC-NCU": {
                "fetched_at": now - coordinator.BUILT_YEAR_CACHE_SECONDS + 1,
                "year": 2021,
            },
            coordinator.MAPPING_REVIEW_CACHE_KEY: [{"key": "keep"}],
            "unknown-old-shape": {"fetched_at": 1, "payload": {"keep": True}},
        }

        pruned = coordinator._prune_expired_cache_entries(cache, now=now)

        self.assertEqual(pruned, 2)
        self.assertNotIn("batumi-airport-board:01.01.2026:departure", cache)
        self.assertNotIn("aircraft:4BB875", cache)
        self.assertIn("callsign:PGT48DK", cache)
        self.assertIn("airport-data-year:TC-NCU", cache)
        self.assertIn(coordinator.MAPPING_REVIEW_CACHE_KEY, cache)
        self.assertIn("unknown-old-shape", cache)

    def test_prune_error_entries_with_short_ttl(self) -> None:
        now = 10_000_000
        cache: dict[str, Any] = {
            "callsign:PGT48DK": {
                "fetched_at": now - coordinator.EXTERNAL_LOOKUP_ERROR_CACHE_SECONDS - 1,
                "payload": {},
                "error": True,
            },
            "callsign:VRH6823": {
                "fetched_at": now - coordinator.EXTERNAL_LOOKUP_ERROR_CACHE_SECONDS + 1,
                "payload": {},
                "error": True,
            },
        }

        pruned = coordinator._prune_expired_cache_entries(cache, now=now)

        self.assertEqual(pruned, 1)
        self.assertNotIn("callsign:PGT48DK", cache)
        self.assertIn("callsign:VRH6823", cache)


class BatumiAirportBoardTest(unittest.IsolatedAsyncioTestCase):
    """Verify Batumi Airport board matching and aggregation."""

    def test_airport_board_match_does_not_fallback_to_opposite_leg(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        board = {
            "data": {
                "flights": [
                    {
                        "airlineIata": "WZ",
                        "airlineIcao": "WZ",
                        "flightNumber": "550",
                        "flightLeg": "DEPARTURE",
                    }
                ]
            }
        }

        self.assertEqual(
            fake._airport_board_match(
                board,
                "RWZ550",
                preferred_leg="ARRIVAL",
            ),
            {},
        )

    def test_emergency_squawk_requires_repeated_fresh_observation(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._emergency_squawk_observations = {}
        row = {"hex": "151ff4", "squawk": "7700", "messages": 381}

        self.assertFalse(fake._emergency_squawk_confirmed(row))
        self.assertFalse(fake._emergency_squawk_confirmed(row))
        self.assertTrue(
            fake._emergency_squawk_confirmed({**row, "messages": 382})
        )

    async def test_emergency_squawk_single_decoded_impulse_does_not_become_candidate(
        self,
    ) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._emergency_squawk_observations = {}
        aircraft_rows = [
            {
                "hex": "151ff4",
                "flight": "AFL2145",
                "squawk": "7700",
                "alt_baro": 35000,
                "seen": 0.1,
                "messages": 381,
            }
        ]

        with patch.object(fake, "_async_enrich_aircraft", return_value={}):
            candidate = await fake._async_pick_interest_candidate(
                aircraft_rows,
                source="test",
                enable_enrichment=True,
            )

        self.assertIsNone(candidate)

    def test_airport_board_route_rejects_wrong_local_direction(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        attrs = {
            "airline_name": "",
            "origin_iata": "",
            "origin_name": "",
            "origin_speech": "",
            "destination_iata": "",
            "destination_name": "",
            "destination_speech": "",
            "route_summary": "",
            "route_source": "",
            "scheduled_departure_local": "",
            "airport_board_remark": "",
            "airport_board_estimated_local": "",
            "enrichment_source": "",
        }
        malformed_arrival = {
            "airlineName": "RED WINGS AIRLINES",
            "flightLeg": "ARRIVAL",
            "stad": "31.05.2026 21:05",
            "etad": "31.05.2026 21:05",
            "remark": {"remarkEn": ""},
            "path": {
                "origin": {
                    "originIata": "ZIA",
                    "originEn": "MOSCOW-ZHUKOVSKY",
                },
                "destination": {
                    "destinationIata": "ZIA",
                    "destinationEn": "MOSCOW-ZHUKOVSKY",
                },
            },
        }

        fake._apply_airport_board_route(
            attrs,
            malformed_arrival,
            phase="positioned_approach",
        )

        self.assertEqual(attrs["route_source"], "")
        self.assertEqual(attrs["origin_iata"], "")
        self.assertEqual(attrs["destination_iata"], "")

    def test_route_direction_uses_configured_local_airport(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._runtime_settings = replace(
            settings.DEFAULT_RUNTIME_SETTINGS,
            local_airport=replace(
                settings.DEFAULT_RUNTIME_SETTINGS.local_airport,
                iata="ABC",
            ),
        )

        self.assertTrue(
            fake._route_matches_local_phase(
                "positioned_landing",
                "TST",
                "ABC",
            )
        )
        self.assertFalse(
            fake._route_matches_local_phase(
                "positioned_landing",
                "TST",
                "BUS",
            )
        )
        self.assertTrue(
            fake._route_matches_local_phase(
                "positioned_takeoff",
                "ABC",
                "TST",
            )
        )

    def test_airport_board_route_applies_valid_local_arrival(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        attrs = {
            "airline_name": "",
            "origin_iata": "",
            "origin_name": "",
            "origin_speech": "",
            "destination_iata": "",
            "destination_name": "",
            "destination_speech": "",
            "route_summary": "",
            "route_source": "",
            "scheduled_departure_local": "",
            "airport_board_remark": "",
            "airport_board_estimated_local": "",
            "enrichment_source": "",
        }
        arrival = {
            "airlineName": "RED WINGS AIRLINES",
            "flightLeg": "ARRIVAL",
            "stad": "31.05.2026 21:05",
            "etad": "31.05.2026 21:05",
            "remark": {"remarkEn": ""},
            "path": {
                "origin": {
                    "originIata": "ZIA",
                    "originEn": "MOSCOW-ZHUKOVSKY",
                },
                "destination": {
                    "destinationIata": "BUS",
                    "destinationEn": "BATUMI",
                },
            },
        }

        fake._apply_airport_board_route(
            attrs,
            arrival,
            phase="positioned_approach",
        )

        self.assertEqual(attrs["route_source"], "batumi_airport_board")
        self.assertEqual(attrs["route_summary"], "ZIA \u2192 BUS")
        self.assertEqual(attrs["origin_speech"], "подмосковного Жуковского")
        self.assertEqual(attrs["destination_speech"], "Батуми")

    def test_handle_candidate_event_suppresses_callsign_only_followup(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}

        previous = coordinator.AircraftCandidate(
            state="positioned_takeoff:738286:738286",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:738286:738286",
            hex="738286",
            flight="738286",
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year_speech="две тысячи шестнадцатого года",
            announcement="Вылетает самолёт 738286.",
        )
        current = coordinator.AircraftCandidate(
            state="positioned_takeoff:738286:ISR890",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:738286:ISR890",
            hex="738286",
            flight="ISR890",
            airline_name="Israir",
            spoken_flight="восемь девять ноль",
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year_speech="две тысячи шестнадцатого года",
            announcement="Вылетает рейс Исра Эйр восемь девять ноль.",
        )

        with patch.object(coordinator.time, "monotonic", return_value=100.0):
            self.assertFalse(fake._handle_candidate_event(previous))
        with patch.object(
            coordinator.time,
            "monotonic",
            return_value=100.0 + coordinator.ROUTINE_HEX_HOLD_SECONDS + 0.1,
        ):
            self.assertTrue(fake._handle_candidate_event(previous))
        self.assertFalse(fake._handle_candidate_event(current))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], coordinator.EVENT_CANDIDATE)
        self.assertEqual(fake._last_event_key, previous.event_key)
        airframe_key = coordinator.candidate_airframe_key(current)
        self.assertNotIn(current.event_key, fake._announced_event_keys_by_airframe[airframe_key])
        self.assertIs(fake._last_announced_by_airframe[airframe_key], previous)

    def test_handle_candidate_event_keeps_route_followup(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}

        previous = coordinator.AircraftCandidate(
            state="positioned_takeoff:738286:738286",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:738286:738286",
            hex="738286",
            flight="738286",
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year_speech="две тысячи шестнадцатого года",
            announcement="Вылетает самолёт 738286.",
        )
        current = coordinator.AircraftCandidate(
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
            built_year_speech="две тысячи шестнадцатого года",
            announcement="Вылетает рейс Исра Эйр восемь девять ноль.",
        )

        with patch.object(coordinator.time, "monotonic", return_value=100.0):
            self.assertFalse(fake._handle_candidate_event(previous))
        with patch.object(
            coordinator.time,
            "monotonic",
            return_value=100.0 + coordinator.ROUTINE_HEX_HOLD_SECONDS + 0.1,
        ):
            self.assertTrue(fake._handle_candidate_event(previous))
        self.assertTrue(fake._handle_candidate_event(current))

        self.assertEqual(len(events), 2)
        self.assertEqual(
            events[1][1]["announcement"],
            "Дополнение: это Исра Эйр, в Бен Гурион.",
        )
        self.assertEqual(events[1][1]["announcement_kind"], "followup")

    def test_handle_candidate_event_allows_late_route_after_suppressed_callsign(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}

        previous = coordinator.AircraftCandidate(
            state="positioned_takeoff:738286:738286",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:738286:738286",
            hex="738286",
            flight="738286",
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year_speech="две тысячи шестнадцатого года",
            announcement="Вылетает самолёт 738286.",
        )
        callsign_only = coordinator.AircraftCandidate(
            state="positioned_takeoff:738286:ISR890",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:738286:ISR890",
            hex="738286",
            flight="ISR890",
            airline_name="Israir",
            spoken_flight="восемь девять ноль",
            aircraft_model="Airbus A320",
            aircraft_model_speech="Аэробус триста двадцать",
            built_year_speech="две тысячи шестнадцатого года",
            announcement="Вылетает рейс Исра Эйр восемь девять ноль.",
        )
        with_route = coordinator.AircraftCandidate(
            **{
                **callsign_only.as_dict(),
                "destination_speech": "Бен Гурион",
            }
        )

        with patch.object(coordinator.time, "monotonic", return_value=100.0):
            self.assertFalse(fake._handle_candidate_event(previous))
        with patch.object(
            coordinator.time,
            "monotonic",
            return_value=100.0 + coordinator.ROUTINE_HEX_HOLD_SECONDS + 0.1,
        ):
            self.assertTrue(fake._handle_candidate_event(previous))
        self.assertFalse(fake._handle_candidate_event(callsign_only))
        self.assertTrue(fake._handle_candidate_event(with_route))

        self.assertEqual(len(events), 2)
        self.assertEqual(
            events[1][1]["announcement"],
            "Дополнение: это Исра Эйр, в Бен Гурион.",
        )
        self.assertEqual(events[1][1]["announcement_kind"], "followup")

    def test_handle_candidate_event_allows_late_details_for_same_event_key(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}

        previous = coordinator.AircraftCandidate(
            state="positioned_approach:155bf7:AZO7053",
            phase="positioned_approach",
            event_key="positioned_approach:155bf7:AZO7053",
            hex="155bf7",
            flight="AZO7053",
            spoken_flight="семь ноль пять три",
            announcement="Заходит на посадку самолёт семь ноль пять три.",
        )
        current = coordinator.AircraftCandidate(
            state="positioned_approach:155bf7:AZO7053",
            phase="positioned_approach",
            event_key="positioned_approach:155bf7:AZO7053",
            hex="155bf7",
            flight="AZO7053",
            airline_name="Azimuth Airlines",
            spoken_flight="семь ноль пять три",
            origin_speech="Москвы, Внуково",
            destination_speech="Батуми",
            aircraft_model_speech="Суперджет",
            announcement="Заходит на посадку пассажирский рейс Азимут. "
            "Из Москвы, Внуково, Суперджет.",
        )

        self.assertTrue(fake._handle_candidate_event(previous))
        self.assertTrue(fake._handle_candidate_event(current))
        self.assertFalse(fake._handle_candidate_event(current))

        self.assertEqual(len(events), 2)
        self.assertEqual(
            events[1][1]["announcement"],
            "Дополнение: это Азимут, из Москвы, Внуково, Суперджет.",
        )
        self.assertEqual(events[1][1]["announcement_kind"], "followup")

    def test_handle_candidate_event_announces_departure_after_same_airframe_arrival(
        self,
    ) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}

        arrival = coordinator.AircraftCandidate(
            state="positioned_landing:155c66:RWZ567",
            phase="positioned_landing",
            event_key="positioned_landing:155c66:RWZ567",
            hex="155c66",
            flight="RWZ567",
            airline_name="RED WINGS AIRLINES",
            origin_speech="Сочи",
            destination_speech="Батуми",
            announcement="Заходит на посадку пассажирский рейс Ред Вингс. Из Сочи.",
        )
        departure = coordinator.AircraftCandidate(
            state="positioned_takeoff:155c66:RWZ568",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:155c66:RWZ568",
            hex="155c66",
            flight="RWZ568",
            airline_name="RED WINGS AIRLINES",
            origin_speech="Батуми",
            destination_speech="Сочи",
            announcement="Вылетает пассажирский рейс Ред Вингс. В Сочи.",
        )

        self.assertTrue(fake._handle_candidate_event(arrival))
        self.assertTrue(fake._handle_candidate_event(departure))

        self.assertEqual(len(events), 2)
        self.assertEqual(events[1][1]["announcement"], departure.announcement)
        self.assertEqual(events[1][1]["announcement_kind"], "initial")

    def test_handle_candidate_event_holds_hex_only_routine_briefly(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}
        fake._held_routine_hex_candidates = {}

        hex_only = coordinator.AircraftCandidate(
            state="positioned_takeoff:155bf7:155bf7",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:155bf7:155bf7",
            hex="155bf7",
            flight="155bf7",
            registered_owner="Azimuth",
            aircraft_model_speech="Суперджет",
            announcement="Вылетает самолёт Азимут. Суперджет.",
        )

        with patch.object(coordinator.time, "monotonic", return_value=100.0):
            self.assertFalse(fake._handle_candidate_event(hex_only))
        with patch.object(
            coordinator.time,
            "monotonic",
            return_value=100.0 + coordinator.ROUTINE_HEX_HOLD_SECONDS + 0.1,
        ):
            self.assertTrue(fake._handle_candidate_event(hex_only))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][1]["announcement"], hex_only.announcement)

    def test_routine_hex_hold_suppresses_sensor_announcement_only(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._held_routine_hex_candidates = {}

        hex_only = coordinator.AircraftCandidate(
            state="positioned_takeoff:155bf7:155bf7",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:155bf7:155bf7",
            hex="155bf7",
            flight="155bf7",
            registered_owner="Azimuth",
            aircraft_model_speech="Суперджет",
            announcement="Вылетает самолёт Азимут. Суперджет.",
            window_visible=True,
            window_preopen_needed=True,
        )

        with patch.object(coordinator.time, "monotonic", return_value=100.0):
            held = fake._apply_routine_hex_announcement_hold(hex_only)

        self.assertEqual(held.state, hex_only.state)
        self.assertTrue(held.window_visible)
        self.assertTrue(held.window_preopen_needed)
        self.assertEqual(held.announcement, "")
        self.assertTrue(held.announcement_suppressed)
        self.assertEqual(
            held.announcement_suppression_reason,
            coordinator.ROUTINE_HEX_HOLD_SUPPRESSION_REASON,
        )

        callsign = coordinator.AircraftCandidate(
            state="positioned_takeoff:155bf7:AZO7054",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:155bf7:AZO7054",
            hex="155bf7",
            flight="AZO7054",
            airline_name="Azimuth Airlines",
            destination_speech="Москву, Внуково",
            aircraft_model_speech="Суперджет",
            announcement="Вылетает пассажирский рейс Азимут. "
            "В Москву, Внуково, Суперджет.",
        )

        with patch.object(coordinator.time, "monotonic", return_value=104.0):
            released = fake._apply_routine_hex_announcement_hold(callsign)

        self.assertIs(released, callsign)
        self.assertFalse(released.announcement_suppressed)
        self.assertEqual(fake._held_routine_hex_candidates, {})

    def test_handle_candidate_event_callsign_arrival_beats_hex_hold(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}
        fake._held_routine_hex_candidates = {}

        hex_only = coordinator.AircraftCandidate(
            state="positioned_takeoff:155bf7:155bf7",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:155bf7:155bf7",
            hex="155bf7",
            flight="155bf7",
            registered_owner="Azimuth",
            aircraft_model_speech="Суперджет",
            announcement="Вылетает самолёт Азимут. Суперджет.",
        )
        with_route = coordinator.AircraftCandidate(
            state="positioned_takeoff:155bf7:AZO7054",
            phase="positioned_takeoff",
            event_key="positioned_takeoff:155bf7:AZO7054",
            hex="155bf7",
            flight="AZO7054",
            airline_name="Azimuth Airlines",
            destination_speech="Москву, Внуково",
            aircraft_model_speech="Суперджет",
            announcement="Вылетает пассажирский рейс Азимут. "
            "В Москву, Внуково, Суперджет.",
        )

        with patch.object(coordinator.time, "monotonic", return_value=100.0):
            self.assertFalse(fake._handle_candidate_event(hex_only))
        with patch.object(coordinator.time, "monotonic", return_value=104.0):
            self.assertTrue(fake._handle_candidate_event(with_route))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][1]["announcement"], with_route.announcement)
        self.assertEqual(fake._held_routine_hex_candidates, {})

    def test_handle_candidate_event_keeps_private_numbered_flight_immediate(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}
        fake._held_routine_hex_candidates = {}

        private = coordinator.AircraftCandidate(
            state="positioned_approach:424242:001",
            phase="positioned_approach",
            event_key="positioned_approach:424242:001",
            hex="424242",
            flight="001",
            registered_owner="Example Jet Holdings",
            spoken_flight="ноль ноль один",
            aircraft_model_speech="Гольфстрим",
            announcement="Заходит на посадку самолёт Example Jet Holdings ноль ноль один. "
            "Гольфстрим.",
        )

        self.assertTrue(fake._handle_candidate_event(private))

        self.assertEqual(len(events), 1)
        self.assertIn("ноль ноль один", events[0][1]["announcement"])

    def test_handle_candidate_event_ignores_silent_no_position_chatter(self) -> None:
        events: list[tuple[str, dict[str, Any]]] = []

        class FakeBus:
            def async_fire(self, event_type: str, data: dict[str, Any]) -> None:
                events.append((event_type, data))

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.hass = types.SimpleNamespace(bus=FakeBus())
        fake._last_event_key = ""
        fake._announced_event_keys_by_airframe = {}
        fake._last_announced_by_airframe = {}

        silent = coordinator.AircraftCandidate(
            state="no_position_nearby:152559:VLK559",
            phase="no_position_nearby",
            event_key="no_position_nearby:152559:VLK559",
            hex="152559",
            flight="VLK559",
            spoken_flight="пять пять девять",
            announcement="",
            announcement_suppressed=True,
        )
        with_route = coordinator.AircraftCandidate(
            state="no_position_nearby:152559:VLK559",
            phase="no_position_nearby",
            event_key="no_position_nearby:152559:VLK559:route",
            hex="152559",
            flight="VLK559",
            airline_name="Van Air",
            spoken_flight="пять пять девять",
            origin_speech="Тбилиси",
            destination_speech="Батуми",
            announcement="Рядом самолёт без координат: Ван Эйр пять пять девять. Тбилиси - Батуми.",
        )

        self.assertFalse(fake._handle_candidate_event(silent))
        self.assertTrue(fake._handle_candidate_event(with_route))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], coordinator.EVENT_CANDIDATE)
        self.assertEqual(events[0][1]["announcement"], with_route.announcement)
        self.assertNotIn("Дополнение", events[0][1]["announcement"])

    async def test_airport_board_fetches_arrival_and_departure_rows(self) -> None:
        calls: list[str] = []

        class FakeCoordinator(coordinator.AircraftWindowCoordinator):
            async def _async_airport_board_leg(
                self,
                _session: object,
                *,
                provider_id: str,
                today: str,
                flight_leg: str,
                request_raw_url: str,
                cache_only: bool = False,
                deadline: float | None = None,
            ) -> dict[str, Any]:
                calls.append(f"{provider_id}:{flight_leg}:{request_raw_url}:{today}")
                return {
                    "data": {
                        "currentTime": "10.05.2026 15:00",
                        "flights": [
                            {
                                "airlineIata": "WZ",
                                "airlineIcao": "RWZ",
                                "flightNumber": "568",
                                "flightLeg": flight_leg,
                            }
                        ],
                    }
                }

        fake = FakeCoordinator.__new__(FakeCoordinator)
        board = await fake._async_airport_board(object())

        self.assertEqual(len(calls), 2)
        self.assertTrue(
            calls[0].startswith(
                "batumi_airport_board:DEPARTURE:/en-EN/flights/departure-flights:"
            )
        )
        self.assertTrue(
            calls[1].startswith(
                "batumi_airport_board:ARRIVAL:/en-EN/flights/arrival-flights:"
            )
        )
        self.assertEqual(len(board["data"]["flights"]), 2)
        self.assertEqual(
            fake._airport_board_match(board, "RWZ568", preferred_leg="DEPARTURE")["flightLeg"],
            "DEPARTURE",
        )

    async def test_airport_board_disabled_for_non_batumi_provider(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._runtime_settings = replace(
            settings.DEFAULT_RUNTIME_SETTINGS,
            local_airport=replace(
                settings.DEFAULT_RUNTIME_SETTINGS.local_airport,
                iata="ABC",
                board_provider="",
            ),
        )

        board = await fake._async_airport_board(object())

        self.assertEqual(board, {})

    def test_batumi_board_match_prefers_candidate_leg(self) -> None:
        board = {
            "data": {
                "flights": [
                    {
                        "airlineIata": "WZ",
                        "airlineIcao": "RWZ",
                        "flightNumber": "568",
                        "flightLeg": "ARRIVAL",
                        "path": {
                            "origin": {"originIata": "AER"},
                            "destination": {"destinationIata": "BUS"},
                        },
                    },
                    {
                        "airlineIata": "WZ",
                        "airlineIcao": "RWZ",
                        "flightNumber": "568",
                        "flightLeg": "DEPARTURE",
                        "path": {
                            "origin": {"originIata": "BUS"},
                            "destination": {"destinationIata": "AER"},
                        },
                    },
                ]
            }
        }
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )

        departure = fake._airport_board_match(board, "RWZ568", preferred_leg="DEPARTURE")
        arrival = fake._airport_board_match(board, "RWZ568", preferred_leg="ARRIVAL")
        fallback = fake._airport_board_match(board, "RWZ568")

        self.assertEqual(departure["path"]["origin"]["originIata"], "BUS")
        self.assertEqual(arrival["path"]["destination"]["destinationIata"], "BUS")
        self.assertEqual(fallback["path"]["origin"]["originIata"], "BUS")

    def test_batumi_board_match_maps_flyone_callsign_prefix_to_board_code(self) -> None:
        board = {
            "data": {
                "flights": [
                    {
                        "airlineIata": "3F",
                        "airlineIcao": "3F",
                        "flightNumber": "588",
                        "flightLeg": "DEPARTURE",
                        "path": {
                            "origin": {"originIata": "BUS"},
                            "destination": {"destinationIata": "EVN"},
                        },
                    },
                ]
            }
        }
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )

        departure = fake._airport_board_match(board, "FIE588", preferred_leg="DEPARTURE")

        self.assertEqual(departure["path"]["destination"]["destinationIata"], "EVN")

    def test_batumi_board_leg_for_positioned_phase(self) -> None:
        self.assertEqual(
            coordinator.AircraftWindowCoordinator._airport_board_leg_for_phase(
                "positioned_landing"
            ),
            "ARRIVAL",
        )
        self.assertEqual(
            coordinator.AircraftWindowCoordinator._airport_board_leg_for_phase(
                "positioned_approach"
            ),
            "ARRIVAL",
        )
        self.assertEqual(
            coordinator.AircraftWindowCoordinator._airport_board_leg_for_phase(
                "positioned_takeoff"
            ),
            "DEPARTURE",
        )
        self.assertEqual(
            coordinator.AircraftWindowCoordinator._airport_board_leg_for_phase(
                "no_position_nearby"
            ),
            "",
        )

    def test_callsign_route_must_match_local_phase(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )

        self.assertTrue(
            fake._route_matches_local_phase(
                "positioned_approach",
                "TLV",
                "BUS",
            )
        )
        self.assertFalse(
            fake._route_matches_local_phase(
                "positioned_approach",
                "TLV",
                "WAW",
            )
        )
        self.assertTrue(
            fake._route_matches_local_phase(
                "positioned_takeoff",
                "BUS",
                "TLV",
            )
        )
        self.assertFalse(
            fake._route_matches_local_phase(
                "positioned_takeoff",
                "TLV",
                "WAW",
            )
        )

    async def test_adsbdb_callsign_route_marks_source_and_uses_iata_speech(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.entry = types.SimpleNamespace(data={}, options={})
        fake.hass = types.SimpleNamespace()

        async def board(
            _session: object,
            *,
            cache_only: bool = False,
            deadline: float | None = None,
        ) -> dict[str, Any]:
            return {}

        async def get_json(
            _session: object,
            url: str,
            **_kwargs: Any,
        ) -> dict[str, Any]:
            if "/callsign/PGT458N" not in url:
                return {}
            return {
                "response": {
                    "flightroute": {
                        "airline": {
                            "name": "Pegasus Airlines",
                            "icao": "PGT",
                            "iata": "H9",
                        },
                        "origin": {
                            "iata_code": "SAW",
                            "icao_code": "LTFJ",
                            "municipality": "Pendik, Istanbul",
                            "name": "Istanbul Sabiha Gökçen International Airport",
                        },
                        "destination": {
                            "iata_code": "BUS",
                            "icao_code": "UGSB",
                            "municipality": "Batumi",
                            "name": "Batumi International Airport",
                        },
                    }
                }
            }

        async def built_year(
            _session: object,
            _registration: str,
            _timeout: object,
            **_kwargs: Any,
        ) -> None:
            return None

        fake._async_airport_board = board
        fake._async_get_json = get_json
        fake._async_airport_data_year = built_year

        attrs = await fake._async_enrich_aircraft(
            {"hex": "4bb862", "flight": "PGT458N"},
            phase="positioned_landing",
        )

        self.assertEqual(attrs["route_summary"], "SAW → BUS")
        self.assertEqual(attrs["route_source"], "adsbdb")
        self.assertEqual(attrs["origin_speech"], "Стамбула, Сабиха Гёкчен")
        self.assertEqual(attrs["spoken_flight"], "четыре пять восемь эн")
        self.assertNotRegex(attrs["spoken_flight"], r"[A-Za-z]")

    async def test_route_fallback_overrides_fill_missing_public_route(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.entry = types.SimpleNamespace(data={}, options={})
        fake.hass = types.SimpleNamespace()
        fake._runtime_settings = settings.runtime_settings_from_options(
            {
                "route_airline_prefix_overrides_json": '{"ABC": "Example Air"}',
                "route_callsign_overrides_json": (
                    '{"ABC123": {"airline_name": "Example Air", '
                    '"origin_iata": "XYZ", "origin_name": "Example City", '
                    '"origin_speech": "Экзампл-сити", '
                    '"destination_iata": "DEF", "destination_name": "Other City", '
                    '"destination_speech": "Отэр-сити", '
                    '"route_summary": "XYZ → DEF", "route_source": "user_override"}}'
                ),
            }
        )

        async def board(
            _session: object,
            *,
            cache_only: bool = False,
            deadline: float | None = None,
        ) -> dict[str, Any]:
            return {}

        async def get_json(
            _session: object,
            _url: str,
            **_kwargs: Any,
        ) -> dict[str, Any]:
            return {}

        async def built_year(
            _session: object,
            _registration: str,
            _timeout: object,
            **_kwargs: Any,
        ) -> None:
            return None

        fake._async_airport_board = board
        fake._async_get_json = get_json
        fake._async_airport_data_year = built_year

        attrs = await fake._async_enrich_aircraft(
            {"hex": "abc123", "flight": "ABC123"},
            phase="positioned_landing",
        )

        self.assertEqual(attrs["airline_name"], "Example Air")
        self.assertEqual(attrs["route_summary"], "XYZ → DEF")
        self.assertEqual(attrs["route_source"], "user_override")
        self.assertEqual(attrs["origin_speech"], "Экзампл-сити")
        self.assertEqual(attrs["destination_speech"], "Отэр-сити")

    def test_batumi_board_match_falls_back_to_single_airline_departure(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        payload = {
            "data": {
                "flights": [
                    {
                        "flightNumber": "311",
                        "flightLeg": "DEPARTURE",
                        "airlineIata": "PC",
                        "airlineIcao": "PGT",
                    }
                ]
            }
        }

        row = fake._airport_board_match(
            payload,
            "PGT48DK",
            preferred_leg="DEPARTURE",
        )

        self.assertEqual(row["flightNumber"], "311")

    def test_batumi_board_match_keeps_ambiguous_airline_fallback_empty(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        payload = {
            "data": {
                "flights": [
                    {
                        "flightNumber": "311",
                        "flightLeg": "DEPARTURE",
                        "airlineIata": "PC",
                        "airlineIcao": "PGT",
                    },
                    {
                        "flightNumber": "313",
                        "flightLeg": "DEPARTURE",
                        "airlineIata": "PC",
                        "airlineIcao": "PGT",
                    },
                ]
            }
        }

        row = fake._airport_board_match(
            payload,
            "PGT48DK",
            preferred_leg="DEPARTURE",
        )

        self.assertEqual(row, {})

    def test_parse_board_time_accepts_batumi_dot_format(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )

        parsed = fake._parse_board_time(
            "25.05.2026 15:00",
            coordinator.datetime(
                2026,
                5,
                25,
                12,
                0,
                tzinfo=coordinator.TBILISI_TIMEZONE,
            ),
        )

        self.assertEqual(parsed.isoformat(), "2026-05-25T15:00:00+04:00")

    def test_live_enrichment_fetches_route_or_missing_aircraft_identity(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )

        self.assertTrue(
            fake._should_fetch_live_enrichment(
                {"hex": "155bf7", "flight": "AZO7054"},
                "positioned_takeoff",
                {"aircraft_model_speech": "Суперджет"},
            )
        )
        self.assertFalse(
            fake._should_fetch_live_enrichment(
                {"hex": "155bf7", "flight": "155bf7"},
                "positioned_takeoff",
                {"registered_owner": "Azimuth", "aircraft_model_speech": "Суперджет"},
            )
        )
        self.assertTrue(
            fake._should_fetch_live_enrichment(
                {"hex": "73805a", "flight": "ELY5115"},
                "positioned_approach",
                {"destination_speech": "Батуми"},
            )
        )
        self.assertFalse(
            fake._should_fetch_live_enrichment(
                {"hex": "155bf7", "flight": "AZO7054"},
                "positioned_takeoff",
                {
                    "aircraft_model_speech": "Суперджет",
                    "destination_speech": "Москву, Внуково",
                },
            )
        )
        self.assertFalse(
            fake._should_fetch_live_enrichment(
                {"hex": "4bb18e", "flight": "THY299"},
                "no_position_nearby",
                {},
            )
        )

    def test_enrichment_sources_are_appended_once(self) -> None:
        attrs = {"enrichment_source": "airport_board"}

        coordinator.AircraftWindowCoordinator._add_enrichment_source(attrs, "adsbdb")
        coordinator.AircraftWindowCoordinator._add_enrichment_source(attrs, "adsbdb")

        self.assertEqual(attrs["enrichment_source"], "airport_board+adsbdb")

    def test_airport_board_route_uses_russian_speech_labels(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        attrs = {
            "airline_name": "",
            "enrichment_source": "",
        }
        fake._apply_airport_board_route(
            attrs,
            {
                "airlineName": "RED WINGS AIRLINES",
                "flightLeg": "DEPARTURE",
                "stad": "2026-05-25T12:00:00",
                "path": {
                    "origin": {"originIata": "BUS", "originEn": "Batumi (BUS)"},
                    "destination": {
                        "destinationIata": "ZIA",
                        "destinationEn": "Moscow Zhukovsky (ZIA)",
                    },
                },
            },
        )

        self.assertEqual(attrs["airline_name"], "RED WINGS AIRLINES")
        self.assertEqual(attrs["origin_speech"], "Батуми")
        self.assertEqual(attrs["destination_speech"], "подмосковный Жуковский")
        self.assertEqual(attrs["route_summary"], "BUS → ZIA")

    def test_airport_board_route_uses_tlv_airport_pronunciation(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        attrs = {
            "airline_name": "",
            "enrichment_source": "",
        }
        fake._apply_airport_board_route(
            attrs,
            {
                "airlineName": "EL AL",
                "flightLeg": "ARRIVAL",
                "stad": "2026-05-25T16:55:00",
                "path": {
                    "origin": {"originIata": "TLV", "originEn": "Tel Aviv (TLV)"},
                    "destination": {"destinationIata": "BUS", "destinationEn": "Batumi (BUS)"},
                },
            },
        )

        self.assertEqual(attrs["origin_speech"], "Бен Гуриона")
        self.assertEqual(attrs["destination_speech"], "Батуми")
        self.assertEqual(attrs["route_summary"], "TLV → BUS")

    def test_airplanes_live_aircraft_fills_missing_aircraft_identity(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        attrs = {
            "aircraft_model": "",
            "aircraft_type": "",
            "registration": "",
            "enrichment_source": "airport_board",
        }

        fake._apply_airplanes_live_aircraft(
            attrs,
            {
                "ac": [
                    {
                        "r": "4X-EKN",
                        "t": "B738",
                        "desc": "BOEING 737-800",
                    }
                ]
            },
        )

        self.assertEqual(attrs["registration"], "4X-EKN")
        self.assertEqual(attrs["aircraft_type"], "B738")
        self.assertEqual(attrs["aircraft_model"], "BOEING 737-800")
        self.assertEqual(attrs["enrichment_source"], "airport_board+airplanes_live")

    def test_visible_mapping_review_collects_unmapped_speech_values(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.entry = types.SimpleNamespace(data={}, options={})
        fake.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(latitude=41.62, longitude=41.62)
        )
        items = fake._mapping_review_items_for_visible_aircraft(
            {
                "hex": "abc123",
                "flight": "ABCD89",
                "lat": 41.61,
                "lon": 41.60,
                "seen": 1.0,
                "seen_pos": 1.0,
                "alt_baro": 1800,
                "baro_rate": -500,
                "gs": 160,
                "track": 290,
            },
            {
                "airline_name": "New Visible Air",
                "origin_iata": "XYZ",
                "origin_name": "New Place (XYZ)",
                "destination_iata": "ATH",
                "destination_name": "Athens (ATH)",
                "route_summary": "XYZ → ATH",
                "aircraft_model": "Mystery Jet 9000",
                "aircraft_type": "MJ90",
            },
        )

        kinds = {item["kind"] for item in items}
        self.assertIn("airline", kinds)
        self.assertIn("origin_airport", kinds)
        self.assertIn("route_airport", kinds)
        self.assertIn("aircraft_model", kinds)
        self.assertIn("callsign_prefix", kinds)
        self.assertNotIn(
            ("destination_airport", "Athens (ATH)"),
            {(item["kind"], item["value"]) for item in items},
        )
        self.assertIn(
            ("origin_airport", "New Place (XYZ)"),
            {(item["kind"], item["value"]) for item in items},
        )

    def test_visible_mapping_review_respects_speech_overrides(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake.entry = types.SimpleNamespace(data={}, options={})
        fake.hass = types.SimpleNamespace(
            config=types.SimpleNamespace(latitude=41.62, longitude=41.62)
        )
        fake._runtime_settings = settings.runtime_settings_from_options(
            {
                "speech_airline_overrides_json": '{"New Visible Air": "Нью Визибл"}',
                "speech_airport_code_from_overrides_json": '{"XYZ": "Иксвайзеда"}',
                "speech_airport_code_route_overrides_json": '{"XYZ": "Иксвайзед"}',
                "speech_callsign_prefix_overrides_json": '{"ABCD": "Абэцэдэ"}',
                "speech_model_overrides_json": (
                    '{"MYSTERY JET 9000 MJ90": "Мистери Джет девять тысяч"}'
                ),
            }
        )

        items = fake._mapping_review_items_for_visible_aircraft(
            {
                "hex": "abc123",
                "flight": "ABCD89",
                "lat": 41.61,
                "lon": 41.60,
                "seen": 1.0,
                "seen_pos": 1.0,
                "alt_baro": 1800,
                "baro_rate": -500,
                "gs": 160,
                "track": 290,
            },
            {
                "airline_name": "New Visible Air",
                "aircraft_model": "Mystery Jet 9000",
                "aircraft_type": "MJ90",
                "origin_iata": "XYZ",
                "origin_name": "New Place (XYZ)",
                "route_summary": "XYZ → ATH",
            },
        )

        kinds = {item["kind"] for item in items}
        self.assertNotIn("airline", kinds)
        self.assertNotIn("origin_airport", kinds)
        self.assertNotIn("route_airport", kinds)
        self.assertNotIn("aircraft_model", kinds)
        self.assertNotIn("callsign_prefix", kinds)

    async def test_mapping_review_record_prunes_resolved_items(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._runtime_settings = settings.runtime_settings_from_options(
            {"speech_model_overrides_json": '{"MJ90": "Мистери Джет"}'}
        )
        fake._cache = {
            coordinator.MAPPING_REVIEW_CACHE_KEY: [
                {
                    "key": "airport:to:KTW",
                    "kind": "destination_airport",
                    "value": "Katowice (KTW)",
                    "count": 3,
                    "first_seen": 1,
                    "last_seen": 2,
                },
                {
                    "key": "airline:new visible air",
                    "kind": "airline",
                    "value": "New Visible Air",
                    "count": 1,
                    "first_seen": 1,
                    "last_seen": 2,
                },
                {
                    "key": "model:mj90",
                    "kind": "aircraft_model",
                    "value": "Mystery Jet 9000 MJ90",
                    "count": 1,
                    "first_seen": 1,
                    "last_seen": 2,
                },
            ]
        }
        saved: list[dict[str, Any]] = []

        async def load_cache() -> dict[str, Any]:
            return fake._cache

        async def save_cache() -> None:
            saved.append(dict(fake._cache))

        fake._async_cache = load_cache
        fake._async_save_cache = save_cache

        items = await fake._async_record_mapping_review_items([])

        self.assertEqual([item["key"] for item in items], ["airline:new visible air"])
        self.assertEqual(saved[-1][coordinator.MAPPING_REVIEW_CACHE_KEY], items)

    def test_scheduled_preopen_result_turns_on_inside_departure_window(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        now = datetime(2026, 5, 20, 12, 0, tzinfo=coordinator.TBILISI_TIMEZONE)
        board = {
            "data": {
                "flights": [
                    {
                        "airlineIata": "WZ",
                        "airlineIcao": "RWZ",
                        "airlineName": "Red Wings",
                        "flightNumber": "1566",
                        "flightLeg": "DEPARTURE",
                        "stad": "2026-05-20T12:03:00",
                        "path": {
                            "origin": {
                                "originIata": "BUS",
                                "originEn": "Batumi (BUS)",
                            },
                            "destination": {
                                "destinationIata": "AER",
                                "destinationEn": "Sochi (AER)",
                            },
                        },
                    }
                ],
            }
        }

        result = fake._scheduled_preopen_result(board, now=now)

        self.assertEqual(result["state"], "on")
        self.assertEqual(result["phase"], "scheduled_departure_preopen")
        self.assertEqual(result["flight"], "RWZ1566")
        self.assertEqual(result["origin_iata"], "BUS")
        self.assertEqual(result["destination_iata"], "AER")
        self.assertEqual(result["scheduled_departure_local"], "12:03")
        self.assertEqual(result["seconds_until_departure"], 180)

    async def test_deadline_miss_does_not_cache_airport_board_error(self) -> None:
        class FailingSession:
            def get(self, *_args: Any, **_kwargs: Any) -> object:
                raise AssertionError("expired deadline must not fetch")

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._cache = {}

        async def load_cache() -> dict[str, Any]:
            return fake._cache

        async def save_cache() -> None:
            raise AssertionError("deadline miss must not cache airport board error")

        fake._async_cache = load_cache
        fake._async_save_cache = save_cache

        result = await fake._async_airport_board_leg(
            FailingSession(),
            provider_id="batumi_airport_board",
            today="20.05.2026",
            flight_leg="DEPARTURE",
            request_raw_url="/en-EN/flights/departure-flights",
            deadline=coordinator.time.monotonic() - 0.01,
        )

        self.assertEqual(result, {})
        self.assertEqual(fake._cache, {})

    async def test_cache_only_json_does_not_fetch_external_lookup(self) -> None:
        class FailingSession:
            def get(self, *_args: Any, **_kwargs: Any) -> object:
                raise AssertionError("cache-only enrichment must not fetch")

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._cache = {}

        async def load_cache() -> dict[str, Any]:
            return fake._cache

        async def save_cache() -> None:
            raise AssertionError("cache-only miss must not write an error")

        fake._async_cache = load_cache
        fake._async_save_cache = save_cache

        result = await fake._async_get_json(
            FailingSession(),
            "https://api.adsbdb.com/v0/callsign/RWZ1565",
            cache_key="callsign:RWZ1565",
            ttl_seconds=coordinator.ROUTE_CACHE_SECONDS,
            timeout=coordinator.aiohttp.ClientTimeout(total=1.0),
            cache_only=True,
        )

        self.assertEqual(result, {})
        self.assertEqual(fake._cache, {})

    async def test_deadline_miss_does_not_cache_external_error(self) -> None:
        class FailingSession:
            def get(self, *_args: Any, **_kwargs: Any) -> object:
                raise AssertionError("expired deadline must not fetch")

        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )
        fake._cache = {}

        async def load_cache() -> dict[str, Any]:
            return fake._cache

        async def save_cache() -> None:
            raise AssertionError("deadline miss must not cache an error")

        fake._async_cache = load_cache
        fake._async_save_cache = save_cache

        result = await fake._async_get_json(
            FailingSession(),
            "https://api.adsbdb.com/v0/callsign/RWZ1565",
            cache_key="callsign:RWZ1565",
            ttl_seconds=coordinator.ROUTE_CACHE_SECONDS,
            timeout=coordinator.aiohttp.ClientTimeout(total=1.0),
            deadline=coordinator.time.monotonic() - 0.01,
        )

        self.assertEqual(result, {})
        self.assertEqual(fake._cache, {})


if __name__ == "__main__":
    unittest.main()
