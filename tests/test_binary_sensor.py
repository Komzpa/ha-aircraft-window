"""Tests for Aircraft Window binary sensors."""

from __future__ import annotations

import sys
import types
import unittest
from importlib import util
from pathlib import Path
from typing import Any

COMPONENT_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "aircraft_window"


def _stub_homeassistant_modules() -> None:
    """Install tiny Home Assistant stubs for importing the binary sensor module."""
    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    binary_sensor_mod = types.ModuleType("homeassistant.components.binary_sensor")
    helpers = types.ModuleType("homeassistant.helpers")
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class BinarySensorEntity:
        pass

    class CoordinatorEntity:
        def __class_getitem__(cls, _item: object) -> type[CoordinatorEntity]:
            return cls

        def __init__(self, coordinator: Any) -> None:
            self.coordinator = coordinator

    class DataUpdateCoordinator:
        def __class_getitem__(cls, _item: object) -> type[DataUpdateCoordinator]:
            return cls

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

    binary_sensor_mod.BinarySensorEntity = BinarySensorEntity
    update_coordinator.CoordinatorEntity = CoordinatorEntity
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.components", components)
    sys.modules.setdefault("homeassistant.components.binary_sensor", binary_sensor_mod)
    sys.modules.setdefault("homeassistant.helpers", helpers)
    sys.modules.setdefault("homeassistant.helpers.update_coordinator", update_coordinator)


def _load_component_module(name: str) -> types.ModuleType:
    """Load an aircraft_window module under a package name for relative imports."""
    package = sys.modules.get("aircraft_window")
    if package is None:
        package = types.ModuleType("aircraft_window")
        package.__path__ = [str(COMPONENT_ROOT)]  # type: ignore[attr-defined]
        package.AircraftWindowConfigEntry = object
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
logic = _load_component_module("logic")
coordinator_stub = types.ModuleType("aircraft_window.coordinator")
coordinator_stub.AircraftWindowCoordinator = object
coordinator_stub.EnrichmentPrefetchCoordinator = object
sys.modules["aircraft_window.coordinator"] = coordinator_stub
binary_sensor = _load_component_module("binary_sensor")


class AircraftWindowBinarySensorTest(unittest.TestCase):
    """Verify curtain-opening sensors do not act on projection-only candidates."""

    def _curtain_sensor_for(self, candidate: object) -> object:
        sensor = binary_sensor.AircraftWindowCurtainPreopenBinarySensor.__new__(
            binary_sensor.AircraftWindowCurtainPreopenBinarySensor
        )
        sensor.coordinator = types.SimpleNamespace(
            data=candidate,
            runtime_settings=settings.DEFAULT_RUNTIME_SETTINGS,
        )
        return sensor

    def test_projected_candidate_does_not_preopen_curtains(self) -> None:
        candidate = logic.AircraftCandidate(
            phase="positioned_takeoff",
            altitude_ft=2000,
            window_visible=False,
            window_preopen_needed=True,
            window_runway_staging=False,
            window_view_reason="projected into window view in 15s",
        )

        self.assertFalse(self._curtain_sensor_for(candidate).is_on)

    def test_visible_candidate_can_preopen_curtains(self) -> None:
        visible = logic.AircraftCandidate(
            phase="positioned_takeoff",
            altitude_ft=2000,
            window_visible=True,
            window_preopen_needed=True,
            window_runway_staging=False,
        )

        self.assertTrue(self._curtain_sensor_for(visible).is_on)

    def test_configured_watched_route_can_preopen_curtains(self) -> None:
        visible = logic.AircraftCandidate(
            phase="kutaisi_route",
            altitude_ft=7000,
            window_visible=True,
            window_preopen_needed=True,
            window_runway_staging=False,
        )

        self.assertTrue(self._curtain_sensor_for(visible).is_on)


if __name__ == "__main__":
    unittest.main()
