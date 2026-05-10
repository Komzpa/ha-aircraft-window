"""Config flow for Aircraft Window."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_DUMP1090_URL,
    CONF_ENABLE_ENRICHMENT,
    CONF_ENRICHMENT_TIMEOUT_SECONDS,
    CONF_HOME_LATITUDE,
    CONF_HOME_LONGITUDE,
    CONF_MAX_APPROACH_ALTITUDE_FT,
    CONF_MAX_APPROACH_DISTANCE_KM,
    CONF_MAX_NO_POSITION_SEEN_SECONDS,
    CONF_MAX_POSITIONED_DISTANCE_KM,
    CONF_SCAN_INTERVAL_SECONDS,
    DEFAULT_DUMP1090_URL,
    DEFAULT_ENRICHMENT_TIMEOUT_SECONDS,
    DEFAULT_MAX_APPROACH_ALTITUDE_FT,
    DEFAULT_MAX_APPROACH_DISTANCE_KM,
    DEFAULT_MAX_NO_POSITION_SEEN_SECONDS,
    DEFAULT_MAX_POSITIONED_DISTANCE_KM,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)


def _schema(defaults: dict[str, Any], *, include_home_coordinates: bool) -> vol.Schema:
    fields: dict[vol.Marker, Any] = {
        vol.Required(
            CONF_DUMP1090_URL,
            default=defaults.get(CONF_DUMP1090_URL, DEFAULT_DUMP1090_URL),
        ): str,
        vol.Required(
            CONF_MAX_POSITIONED_DISTANCE_KM,
            default=defaults.get(
                CONF_MAX_POSITIONED_DISTANCE_KM,
                DEFAULT_MAX_POSITIONED_DISTANCE_KM,
            ),
        ): vol.Coerce(float),
        vol.Required(
            CONF_MAX_APPROACH_DISTANCE_KM,
            default=defaults.get(
                CONF_MAX_APPROACH_DISTANCE_KM,
                DEFAULT_MAX_APPROACH_DISTANCE_KM,
            ),
        ): vol.Coerce(float),
        vol.Required(
            CONF_MAX_APPROACH_ALTITUDE_FT,
            default=defaults.get(
                CONF_MAX_APPROACH_ALTITUDE_FT,
                DEFAULT_MAX_APPROACH_ALTITUDE_FT,
            ),
        ): vol.Coerce(float),
        vol.Required(
            CONF_MAX_NO_POSITION_SEEN_SECONDS,
            default=defaults.get(
                CONF_MAX_NO_POSITION_SEEN_SECONDS,
                DEFAULT_MAX_NO_POSITION_SEEN_SECONDS,
            ),
        ): vol.Coerce(float),
        vol.Required(
            CONF_SCAN_INTERVAL_SECONDS,
            default=defaults.get(CONF_SCAN_INTERVAL_SECONDS, DEFAULT_SCAN_INTERVAL_SECONDS),
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
        vol.Required(
            CONF_ENABLE_ENRICHMENT,
            default=defaults.get(CONF_ENABLE_ENRICHMENT, True),
        ): bool,
        vol.Required(
            CONF_ENRICHMENT_TIMEOUT_SECONDS,
            default=defaults.get(
                CONF_ENRICHMENT_TIMEOUT_SECONDS,
                DEFAULT_ENRICHMENT_TIMEOUT_SECONDS,
            ),
        ): vol.Coerce(float),
    }

    if include_home_coordinates:
        fields.update(
            {
                vol.Required(
                    CONF_HOME_LATITUDE,
                    default=defaults[CONF_HOME_LATITUDE],
                ): float,
                vol.Required(
                    CONF_HOME_LONGITUDE,
                    default=defaults[CONF_HOME_LONGITUDE],
                ): float,
            }
        )

    return vol.Schema(fields)


class AircraftWindowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Aircraft Window config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Create an Aircraft Window config entry."""
        await self.async_set_unique_id("aircraft_window")
        self._abort_if_unique_id_configured()

        defaults: dict[str, Any] = {}
        if user_input is not None:
            return self.async_create_entry(title="Aircraft Window", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(defaults, include_home_coordinates=False),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return AircraftWindowOptionsFlow(config_entry)


class AircraftWindowOptionsFlow(config_entries.OptionsFlow):
    """Handle Aircraft Window options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {
            CONF_HOME_LATITUDE: self.hass.config.latitude,
            CONF_HOME_LONGITUDE: self.hass.config.longitude,
        }
        defaults.update(self._config_entry.data)
        defaults.update(self._config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(defaults, include_home_coordinates=True),
        )
