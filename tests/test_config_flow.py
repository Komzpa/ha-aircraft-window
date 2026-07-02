"""Tests for config-flow schema defaults without a Home Assistant runtime."""

from __future__ import annotations

import sys
import types
import unittest
from importlib import util
from pathlib import Path
from typing import Any

COMPONENT_ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "aircraft_window"


def _stub_homeassistant_modules() -> None:
    """Install tiny Home Assistant stubs for importing the config flow."""
    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")

    class ConfigEntry:
        pass

    class HomeAssistant:
        pass

    class ConfigFlow:
        def __init_subclass__(cls, **_kwargs: Any) -> None:
            super().__init_subclass__()

    class OptionsFlow:
        pass

    config_entries.ConfigEntry = ConfigEntry
    config_entries.ConfigFlow = ConfigFlow
    config_entries.ConfigFlowResult = dict
    config_entries.OptionsFlow = OptionsFlow
    core.callback = lambda func: func
    core.HomeAssistant = HomeAssistant

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.config_entries", config_entries)
    sys.modules.setdefault("homeassistant.core", core)


def _stub_voluptuous_module() -> None:
    """Install a tiny voluptuous stub that preserves schema defaults."""
    voluptuous = types.ModuleType("voluptuous")

    class Marker:
        def __init__(self, schema: str, *, default: Any = None) -> None:
            self.schema = schema
            self._default = default

        def default(self) -> Any:
            return self._default

    class Schema:
        def __init__(self, schema: dict[Any, Any]) -> None:
            self.schema = schema

    class InValidator:
        def __init__(self, container: object) -> None:
            self.container = container

    voluptuous.Required = lambda schema, default=None: Marker(schema, default=default)
    voluptuous.Optional = lambda schema, default=None: Marker(schema, default=default)
    voluptuous.All = lambda *validators: validators
    voluptuous.Coerce = lambda target: target
    voluptuous.In = InValidator
    voluptuous.Range = lambda **_kwargs: object()
    voluptuous.Schema = Schema

    sys.modules.setdefault("voluptuous", voluptuous)


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
_stub_voluptuous_module()
const = _load_component_module("const")
config_flow = _load_component_module("config_flow")


def _field_default(schema: Any, field: str) -> Any:
    """Return the default attached to a voluptuous marker in a schema."""
    for marker in schema.schema:
        if getattr(marker, "schema", None) == field:
            return marker.default()
    raise AssertionError(f"missing schema field {field}")


def _field_validator(schema: Any, field: str) -> Any:
    """Return the validator attached to a voluptuous marker in a schema."""
    for marker, validator in schema.schema.items():
        if getattr(marker, "schema", None) == field:
            return validator
    raise AssertionError(f"missing schema field {field}")


class AircraftWindowConfigFlowTest(unittest.TestCase):
    """Verify config-flow defaults that affect dehardcoded profiles."""

    def test_schema_hides_stored_batumi_defaults_for_other_airports(self) -> None:
        schema = config_flow._schema(
            {
                const.CONF_LOCAL_AIRPORT_IATA: "ABC",
                const.CONF_LOCAL_AIRPORT_NAME: "Batumi",
                const.CONF_AIRPORT_BOARD_PROVIDER: "batumi_airport_board",
                const.CONF_WATCH_AIRPORTS: "KUT",
            },
            include_home_coordinates=False,
        )

        self.assertEqual(_field_default(schema, const.CONF_LOCAL_AIRPORT_NAME), "ABC")
        self.assertEqual(_field_default(schema, const.CONF_AIRPORT_BOARD_PROVIDER), "")
        self.assertEqual(_field_default(schema, const.CONF_WATCH_AIRPORTS), "")

    def test_schema_keeps_custom_provider_defaults_for_other_airports(self) -> None:
        schema = config_flow._schema(
            {
                const.CONF_LOCAL_AIRPORT_IATA: "ABC",
                const.CONF_LOCAL_AIRPORT_NAME: "Custom Airport",
                const.CONF_AIRPORT_BOARD_PROVIDER: "json_airport_board",
                const.CONF_WATCH_AIRPORTS: "DEF",
            },
            include_home_coordinates=False,
        )

        self.assertEqual(
            _field_default(schema, const.CONF_LOCAL_AIRPORT_NAME),
            "Custom Airport",
        )
        self.assertEqual(
            _field_default(schema, const.CONF_AIRPORT_BOARD_PROVIDER),
            "json_airport_board",
        )
        self.assertEqual(_field_default(schema, const.CONF_WATCH_AIRPORTS), "DEF")

    def test_schema_limits_airport_board_provider_choices(self) -> None:
        schema = config_flow._schema({}, include_home_coordinates=False)

        validator = _field_validator(schema, const.CONF_AIRPORT_BOARD_PROVIDER)

        self.assertEqual(
            validator.container,
            ("", "batumi_airport_board", "json_airport_board"),
        )

    def test_schema_limits_speech_locale_choices(self) -> None:
        schema = config_flow._schema(
            {const.CONF_SPEECH_LOCALE: "en"},
            include_home_coordinates=False,
        )

        validator = _field_validator(schema, const.CONF_SPEECH_LOCALE)

        self.assertEqual(_field_default(schema, const.CONF_SPEECH_LOCALE), "ru")
        self.assertEqual(validator.container, ("ru",))

    def test_schema_defaults_area_flags_by_profile(self) -> None:
        default_schema = config_flow._schema({}, include_home_coordinates=False)
        other_schema = config_flow._schema(
            {const.CONF_LOCAL_AIRPORT_IATA: "ABC"},
            include_home_coordinates=False,
        )

        self.assertTrue(_field_default(default_schema, const.CONF_TERMINAL_AREA_ENABLED))
        self.assertTrue(_field_default(default_schema, const.CONF_RUNWAY_STAGING_ENABLED))
        self.assertFalse(_field_default(other_schema, const.CONF_TERMINAL_AREA_ENABLED))
        self.assertFalse(_field_default(other_schema, const.CONF_RUNWAY_STAGING_ENABLED))

    def test_schema_enables_area_flags_for_legacy_custom_values(self) -> None:
        schema = config_flow._schema(
            {
                const.CONF_LOCAL_AIRPORT_IATA: "ABC",
                const.CONF_TERMINAL_AREA_LATITUDE: 47.1,
                const.CONF_RUNWAY_STAGING_LATITUDE: 47.2,
            },
            include_home_coordinates=False,
        )

        self.assertTrue(_field_default(schema, const.CONF_TERMINAL_AREA_ENABLED))
        self.assertTrue(_field_default(schema, const.CONF_RUNWAY_STAGING_ENABLED))


if __name__ == "__main__":
    unittest.main()
