"""Runtime profile settings for Aircraft Window."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import timedelta, timezone, tzinfo
from typing import Any

from .const import (
    CONF_ADSBDB_BASE_URL,
    CONF_AIRPLANES_LIVE_BASE_URL,
    CONF_AIRPORT_BOARD_CACHE_SECONDS,
    CONF_AIRPORT_BOARD_PROVIDER,
    CONF_BATUMI_AIRPORT_BOARD_BASE_URL,
    CONF_DAY_HUMAN_VISIBLE_RADIUS_KM,
    CONF_HEXDB_BASE_URL,
    CONF_LOCAL_AIRPORT_IATA,
    CONF_LOCAL_AIRPORT_NAME,
    CONF_LOCAL_TIMEZONE_OFFSET_HOURS,
    CONF_LOW_LIGHT_HUMAN_VISIBLE_RADIUS_KM,
    CONF_NIGHT_HUMAN_VISIBLE_RADIUS_KM,
    CONF_ORBIT_MAX_GROUND_SPEED_KT,
    CONF_ORBIT_MIN_GROUND_SPEED_KT,
    CONF_ORBIT_TRACK_RATE_DEGREES_PER_SECOND,
    CONF_RAPID_DESCENT_FPM,
    CONF_RAPID_DESCENT_MIN_ALTITUDE_FT,
    CONF_ROUTE_AIRLINE_PREFIX_OVERRIDES,
    CONF_ROUTE_CALLSIGN_OVERRIDES,
    CONF_RUNWAY_STAGING_LATITUDE,
    CONF_RUNWAY_STAGING_LONGITUDE,
    CONF_RUNWAY_STAGING_MAX_ALTITUDE_FT,
    CONF_RUNWAY_STAGING_MAX_SPEED_KT,
    CONF_RUNWAY_STAGING_RADIUS_KM,
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
)
from .route_fallbacks import DEFAULT_ROUTE_FALLBACKS, RouteFallbacks
from .speech_ru import DEFAULT_RUSSIAN_SPEECH_PACK, RussianSpeechPack

BATUMI_WINDOW_VIEW_POLYGON_LON_LAT = (
    (41.5906258, 41.6211806),
    (41.5759385, 41.6106128),
    (40.5297019, 40.8787998),
    (37.6439069, 39.8782721),
    (30.1070473, 40.9740093),
    (30.5487884, 46.1944223),
    (41.4123703, 45.3912115),
    (42.0420538, 42.0792269),
)


@dataclass(frozen=True, slots=True)
class RunwayStagingArea:
    """Airport ground/staging area that should preopen the curtain."""

    latitude: float
    longitude: float
    radius_km: float
    max_altitude_ft: float
    max_speed_kt: float


@dataclass(frozen=True, slots=True)
class TerminalArea:
    """Routine terminal area where expected turns/descents are not special."""

    latitude: float
    longitude: float
    radius_km: float
    max_altitude_ft: float


@dataclass(frozen=True, slots=True)
class LocalAirportProfile:
    """Configured local airport and optional board provider context."""

    iata: str
    name: str
    timezone: tzinfo
    board_provider: str = ""
    terminal_area: TerminalArea | None = None
    runway_staging_areas: tuple[RunwayStagingArea, ...] = ()


@dataclass(frozen=True, slots=True)
class WindowViewProfile:
    """Observer window geometry and practical visibility limits."""

    lead_seconds: float
    projection_step_seconds: float
    default_radius_km: float
    day_radius_km: float
    low_light_radius_km: float
    night_radius_km: float
    azimuth_degrees: float
    half_angle_degrees: float
    polygon_lon_lat: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class WatchAirport:
    """Route endpoint that should become a special observation candidate."""

    iata: str
    phase: str
    reason_label: str


@dataclass(frozen=True, slots=True)
class WatchPolicy:
    """Configurable special-interest thresholds and watched route endpoints."""

    rapid_descent_fpm: float
    rapid_descent_min_altitude_ft: float
    orbit_track_rate_degrees_per_second: float
    orbit_min_ground_speed_kt: float
    orbit_max_ground_speed_kt: float
    terminal_suppression_enabled: bool
    watch_airports: tuple[WatchAirport, ...] = ()

    def airport(self, iata: str) -> WatchAirport | None:
        """Return the configured watch airport for an IATA code."""
        token = iata.strip().upper()
        for airport in self.watch_airports:
            if airport.iata.upper() == token:
                return airport
        return None

    def airport_phase(self, phase: str) -> WatchAirport | None:
        """Return the configured watch airport for a classifier phase."""
        token = phase.strip()
        for airport in self.watch_airports:
            if airport.phase == token:
                return airport
        return None


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    """External enrichment and airport board provider defaults."""

    adsbdb_base_url: str
    hexdb_base_url: str
    airplanes_live_base_url: str
    airport_board_cache_seconds: int
    batumi_airport_board_base_url: str
    batumi_airport_board_legs: dict[str, str]


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Resolved runtime settings for one Aircraft Window entry."""

    local_airport: LocalAirportProfile
    window_view: WindowViewProfile
    watch_policy: WatchPolicy
    providers: ProviderSettings
    speech_pack: RussianSpeechPack
    model_speech_overrides: dict[str, str]
    route_fallbacks: RouteFallbacks


