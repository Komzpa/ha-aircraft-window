"""Tests for coordinator helpers that do not need a running Home Assistant."""

from __future__ import annotations

import sys
import types
import unittest
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
_load_component_module("logic")
coordinator = _load_component_module("coordinator")


class BatumiAirportBoardTest(unittest.IsolatedAsyncioTestCase):
    """Verify Batumi Airport board matching and aggregation."""

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
            destination_speech="Тель-Авив",
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
            "Дополнение: это Исра Эйр, в Тель-Авив.",
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
                "destination_speech": "Тель-Авив",
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
            "Дополнение: это Исра Эйр, в Тель-Авив.",
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

    async def test_batumi_board_fetches_arrival_and_departure_rows(self) -> None:
        calls: list[str] = []

        class FakeCoordinator(coordinator.AircraftWindowCoordinator):
            async def _async_batumi_airport_board_leg(
                self,
                _session: object,
                *,
                today: str,
                flight_leg: str,
                request_raw_url: str,
                cache_only: bool = False,
                deadline: float | None = None,
            ) -> dict[str, Any]:
                calls.append(f"{flight_leg}:{request_raw_url}:{today}")
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
        board = await fake._async_batumi_airport_board(object())

        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[0].startswith("DEPARTURE:/en-EN/flights/departure-flights:"))
        self.assertTrue(calls[1].startswith("ARRIVAL:/en-EN/flights/arrival-flights:"))
        self.assertEqual(len(board["data"]["flights"]), 2)
        self.assertEqual(
            fake._airport_board_match(board, "RWZ568", preferred_leg="DEPARTURE")["flightLeg"],
            "DEPARTURE",
        )

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

    def test_parse_board_time_accepts_batumi_dot_format(self) -> None:
        parsed = coordinator.AircraftWindowCoordinator._parse_board_time(
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

    def test_live_route_fetch_is_limited_to_real_callsign_route_misses(self) -> None:
        fake = coordinator.AircraftWindowCoordinator.__new__(
            coordinator.AircraftWindowCoordinator
        )

        self.assertTrue(
            fake._should_fetch_live_route(
                {"hex": "155bf7", "flight": "AZO7054"},
                "positioned_takeoff",
                {"aircraft_model_speech": "Суперджет"},
            )
        )
        self.assertFalse(
            fake._should_fetch_live_route(
                {"hex": "155bf7", "flight": "155bf7"},
                "positioned_takeoff",
                {"registered_owner": "Azimuth", "aircraft_model_speech": "Суперджет"},
            )
        )
        self.assertFalse(
            fake._should_fetch_live_route(
                {"hex": "155bf7", "flight": "AZO7054"},
                "positioned_takeoff",
                {"destination_speech": "Москву, Внуково"},
            )
        )
        self.assertFalse(
            fake._should_fetch_live_route(
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
        self.assertEqual(attrs["destination_speech"], "Жуковский")
        self.assertEqual(attrs["route_summary"], "BUS → ZIA")

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

        result = await fake._async_batumi_airport_board_leg(
            FailingSession(),
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
