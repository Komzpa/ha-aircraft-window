"""Tests for coordinator helpers that do not need a running Home Assistant."""

from __future__ import annotations

import sys
import types
import unittest
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


if __name__ == "__main__":
    unittest.main()