DEFAULT_BATUMI_RUNWAY_STAGING_AREA = RunwayStagingArea(
    latitude=41.6103,
    longitude=41.6004,
    radius_km=3.0,
    max_altitude_ft=500.0,
    max_speed_kt=45.0,
)

DEFAULT_BATUMI_TERMINAL_AREA = TerminalArea(
    latitude=DEFAULT_BATUMI_RUNWAY_STAGING_AREA.latitude,
    longitude=DEFAULT_BATUMI_RUNWAY_STAGING_AREA.longitude,
    radius_km=55.0,
    max_altitude_ft=10000.0,
)

DEFAULT_RUNTIME_SETTINGS = RuntimeSettings(
    local_airport=LocalAirportProfile(
        iata="BUS",
        name="Batumi",
        timezone=timezone(timedelta(hours=4)),
        board_provider="batumi_airport_board",
        terminal_area=DEFAULT_BATUMI_TERMINAL_AREA,
        runway_staging_areas=(DEFAULT_BATUMI_RUNWAY_STAGING_AREA,),
    ),
    window_view=WindowViewProfile(
        lead_seconds=240.0,
        projection_step_seconds=15.0,
        default_radius_km=80.0,
        day_radius_km=12.0,
        low_light_radius_km=35.0,
        night_radius_km=45.0,
        azimuth_degrees=290.0,
        half_angle_degrees=90.0,
        polygon_lon_lat=BATUMI_WINDOW_VIEW_POLYGON_LON_LAT,
    ),
    watch_policy=WatchPolicy(
        rapid_descent_fpm=-3500.0,
        rapid_descent_min_altitude_ft=1000.0,
        orbit_track_rate_degrees_per_second=2.5,
        orbit_min_ground_speed_kt=60.0,
        orbit_max_ground_speed_kt=260.0,
        terminal_suppression_enabled=True,
        watch_airports=(
            WatchAirport(
                iata="KUT",
                phase="kutaisi_route",
                reason_label="route includes KUT",
            ),
        ),
    ),
    providers=ProviderSettings(
        adsbdb_base_url="https://api.adsbdb.com/v0",
        hexdb_base_url="https://hexdb.io/api/v1",
        airplanes_live_base_url="https://api.airplanes.live/v2",
        airport_board_cache_seconds=5 * 60,
        batumi_airport_board_base_url="https://batumiairport.com/Home/searchFlights",
        batumi_airport_board_legs={
            "DEPARTURE": "/en-EN/flights/departure-flights",
            "ARRIVAL": "/en-EN/flights/arrival-flights",
        },
    ),
    speech_pack=DEFAULT_RUSSIAN_SPEECH_PACK,
    model_speech_overrides={},
    route_fallbacks=DEFAULT_ROUTE_FALLBACKS,
)


def _float_option(options: dict[str, Any], key: str, default: float) -> float:
    """Return a finite float option or its default."""
    try:
        value = float(options.get(key, default))
    except (TypeError, ValueError):
        return default
    return value


def _int_option(options: dict[str, Any], key: str, default: int) -> int:
    """Return an integer option or its default."""
    try:
        return int(options.get(key, default))
    except (TypeError, ValueError):
        return default


def _base_url_option(options: dict[str, Any], key: str, default: str) -> str:
    """Return a base URL option, normalized for path joins."""
    value = str(options.get(key, default) or "").strip()
    if not value:
        return default
    return value.rstrip("/")


