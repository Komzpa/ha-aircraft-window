"""Tests for coordinator helpers that do not need a running Home Assistant."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime
from importlib import util
from pathlib import Path
from typing import Any

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

        self.assertTrue(fake._handle_candidate_event(previous))
        self.assertTrue(fake._handle_candidate_event(current))

        self.assertEqual(len(events), 2)
        self.assertEqual(
            events[1][1]["announcement"],
            "Дополнение: это Исра Эйр восемь девять ноль, в Тель-Авив.",
        )

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

        self.assertTrue(fake._handle_candidate_event(previous))
        self.assertFalse(fake._handle_candidate_event(callsign_only))
        self.assertTrue(fake._handle_candidate_event(with_route))

        self.assertEqual(len(events), 2)
        self.assertEqual(
            events[1][1]["announcement"],
            "Дополнение: это Исра Эйр восемь девять ноль, в Тель-Авив.",
        )

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

    def test_enrichment_sources_are_appended_once(self) -> None:
        attrs = {"enrichment_source": "airport_board"}

        coordinator.AircraftWindowCoordinator._add_enrichment_source(attrs, "adsbdb")
        coordinator.AircraftWindowCoordinator._add_enrichment_source(attrs, "adsbdb")

        self.assertEqual(attrs["enrichment_source"], "airport_board+adsbdb")

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
