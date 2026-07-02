"""Runtime profile settings for Aircraft Window."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta, timezone, tzinfo

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
)