def _json_polygon_option(
    options: dict[str, Any],
    key: str,
    default: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    """Parse a JSON lon/lat polygon option or return the supplied default."""
    raw = options.get(key, "")
    if raw in (None, ""):
        return default
    if isinstance(raw, list):
        parsed = raw
    else:
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return default
    if not isinstance(parsed, list):
        return default
    if not parsed:
        return ()
    points: list[tuple[float, float]] = []
    for item in parsed:
        if isinstance(item, dict):
            raw_lon = item.get("lon", item.get("longitude"))
            raw_lat = item.get("lat", item.get("latitude"))
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            raw_lon, raw_lat = item
        else:
            return default
        try:
            lon = float(raw_lon)
            lat = float(raw_lat)
        except (TypeError, ValueError):
            return default
        if (
            not math.isfinite(lon)
            or not math.isfinite(lat)
            or not -180.0 <= lon <= 180.0
            or not -90.0 <= lat <= 90.0
        ):
            return default
        points.append((lon, lat))
    if len(points) < 3:
        return default
    return tuple(points)


def _watch_airports_from_option(value: Any) -> tuple[WatchAirport, ...]:
    """Parse a comma-separated watched-airport list."""
    airports: list[WatchAirport] = []
    seen: set[str] = set()
    for raw_token in str(value or "").split(","):
        iata = raw_token.strip().upper()
        if not iata or iata in seen:
            continue
        if not (3 <= len(iata) <= 4 and iata.isalnum()):
            continue
        seen.add(iata)
        phase = f"{iata.lower()}_route"
        if iata == "KUT":
            phase = "kutaisi_route"
        airports.append(
            WatchAirport(
                iata=iata,
                phase=phase,
                reason_label=f"route includes {iata}",
            )
        )
    return tuple(airports)


def _json_string_map_option(options: dict[str, Any], key: str) -> dict[str, str]:
    """Parse a JSON object option into a string-to-string mapping."""
    raw = options.get(key, "")
    if raw in (None, ""):
        return {}
    if isinstance(raw, dict):
        parsed = raw
    else:
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, str] = {}
    for raw_key, raw_value in parsed.items():
        item_key = str(raw_key).strip()
        item_value = str(raw_value).strip()
        if item_key and item_value:
            result[item_key] = item_value
    return result


