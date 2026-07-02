"""Config flow for Aircraft Window."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_ADSBDB_BASE_URL,
    CONF_AIRPLANES_LIVE_BASE_URL,
    CONF_AIRPORT_BOARD_CACHE_SECONDS,
    CONF_AIRPORT_BOARD_PROVIDER,
    CONF_AIRPORT_DATA_BASE_URL,
    CONF_BACKGROUND_INTERVAL_SECONDS,
    CONF_BATUMI_AIRPORT_BOARD_BASE_URL,
    CONF_BUILT_YEAR_CACHE_SECONDS,
    CONF_COLLECT_MAPPING_REVIEW,
    CONF_DAY_HUMAN_VISIBLE_RADIUS_KM,
    CONF_DUMP1090_URL,
    CONF_ENABLE_ENRICHMENT,
    CONF_ENRICHMENT_TIMEOUT_SECONDS,
    CONF_HEXDB_BASE_URL,
    CONF_HOME_LATITUDE,
    CONF_HOME_LONGITUDE,
    CONF_LOCAL_AIRPORT_IATA,
    CONF_LOCAL_AIRPORT_NAME,
    CONF_LOCAL_TIMEZONE_OFFSET_HOURS,
    CONF_LOW_LIGHT_HUMAN_VISIBLE_RADIUS_KM,
    CONF_MAX_APPROACH_ALTITUDE_FT,
    CONF_MAX_APPROACH_DISTANCE_KM,
    CONF_MAX_NO_POSITION_SEEN_SECONDS,
    CONF_MAX_POSITIONED_DISTANCE_KM,
    CONF_NIGHT_HUMAN_VISIBLE_RADIUS_KM,
    CONF_ORBIT_MAX_GROUND_SPEED_KT,
    CONF_ORBIT_MIN_GROUND_SPEED_KT,
    CONF_ORBIT_TRACK_RATE_DEGREES_PER_SECOND,
    CONF_PREFETCH_BUDGET_SECONDS,
    CONF_PREFETCH_LIMIT,
    CONF_RAPID_DESCENT_FPM,
    CONF_RAPID_DESCENT_MIN_ALTITUDE_FT,
    CONF_ROUTE_AIRLINE_PREFIX_OVERRIDES,
    CONF_ROUTE_CALLSIGN_OVERRIDES,
    CONF_RUNWAY_STAGING_LATITUDE,
    CONF_RUNWAY_STAGING_LONGITUDE,
    CONF_RUNWAY_STAGING_MAX_ALTITUDE_FT,
    CONF_RUNWAY_STAGING_MAX_SPEED_KT,
    CONF_RUNWAY_STAGING_RADIUS_KM,
    CONF_SCAN_INTERVAL_SECONDS,
    CONF_SPEECH_AIRLINE_ALIAS_OVERRIDES,
    CONF_SPEECH_AIRLINE_OVERRIDES,
    CONF_SPEECH_AIRPORT_CODE_FROM_OVERRIDES,
    CONF_SPEECH_AIRPORT_CODE_ROUTE_OVERRIDES,
    CONF_SPEECH_AIRPORT_CODE_TO_OVERRIDES,
    CONF_SPEECH_CALLSIGN_PREFIX_OVERRIDES,
    CONF_SPEECH_CITY_FROM_OVERRIDES,
    CONF_SPEECH_CITY_ROUTE_OVERRIDES,
    CONF_SPEECH_CITY_TO_OVERRIDES,
    CONF_SPEECH_MODEL_OVERRIDES,
    CONF_TERMINAL_AREA_LATITUDE,
    CONF_TERMINAL_AREA_LONGITUDE,
    CONF_TERMINAL_AREA_MAX_ALTITUDE_FT,
    CONF_TERMINAL_AREA_RADIUS_KM,
    CONF_TERMINAL_SUPPRESSION_ENABLED,
    CONF_WATCH_AIRPORTS,
    CONF_WINDOW_VIEW_AZIMUTH_DEGREES,
    CONF_WINDOW_VIEW_HALF_ANGLE_DEGREES,
    CONF_WINDOW_VIEW_LEAD_SECONDS,
    CONF_WINDOW_VIEW_POLYGON_JSON,
    CONF_WINDOW_VIEW_PROJECTION_STEP_SECONDS,
    CONF_WINDOW_VIEW_RADIUS_KM,
    DEFAULT_BACKGROUND_INTERVAL_SECONDS,
    DEFAULT_COLLECT_MAPPING_REVIEW,
    DEFAULT_DUMP1090_URL,
    DEFAULT_ENRICHMENT_TIMEOUT_SECONDS,
    DEFAULT_MAX_APPROACH_ALTITUDE_FT,
    DEFAULT_MAX_APPROACH_DISTANCE_KM,
    DEFAULT_MAX_NO_POSITION_SEEN_SECONDS,
    DEFAULT_MAX_POSITIONED_DISTANCE_KM,
    DEFAULT_PREFETCH_BUDGET_SECONDS,
    DEFAULT_PREFETCH_LIMIT,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from .settings import DEFAULT_RUNTIME_SETTINGS

DEFAULT_WATCH_AIRPORTS = ",".join(
    airport.iata for airport in DEFAULT_RUNTIME_SETTINGS.watch_policy.watch_airports
)


def _schema(defaults: dict[str, Any], *, include_home_coordinates: bool) -> vol.Schema:
    default_airport = DEFAULT_RUNTIME_SETTINGS.local_airport
    default_terminal = default_airport.terminal_area
    assert default_terminal is not None
    default_staging = default_airport.runway_staging_areas[0]
    default_view = DEFAULT_RUNTIME_SETTINGS.window_view
    default_policy = DEFAULT_RUNTIME_SETTINGS.watch_policy
    default_timezone_offset_hours = (
        default_airport.timezone.utcoffset(None).total_seconds() / 3600.0
    )
    fields: dict[vol.Marker, Any] = {
        vol.Required(
            CONF_DUMP1090_URL,
            default=defaults.get(CONF_DUMP1090_URL, DEFAULT_DUMP1090_URL),
        ): str,
        vol.Required(
            CONF_LOCAL_AIRPORT_IATA,
            default=defaults.get(CONF_LOCAL_AIRPORT_IATA, default_airport.iata),
        ): str,
        vol.Required(
            CONF_LOCAL_AIRPORT_NAME,
            default=defaults.get(CONF_LOCAL_AIRPORT_NAME, default_airport.name),
        ): str,
        vol.Required(
            CONF_LOCAL_TIMEZONE_OFFSET_HOURS,
            default=defaults.get(
                CONF_LOCAL_TIMEZONE_OFFSET_HOURS,
                default_timezone_offset_hours,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=-12.0, max=14.0)),
        vol.Required(
            CONF_AIRPORT_BOARD_PROVIDER,
            default=defaults.get(
                CONF_AIRPORT_BOARD_PROVIDER,
                default_airport.board_provider,
            ),
        ): str,
        vol.Required(
            CONF_WINDOW_VIEW_LEAD_SECONDS,
            default=defaults.get(
                CONF_WINDOW_VIEW_LEAD_SECONDS,
                default_view.lead_seconds,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=3600.0)),
        vol.Required(
            CONF_WINDOW_VIEW_PROJECTION_STEP_SECONDS,
            default=defaults.get(
                CONF_WINDOW_VIEW_PROJECTION_STEP_SECONDS,
                default_view.projection_step_seconds,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=300.0)),
        vol.Required(
            CONF_WINDOW_VIEW_AZIMUTH_DEGREES,
            default=defaults.get(
                CONF_WINDOW_VIEW_AZIMUTH_DEGREES,
                default_view.azimuth_degrees,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=360.0)),
        vol.Required(
            CONF_WINDOW_VIEW_HALF_ANGLE_DEGREES,
            default=defaults.get(
                CONF_WINDOW_VIEW_HALF_ANGLE_DEGREES,
                default_view.half_angle_degrees,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=180.0)),
        vol.Required(
            CONF_WINDOW_VIEW_RADIUS_KM,
            default=defaults.get(CONF_WINDOW_VIEW_RADIUS_KM, default_view.default_radius_km),
        ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=500.0)),
        vol.Optional(
            CONF_WINDOW_VIEW_POLYGON_JSON,
            default=defaults.get(CONF_WINDOW_VIEW_POLYGON_JSON, ""),
        ): str,
        vol.Required(
            CONF_DAY_HUMAN_VISIBLE_RADIUS_KM,
            default=defaults.get(
                CONF_DAY_HUMAN_VISIBLE_RADIUS_KM,
                default_view.day_radius_km,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=500.0)),
        vol.Required(
            CONF_LOW_LIGHT_HUMAN_VISIBLE_RADIUS_KM,
            default=defaults.get(
                CONF_LOW_LIGHT_HUMAN_VISIBLE_RADIUS_KM,
                default_view.low_light_radius_km,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=500.0)),
        vol.Required(
            CONF_NIGHT_HUMAN_VISIBLE_RADIUS_KM,
            default=defaults.get(
                CONF_NIGHT_HUMAN_VISIBLE_RADIUS_KM,
                default_view.night_radius_km,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=1.0, max=500.0)),
        vol.Required(
            CONF_TERMINAL_AREA_LATITUDE,
            default=defaults.get(CONF_TERMINAL_AREA_LATITUDE, default_terminal.latitude),
        ): vol.Coerce(float),
        vol.Required(
            CONF_TERMINAL_AREA_LONGITUDE,
            default=defaults.get(CONF_TERMINAL_AREA_LONGITUDE, default_terminal.longitude),
        ): vol.Coerce(float),
        vol.Required(
            CONF_TERMINAL_AREA_RADIUS_KM,
            default=defaults.get(CONF_TERMINAL_AREA_RADIUS_KM, default_terminal.radius_km),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=500.0)),
        vol.Required(
            CONF_TERMINAL_AREA_MAX_ALTITUDE_FT,
            default=defaults.get(
                CONF_TERMINAL_AREA_MAX_ALTITUDE_FT,
                default_terminal.max_altitude_ft,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=60000.0)),
        vol.Required(
            CONF_RUNWAY_STAGING_LATITUDE,
            default=defaults.get(CONF_RUNWAY_STAGING_LATITUDE, default_staging.latitude),
        ): vol.Coerce(float),
        vol.Required(
            CONF_RUNWAY_STAGING_LONGITUDE,
            default=defaults.get(CONF_RUNWAY_STAGING_LONGITUDE, default_staging.longitude),
        ): vol.Coerce(float),
        vol.Required(
            CONF_RUNWAY_STAGING_RADIUS_KM,
            default=defaults.get(CONF_RUNWAY_STAGING_RADIUS_KM, default_staging.radius_km),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=100.0)),
        vol.Required(
            CONF_RUNWAY_STAGING_MAX_ALTITUDE_FT,
            default=defaults.get(
                CONF_RUNWAY_STAGING_MAX_ALTITUDE_FT,
                default_staging.max_altitude_ft,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10000.0)),
        vol.Required(
            CONF_RUNWAY_STAGING_MAX_SPEED_KT,
            default=defaults.get(
                CONF_RUNWAY_STAGING_MAX_SPEED_KT,
                default_staging.max_speed_kt,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=300.0)),
        vol.Required(
            CONF_WATCH_AIRPORTS,
            default=defaults.get(CONF_WATCH_AIRPORTS, DEFAULT_WATCH_AIRPORTS),
        ): str,
        vol.Required(
            CONF_RAPID_DESCENT_FPM,
            default=defaults.get(CONF_RAPID_DESCENT_FPM, default_policy.rapid_descent_fpm),
        ): vol.All(vol.Coerce(float), vol.Range(min=-20000.0, max=-100.0)),
        vol.Required(
            CONF_RAPID_DESCENT_MIN_ALTITUDE_FT,
            default=defaults.get(
                CONF_RAPID_DESCENT_MIN_ALTITUDE_FT,
                default_policy.rapid_descent_min_altitude_ft,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=60000.0)),
        vol.Required(
            CONF_ORBIT_TRACK_RATE_DEGREES_PER_SECOND,
            default=defaults.get(
                CONF_ORBIT_TRACK_RATE_DEGREES_PER_SECOND,
                default_policy.orbit_track_rate_degrees_per_second,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=30.0)),
        vol.Required(
            CONF_ORBIT_MIN_GROUND_SPEED_KT,
            default=defaults.get(
                CONF_ORBIT_MIN_GROUND_SPEED_KT,
                default_policy.orbit_min_ground_speed_kt,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1000.0)),
        vol.Required(
            CONF_ORBIT_MAX_GROUND_SPEED_KT,
            default=defaults.get(
                CONF_ORBIT_MAX_GROUND_SPEED_KT,
                default_policy.orbit_max_ground_speed_kt,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1000.0)),
        vol.Required(
            CONF_TERMINAL_SUPPRESSION_ENABLED,
            default=defaults.get(
                CONF_TERMINAL_SUPPRESSION_ENABLED,
                default_policy.terminal_suppression_enabled,
            ),
        ): bool,
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
            CONF_BACKGROUND_INTERVAL_SECONDS,
            default=defaults.get(
                CONF_BACKGROUND_INTERVAL_SECONDS,
                DEFAULT_BACKGROUND_INTERVAL_SECONDS,
            ),
        ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
        vol.Required(
            CONF_ENABLE_ENRICHMENT,
            default=defaults.get(CONF_ENABLE_ENRICHMENT, True),
        ): bool,
        vol.Required(
            CONF_COLLECT_MAPPING_REVIEW,
            default=defaults.get(CONF_COLLECT_MAPPING_REVIEW, DEFAULT_COLLECT_MAPPING_REVIEW),
        ): bool,
        vol.Optional(
            CONF_ADSBDB_BASE_URL,
            default=defaults.get(
                CONF_ADSBDB_BASE_URL,
                DEFAULT_RUNTIME_SETTINGS.providers.adsbdb_base_url,
            ),
        ): str,
        vol.Optional(
            CONF_HEXDB_BASE_URL,
            default=defaults.get(
                CONF_HEXDB_BASE_URL,
                DEFAULT_RUNTIME_SETTINGS.providers.hexdb_base_url,
            ),
        ): str,
        vol.Optional(
            CONF_AIRPLANES_LIVE_BASE_URL,
            default=defaults.get(
                CONF_AIRPLANES_LIVE_BASE_URL,
                DEFAULT_RUNTIME_SETTINGS.providers.airplanes_live_base_url,
            ),
        ): str,
        vol.Optional(
            CONF_AIRPORT_DATA_BASE_URL,
            default=defaults.get(
                CONF_AIRPORT_DATA_BASE_URL,
                DEFAULT_RUNTIME_SETTINGS.providers.airport_data_base_url,
            ),
        ): str,
        vol.Optional(
            CONF_BUILT_YEAR_CACHE_SECONDS,
            default=defaults.get(
                CONF_BUILT_YEAR_CACHE_SECONDS,
                DEFAULT_RUNTIME_SETTINGS.providers.built_year_cache_seconds,
            ),
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=365 * 24 * 60 * 60)),
        vol.Optional(
            CONF_AIRPORT_BOARD_CACHE_SECONDS,
            default=defaults.get(
                CONF_AIRPORT_BOARD_CACHE_SECONDS,
                DEFAULT_RUNTIME_SETTINGS.providers.airport_board_cache_seconds,
            ),
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=86400)),
        vol.Optional(
            CONF_BATUMI_AIRPORT_BOARD_BASE_URL,
            default=defaults.get(
                CONF_BATUMI_AIRPORT_BOARD_BASE_URL,
                DEFAULT_RUNTIME_SETTINGS.providers.batumi_airport_board_base_url,
            ),
        ): str,
        vol.Optional(
            CONF_SPEECH_AIRLINE_OVERRIDES,
            default=defaults.get(CONF_SPEECH_AIRLINE_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_AIRLINE_ALIAS_OVERRIDES,
            default=defaults.get(CONF_SPEECH_AIRLINE_ALIAS_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_AIRPORT_CODE_FROM_OVERRIDES,
            default=defaults.get(CONF_SPEECH_AIRPORT_CODE_FROM_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_AIRPORT_CODE_TO_OVERRIDES,
            default=defaults.get(CONF_SPEECH_AIRPORT_CODE_TO_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_AIRPORT_CODE_ROUTE_OVERRIDES,
            default=defaults.get(CONF_SPEECH_AIRPORT_CODE_ROUTE_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_CITY_FROM_OVERRIDES,
            default=defaults.get(CONF_SPEECH_CITY_FROM_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_CITY_TO_OVERRIDES,
            default=defaults.get(CONF_SPEECH_CITY_TO_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_CITY_ROUTE_OVERRIDES,
            default=defaults.get(CONF_SPEECH_CITY_ROUTE_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_CALLSIGN_PREFIX_OVERRIDES,
            default=defaults.get(CONF_SPEECH_CALLSIGN_PREFIX_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_SPEECH_MODEL_OVERRIDES,
            default=defaults.get(CONF_SPEECH_MODEL_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_ROUTE_AIRLINE_PREFIX_OVERRIDES,
            default=defaults.get(CONF_ROUTE_AIRLINE_PREFIX_OVERRIDES, "{}"),
        ): str,
        vol.Optional(
            CONF_ROUTE_CALLSIGN_OVERRIDES,
            default=defaults.get(CONF_ROUTE_CALLSIGN_OVERRIDES, "{}"),
        ): str,
        vol.Required(
            CONF_ENRICHMENT_TIMEOUT_SECONDS,
            default=defaults.get(
                CONF_ENRICHMENT_TIMEOUT_SECONDS,
                DEFAULT_ENRICHMENT_TIMEOUT_SECONDS,
            ),
        ): vol.Coerce(float),
        vol.Required(
            CONF_PREFETCH_LIMIT,
            default=defaults.get(CONF_PREFETCH_LIMIT, DEFAULT_PREFETCH_LIMIT),
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
        vol.Required(
            CONF_PREFETCH_BUDGET_SECONDS,
            default=defaults.get(
                CONF_PREFETCH_BUDGET_SECONDS,
                DEFAULT_PREFETCH_BUDGET_SECONDS,
            ),
        ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=60.0)),
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