def _json_route_map_option(options: dict[str, Any], key: str) -> dict[str, dict[str, str]]:
    """Parse a JSON object option into callsign-to-route fallback mappings."""
    raw = options.get(key, "")
    if raw in (None, ""):
        return {}
    if isinstance(raw, dict):
        parsed = raw
    else:
        try:
            parsed = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    if not isinstance(parsed, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for raw_callsign, raw_route in parsed.items():
        callsign = str(raw_callsign).strip().replace(" ", "").upper()
        if not callsign or not isinstance(raw_route, dict):
            continue
        route = {
            str(route_key).strip(): str(route_value).strip()
            for route_key, route_value in raw_route.items()
            if str(route_key).strip() and str(route_value).strip()
        }
        if route:
            result[callsign] = route
    return result


def _route_fallbacks_from_options(options: dict[str, Any]) -> RouteFallbacks:
    """Return built-in route fallbacks plus user-maintained overrides."""
    prefix_overrides = {
        key.upper(): value
        for key, value in _json_string_map_option(
            options,
            CONF_ROUTE_AIRLINE_PREFIX_OVERRIDES,
        ).items()
    }
    return DEFAULT_ROUTE_FALLBACKS.with_overrides(
        airline_by_callsign_prefix=prefix_overrides,
        route_by_callsign=_json_route_map_option(options, CONF_ROUTE_CALLSIGN_OVERRIDES),
    )


def _provider_settings_from_options(options: dict[str, Any]) -> ProviderSettings:
    """Return external provider settings with user-maintained overrides."""
    defaults = DEFAULT_RUNTIME_SETTINGS.providers
    return ProviderSettings(
        adsbdb_base_url=_base_url_option(
            options,
            CONF_ADSBDB_BASE_URL,
            defaults.adsbdb_base_url,
        ),
        hexdb_base_url=_base_url_option(
            options,
            CONF_HEXDB_BASE_URL,
            defaults.hexdb_base_url,
        ),
        airplanes_live_base_url=_base_url_option(
            options,
            CONF_AIRPLANES_LIVE_BASE_URL,
            defaults.airplanes_live_base_url,
        ),
        airport_board_cache_seconds=max(
            0,
            _int_option(
                options,
                CONF_AIRPORT_BOARD_CACHE_SECONDS,
                defaults.airport_board_cache_seconds,
            ),
        ),
        batumi_airport_board_base_url=_base_url_option(
            options,
            CONF_BATUMI_AIRPORT_BOARD_BASE_URL,
            defaults.batumi_airport_board_base_url,
        ),
        batumi_airport_board_legs=defaults.batumi_airport_board_legs,
    )


def _model_speech_overrides_from_options(options: dict[str, Any]) -> dict[str, str]:
    """Parse user-maintained aircraft model/type speech overrides."""
    return {
        " ".join(key.upper().split()): value
        for key, value in _json_string_map_option(
            options,
            CONF_SPEECH_MODEL_OVERRIDES,
        ).items()
    }


def _city_speech_key(value: str) -> str:
    """Return the city speech lookup key used by route labels."""
    label = value.split("(")[0].replace("-", " ").strip()
    return " ".join(label.split()).title()


def _city_speech_overrides_from_options(
    options: dict[str, Any],
    key: str,
) -> dict[str, str]:
    """Parse user-maintained airport city speech overrides."""
    return {
        _city_speech_key(item_key): value
        for item_key, value in _json_string_map_option(options, key).items()
    }


def _speech_pack_from_options(options: dict[str, Any]) -> RussianSpeechPack:
    """Return the built-in Russian speech pack plus user-maintained overrides."""
    airline_aliases = {
        key.casefold(): value
        for key, value in _json_string_map_option(
            options,
            CONF_SPEECH_AIRLINE_ALIAS_OVERRIDES,
        ).items()
    }
    upper_code_keys = (
        CONF_SPEECH_AIRPORT_CODE_FROM_OVERRIDES,
        CONF_SPEECH_AIRPORT_CODE_TO_OVERRIDES,
        CONF_SPEECH_AIRPORT_CODE_ROUTE_OVERRIDES,
        CONF_SPEECH_CALLSIGN_PREFIX_OVERRIDES,
    )
    normalized_maps = {
        key: {
            item_key.upper(): value
            for item_key, value in _json_string_map_option(options, key).items()
        }
        for key in upper_code_keys
    }
    return DEFAULT_RUSSIAN_SPEECH_PACK.with_overrides(
        city_from=_city_speech_overrides_from_options(
            options,
            CONF_SPEECH_CITY_FROM_OVERRIDES,
        ),
        city_to=_city_speech_overrides_from_options(
            options,
            CONF_SPEECH_CITY_TO_OVERRIDES,
        ),
        city_route=_city_speech_overrides_from_options(
            options,
            CONF_SPEECH_CITY_ROUTE_OVERRIDES,
        ),
        airline=_json_string_map_option(options, CONF_SPEECH_AIRLINE_OVERRIDES),
        airline_aliases=airline_aliases,
        airport_code_from=normalized_maps[CONF_SPEECH_AIRPORT_CODE_FROM_OVERRIDES],
        airport_code_to=normalized_maps[CONF_SPEECH_AIRPORT_CODE_TO_OVERRIDES],
        airport_code_route=normalized_maps[CONF_SPEECH_AIRPORT_CODE_ROUTE_OVERRIDES],
        callsign_prefix=normalized_maps[CONF_SPEECH_CALLSIGN_PREFIX_OVERRIDES],
    )


def runtime_settings_from_options(options: dict[str, Any]) -> RuntimeSettings:
    """Build runtime settings from config entry data and options."""
    defaults = DEFAULT_RUNTIME_SETTINGS
    default_airport = defaults.local_airport
    default_view = defaults.window_view
    default_staging = default_airport.runway_staging_areas[0]
    default_terminal = default_airport.terminal_area
    assert default_terminal is not None

    local_iata = str(
        options.get(CONF_LOCAL_AIRPORT_IATA, default_airport.iata)
        or default_airport.iata
    ).strip().upper()
    local_name = str(
        options.get(CONF_LOCAL_AIRPORT_NAME, default_airport.name)
        or default_airport.name
    ).strip()
    board_provider_default = (
        default_airport.board_provider if local_iata == default_airport.iata.upper() else ""
    )
    board_provider = str(
        options.get(CONF_AIRPORT_BOARD_PROVIDER, board_provider_default) or ""
    ).strip()
    timezone_offset_hours = _float_option(
        options,
        CONF_LOCAL_TIMEZONE_OFFSET_HOURS,
        default_airport.timezone.utcoffset(None).total_seconds() / 3600.0,
    )
    default_polygon = (
        default_view.polygon_lon_lat if local_iata == default_airport.iata.upper() else ()
    )

    runway_staging = RunwayStagingArea(
        latitude=_float_option(
            options,
            CONF_RUNWAY_STAGING_LATITUDE,
            default_staging.latitude,
        ),
        longitude=_float_option(
            options,
            CONF_RUNWAY_STAGING_LONGITUDE,
            default_staging.longitude,
        ),
        radius_km=_float_option(
            options,
            CONF_RUNWAY_STAGING_RADIUS_KM,
            default_staging.radius_km,
        ),
        max_altitude_ft=_float_option(
            options,
            CONF_RUNWAY_STAGING_MAX_ALTITUDE_FT,
            default_staging.max_altitude_ft,
        ),
        max_speed_kt=_float_option(
            options,
            CONF_RUNWAY_STAGING_MAX_SPEED_KT,
            default_staging.max_speed_kt,
        ),
    )
    terminal_area = TerminalArea(
        latitude=_float_option(
            options,
            CONF_TERMINAL_AREA_LATITUDE,
            default_terminal.latitude,
        ),
        longitude=_float_option(
            options,
            CONF_TERMINAL_AREA_LONGITUDE,
            default_terminal.longitude,
        ),
        radius_km=_float_option(
            options,
            CONF_TERMINAL_AREA_RADIUS_KM,
            default_terminal.radius_km,
        ),
        max_altitude_ft=_float_option(
            options,
            CONF_TERMINAL_AREA_MAX_ALTITUDE_FT,
            default_terminal.max_altitude_ft,
        ),
    )
    window_view = WindowViewProfile(
        lead_seconds=_float_option(
            options,
            CONF_WINDOW_VIEW_LEAD_SECONDS,
            default_view.lead_seconds,
        ),
        projection_step_seconds=_float_option(
            options,
            CONF_WINDOW_VIEW_PROJECTION_STEP_SECONDS,
            default_view.projection_step_seconds,
        ),
        default_radius_km=_float_option(
            options,
            CONF_WINDOW_VIEW_RADIUS_KM,
            default_view.default_radius_km,
        ),
        day_radius_km=_float_option(
            options,
            CONF_DAY_HUMAN_VISIBLE_RADIUS_KM,
            default_view.day_radius_km,
        ),
        low_light_radius_km=_float_option(
            options,
            CONF_LOW_LIGHT_HUMAN_VISIBLE_RADIUS_KM,
            default_view.low_light_radius_km,
        ),
        night_radius_km=_float_option(
            options,
            CONF_NIGHT_HUMAN_VISIBLE_RADIUS_KM,
            default_view.night_radius_km,
        ),
        azimuth_degrees=_float_option(
            options,
            CONF_WINDOW_VIEW_AZIMUTH_DEGREES,
            default_view.azimuth_degrees,
        ),
        half_angle_degrees=_float_option(
            options,
            CONF_WINDOW_VIEW_HALF_ANGLE_DEGREES,
            default_view.half_angle_degrees,
        ),
        polygon_lon_lat=_json_polygon_option(
            options,
            CONF_WINDOW_VIEW_POLYGON_JSON,
            default_polygon,
        ),
    )
    watch_airports = _watch_airports_from_option(
        options.get(
            CONF_WATCH_AIRPORTS,
            ",".join(airport.iata for airport in defaults.watch_policy.watch_airports),
        )
    )
    return RuntimeSettings(
        local_airport=LocalAirportProfile(
            iata=local_iata,
            name=local_name,
            timezone=timezone(timedelta(hours=timezone_offset_hours)),
            board_provider=board_provider,
            terminal_area=terminal_area,
            runway_staging_areas=(runway_staging,),
        ),
        window_view=window_view,
        watch_policy=WatchPolicy(
            rapid_descent_fpm=_float_option(
                options,
                CONF_RAPID_DESCENT_FPM,
                defaults.watch_policy.rapid_descent_fpm,
            ),
            rapid_descent_min_altitude_ft=_float_option(
                options,
                CONF_RAPID_DESCENT_MIN_ALTITUDE_FT,
                defaults.watch_policy.rapid_descent_min_altitude_ft,
            ),
            orbit_track_rate_degrees_per_second=_float_option(
                options,
                CONF_ORBIT_TRACK_RATE_DEGREES_PER_SECOND,
                defaults.watch_policy.orbit_track_rate_degrees_per_second,
            ),
            orbit_min_ground_speed_kt=_float_option(
                options,
                CONF_ORBIT_MIN_GROUND_SPEED_KT,
                defaults.watch_policy.orbit_min_ground_speed_kt,
            ),
            orbit_max_ground_speed_kt=_float_option(
                options,
                CONF_ORBIT_MAX_GROUND_SPEED_KT,
                defaults.watch_policy.orbit_max_ground_speed_kt,
            ),
            terminal_suppression_enabled=bool(
                options.get(
                    CONF_TERMINAL_SUPPRESSION_ENABLED,
                    defaults.watch_policy.terminal_suppression_enabled,
                )
            ),
            watch_airports=watch_airports,
        ),
        providers=_provider_settings_from_options(options),
        speech_pack=_speech_pack_from_options(options),
        model_speech_overrides=_model_speech_overrides_from_options(options),
        route_fallbacks=_route_fallbacks_from_options(options),
    )
