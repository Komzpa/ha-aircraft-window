"""Coordinator for Aircraft Window."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_BACKGROUND_INTERVAL_SECONDS,
    CONF_COLLECT_MAPPING_REVIEW,
    CONF_DUMP1090_URL,
    CONF_ENABLE_ENRICHMENT,
    CONF_ENRICHMENT_TIMEOUT_SECONDS,
    CONF_HOME_LATITUDE,
    CONF_HOME_LONGITUDE,
    CONF_MAX_APPROACH_ALTITUDE_FT,
    CONF_MAX_APPROACH_DISTANCE_KM,
    CONF_MAX_NO_POSITION_SEEN_SECONDS,
    CONF_MAX_POSITIONED_DISTANCE_KM,
    CONF_PREFETCH_BUDGET_SECONDS,
    CONF_PREFETCH_LIMIT,
    CONF_SCAN_INTERVAL_SECONDS,
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
    EVENT_CANDIDATE,
    SCHEDULED_PREOPEN_AFTER_SECONDS,
    SCHEDULED_PREOPEN_BEFORE_SECONDS,
)
from .logic import (
    KNOWN_BUILT_YEAR_BY_REGISTRATION,
    AircraftCandidate,
    airline_speech,
    airport_label,
    airport_speech,
    backfill_position_from_history,
    build_followup_announcement,
    candidate_airframe_key,
    candidate_has_real_flight,
    classify_service_type,
    extract_airport_data_year,
    flight_label,
    has_aircraft_model_speech_mapping,
    has_airline_speech_mapping,
    has_airport_speech_mapping,
    has_callsign_prefix_speech_mapping,
    has_route_details,
    idle_candidate,
    interest_candidate,
    known_airline_for_callsign,
    known_route_for_callsign,
    make_key,
    movement_family,
    normalized_airport_city,
    parse_float,
    pick_candidate,
    spoken_flight,
    spoken_model,
    spoken_year,
    tts_cyrillic_text,
    window_view_attrs,
)
from .settings import DEFAULT_RUNTIME_SETTINGS, RuntimeSettings, runtime_settings_from_options

_LOGGER = logging.getLogger(__name__)

ADSBDB_BASE_URL = DEFAULT_RUNTIME_SETTINGS.providers.adsbdb_base_url
HEXDB_BASE_URL = DEFAULT_RUNTIME_SETTINGS.providers.hexdb_base_url
AIRPLANES_LIVE_BASE_URL = DEFAULT_RUNTIME_SETTINGS.providers.airplanes_live_base_url
LOCAL_AIRPORT_IATA = DEFAULT_RUNTIME_SETTINGS.local_airport.iata
ROUTE_CACHE_SECONDS = 6 * 60 * 60
AIRCRAFT_CACHE_SECONDS = 24 * 60 * 60
BUILT_YEAR_CACHE_SECONDS = 30 * 24 * 60 * 60
AIRPORT_BOARD_CACHE_SECONDS = DEFAULT_RUNTIME_SETTINGS.providers.airport_board_cache_seconds
ROUTINE_HEX_HOLD_SECONDS = 10.0
ROUTINE_HEX_HOLD_SUPPRESSION_REASON = "waiting briefly for callsign"
BATUMI_AIRPORT_BOARD_BASE_URL = (
    DEFAULT_RUNTIME_SETTINGS.providers.batumi_airport_board_base_url
)
TBILISI_TIMEZONE = DEFAULT_RUNTIME_SETTINGS.local_airport.timezone
BATUMI_AIRPORT_BOARD_LEGS = DEFAULT_RUNTIME_SETTINGS.providers.batumi_airport_board_legs
EXTERNAL_LOOKUP_ERROR_CACHE_SECONDS = 10 * 60
MIN_EXTERNAL_LOOKUP_TIMEOUT_SECONDS = 0.25
MAPPING_REVIEW_CACHE_KEY = "mapping_review:v1"
MAPPING_REVIEW_MAX_ITEMS = 80
MAPPING_REVIEW_VISIBLE_LIMIT = 24


def _cache_entry_ttl_seconds(key: str, entry: dict[str, Any]) -> int | None:
    """Return the effective TTL for a persistent cache entry."""
    if key == MAPPING_REVIEW_CACHE_KEY:
        return None
    if key.startswith("batumi-airport-board:"):
        return AIRPORT_BOARD_CACHE_SECONDS
    if key.startswith("airport-data-year:"):
        return BUILT_YEAR_CACHE_SECONDS
    if entry.get("error") is True:
        return EXTERNAL_LOOKUP_ERROR_CACHE_SECONDS
    if key.startswith("callsign:"):
        return ROUTE_CACHE_SECONDS
    if key.startswith(("aircraft:", "hexdb-aircraft:", "airplanes-live-aircraft:")):
        return AIRCRAFT_CACHE_SECONDS
    return None


def _prune_expired_cache_entries(cache: dict[str, Any], *, now: int | None = None) -> int:
    """Remove expired known cache entries in-place and return the removal count."""
    current_time = int(time.time()) if now is None else now
    expired: list[str] = []
    for key, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        ttl_seconds = _cache_entry_ttl_seconds(key, entry)
        if ttl_seconds is None:
            continue
        try:
            fetched_at = int(entry.get("fetched_at", 0))
        except (TypeError, ValueError):
            fetched_at = 0
        if fetched_at <= 0 or current_time - fetched_at >= ttl_seconds:
            expired.append(key)
    for key in expired:
        cache.pop(key, None)
    return len(expired)


def _prefetch_score(row: dict[str, Any]) -> tuple[int, float, float, str]:
    """Return a priority score for receiver-wide background enrichment."""
    flight = flight_label(row).replace(" ", "").upper()
    hex_id = str(row.get("hex") or "").strip().upper()
    seen = parse_float(row.get("seen"))
    seen_pos = parse_float(row.get("seen_pos"))
    altitude = parse_float(row.get("alt_baro"))
    if altitude is None:
        altitude = parse_float(row.get("alt_geom"))
    rssi = parse_float(row.get("rssi"))
    messages = parse_float(row.get("messages")) or 0.0

    score = 0
    if hex_id:
        score += 20
    if flight and flight != "UNKNOWN" and flight != hex_id:
        score += 40
    if row.get("lat") is not None and row.get("lon") is not None:
        score += 10
    if seen is not None and seen <= 10:
        score += 8
    if seen_pos is not None and seen_pos <= 30:
        score += 5
    if altitude is not None and altitude != 0 and altitude <= 12000:
        score += 6
    if rssi is not None and rssi >= -12:
        score += 4
    if messages >= 20:
        score += 2
    freshness = 999.0 if seen is None else seen
    low_altitude = 999999.0 if altitude is None else altitude
    return (score, -freshness, -messages, f"{flight}:{hex_id}:{low_altitude}")


def _select_prefetch_rows(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Return receiver rows worth warming, sorted independently of dump1090 order."""
    candidates = [
        row
        for row in rows
        if str(row.get("hex") or "").strip()
        and row.get("alt_baro") != "ground"
        and row.get("alt_geom") != "ground"
    ]
    candidates.sort(key=_prefetch_score, reverse=True)
    return candidates if limit == 0 else candidates[:limit]


def _mapping_review_airport_value(name: str, code: str) -> str:
    """Return a compact airport review label without duplicating the IATA code."""
    if code and name and f"({code})" not in name.upper():
        return f"{name} ({code})"
    return name or code


CALLSIGN_PREFIX_TO_BOARD_AIRLINE = {
    "AIZ": "IZ",
    "AHY": "J2",
    "BRU": "B2",
    "ELY": "LY",
    "FDB": "FZ",
    "FIA": "3F",
    "FIE": "3F",
    "ISR": "6H",
    "PGT": "PC",
    "RWZ": "WZ",
    "THY": "TK",
    "TGZ": "A9",
    "VAA": "V9",
    "WZZ": "W6",
}


@dataclass(slots=True)
class AircraftWindowRuntimeData:
    """Runtime data for one Aircraft Window config entry."""

    candidate: AircraftWindowCoordinator
    enrichment_prefetch: EnrichmentPrefetchCoordinator

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize both coordinators with shared cache ownership."""
        self.candidate = AircraftWindowCoordinator(hass, entry)
        self.enrichment_prefetch = EnrichmentPrefetchCoordinator(
            hass,
            entry,
            self.candidate,
        )


class AircraftWindowCoordinator(DataUpdateCoordinator[AircraftCandidate]):
    """Fetch and classify aircraft data."""

    _EMERGENCY_SQUAWK_CONFIRM_SECONDS = 30.0
    _EMERGENCY_SQUAWK_CONFIRM_SNAPSHOTS = 2
    _EMERGENCY_SQUAWK_CONFIRM_MESSAGE_DELTA = 1.0

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
        self._cache: dict[str, Any] | None = None
        self._last_event_key = ""
        self._last_announced_by_airframe: dict[str, AircraftCandidate] = {}
        self._announced_event_keys_by_airframe: dict[str, set[str]] = {}
        self._held_routine_hex_candidates: dict[str, float] = {}
        self._emergency_squawk_observations: dict[str, dict[str, float]] = {}
        options = self.options
        self._runtime_settings = runtime_settings_from_options(options)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=options.get(CONF_SCAN_INTERVAL_SECONDS, DEFAULT_SCAN_INTERVAL_SECONDS)
            ),
        )

    @property
    def options(self) -> dict[str, Any]:
        """Return merged config entry data and options."""
        merged = dict(self.entry.data)
        merged.update(self.entry.options)
        return merged

    @property
    def runtime_settings(self) -> RuntimeSettings:
        """Return resolved runtime profile settings for this entry."""
        return getattr(self, "_runtime_settings", DEFAULT_RUNTIME_SETTINGS)

    async def _async_update_data(self) -> AircraftCandidate:
        """Fetch aircraft data and return the best candidate."""
        options = self.options
        dump1090_url = options.get(CONF_DUMP1090_URL, DEFAULT_DUMP1090_URL)
        timeout = aiohttp.ClientTimeout(total=3)

        try:
            session = async_get_clientsession(self.hass)
            async with session.get(dump1090_url, timeout=timeout) as response:
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError) as exc:
            return idle_candidate(f"dump1090 unavailable: {exc}", source=dump1090_url)

        aircraft_rows = payload.get("aircraft")
        if not isinstance(aircraft_rows, list):
            return idle_candidate("dump1090 payload has no aircraft list", source=dump1090_url)
        aircraft_rows = [row for row in aircraft_rows if isinstance(row, dict)]

        # DataUpdateCoordinator expects the update method to do async work, so
        # enrichment is performed for the selected candidate after the pure
        # classifier picks it.
        base_candidate = pick_candidate(
            aircraft_rows,
            home_latitude=float(options.get(CONF_HOME_LATITUDE, self.hass.config.latitude)),
            home_longitude=float(options.get(CONF_HOME_LONGITUDE, self.hass.config.longitude)),
            max_positioned_distance_km=float(
                options.get(CONF_MAX_POSITIONED_DISTANCE_KM, DEFAULT_MAX_POSITIONED_DISTANCE_KM)
            ),
            max_approach_distance_km=float(
                options.get(CONF_MAX_APPROACH_DISTANCE_KM, DEFAULT_MAX_APPROACH_DISTANCE_KM)
            ),
            max_approach_altitude_ft=float(
                options.get(CONF_MAX_APPROACH_ALTITUDE_FT, DEFAULT_MAX_APPROACH_ALTITUDE_FT)
            ),
            max_no_position_seen_seconds=float(
                options.get(CONF_MAX_NO_POSITION_SEEN_SECONDS, DEFAULT_MAX_NO_POSITION_SEEN_SECONDS)
            ),
            source=dump1090_url,
            settings=self.runtime_settings,
        )
        if base_candidate.phase == "no_position_nearby":
            backfilled_rows = await self._async_backfill_no_position_rows(
                aircraft_rows,
                source=dump1090_url,
            )
            if backfilled_rows is not aircraft_rows:
                base_candidate = pick_candidate(
                    backfilled_rows,
                    home_latitude=float(
                        options.get(CONF_HOME_LATITUDE, self.hass.config.latitude)
                    ),
                    home_longitude=float(
                        options.get(CONF_HOME_LONGITUDE, self.hass.config.longitude)
                    ),
                    max_positioned_distance_km=float(
                        options.get(
                            CONF_MAX_POSITIONED_DISTANCE_KM,
                            DEFAULT_MAX_POSITIONED_DISTANCE_KM,
                        )
                    ),
                    max_approach_distance_km=float(
                        options.get(
                            CONF_MAX_APPROACH_DISTANCE_KM,
                            DEFAULT_MAX_APPROACH_DISTANCE_KM,
                        )
                    ),
                    max_approach_altitude_ft=float(
                        options.get(
                            CONF_MAX_APPROACH_ALTITUDE_FT,
                            DEFAULT_MAX_APPROACH_ALTITUDE_FT,
                        )
                    ),
                    max_no_position_seen_seconds=float(
                        options.get(
                            CONF_MAX_NO_POSITION_SEEN_SECONDS,
                            DEFAULT_MAX_NO_POSITION_SEEN_SECONDS,
                        )
                    ),
                    source=dump1090_url,
                    settings=self.runtime_settings,
                )
                aircraft_rows = backfilled_rows
        if base_candidate.active and options.get(CONF_ENABLE_ENRICHMENT, True):
            row = next(
                (
                    aircraft
                    for aircraft in aircraft_rows
                    if base_candidate.event_key == make_key(aircraft, base_candidate.phase)
                ),
                None,
            )
            if row is not None:
                enrichment = await self._async_enrich_aircraft(
                    row,
                    phase=base_candidate.phase,
                    cache_only=True,
                )
                if self._should_fetch_live_enrichment(row, base_candidate.phase, enrichment):
                    enrichment = await self._async_enrich_aircraft(
                        row,
                        phase=base_candidate.phase,
                        cache_only=False,
                        deadline=time.monotonic()
                        + float(
                            options.get(
                                CONF_ENRICHMENT_TIMEOUT_SECONDS,
                                DEFAULT_ENRICHMENT_TIMEOUT_SECONDS,
                            )
                        ),
                    )
                base_candidate = pick_candidate(
                    [row],
                    home_latitude=float(options.get(CONF_HOME_LATITUDE, self.hass.config.latitude)),
                    home_longitude=float(
                        options.get(CONF_HOME_LONGITUDE, self.hass.config.longitude)
                    ),
                    max_positioned_distance_km=float(
                        options.get(
                            CONF_MAX_POSITIONED_DISTANCE_KM,
                            DEFAULT_MAX_POSITIONED_DISTANCE_KM,
                        )
                    ),
                    max_approach_distance_km=float(
                        options.get(
                            CONF_MAX_APPROACH_DISTANCE_KM,
                            DEFAULT_MAX_APPROACH_DISTANCE_KM,
                        )
                    ),
                    max_approach_altitude_ft=float(
                        options.get(
                            CONF_MAX_APPROACH_ALTITUDE_FT,
                            DEFAULT_MAX_APPROACH_ALTITUDE_FT,
                        )
                    ),
                    max_no_position_seen_seconds=float(
                        options.get(
                            CONF_MAX_NO_POSITION_SEEN_SECONDS,
                            DEFAULT_MAX_NO_POSITION_SEEN_SECONDS,
                        )
                    ),
                    source=dump1090_url,
                    enrich=lambda _aircraft: enrichment,
                )

        special_candidate = await self._async_pick_interest_candidate(
            aircraft_rows,
            source=dump1090_url,
            enable_enrichment=bool(options.get(CONF_ENABLE_ENRICHMENT, True)),
        )
        if (
            special_candidate is not None
            and (
                not base_candidate.active
                or special_candidate.phase == "emergency_squawk"
                or (
                    special_candidate.phase == "military_visible"
                    and base_candidate.phase
                    not in {"positioned_landing", "positioned_takeoff", "positioned_approach"}
                    and special_candidate.confidence > base_candidate.confidence
                )
            )
        ):
            base_candidate = special_candidate

        if base_candidate.active:
            base_candidate = self._apply_routine_hex_announcement_hold(base_candidate)
            self._handle_candidate_event(base_candidate, apply_hold=False)
        elif not base_candidate.active:
            self._last_event_key = ""
            self._held_routine_hex_candidates.clear()
        return base_candidate

    def _should_fetch_live_enrichment(
        self,
        aircraft: dict[str, Any],
        phase: str,
        enrichment: dict[str, Any],
    ) -> bool:
        """Return true when a hot candidate can cheaply improve missing data."""
        if not self._airport_board_leg_for_phase(phase):
            return False
        flight = flight_label(aircraft).replace(" ", "").upper()
        hex_id = str(aircraft.get("hex") or "").strip().upper()
        real_flight = bool(flight and flight != "UNKNOWN" and not flight.startswith(hex_id))
        if real_flight and not has_route_details(enrichment):
            return True
        has_aircraft_identity = any(
            str(enrichment.get(key) or "").strip()
            for key in (
                "aircraft_model",
                "aircraft_type",
                "aircraft_model_speech",
                "registration",
                "registered_owner",
            )
        )
        return bool(hex_id and not has_aircraft_identity)

    def _handle_candidate_event(
        self,
        base_candidate: AircraftCandidate,
        *,
        apply_hold: bool = True,
    ) -> bool:
        """Fire a candidate event unless it is same-airframe routine churn."""
        if base_candidate.announcement_suppressed or not base_candidate.announcement.strip():
            return False

        if apply_hold and self._routine_hex_announcement_hold_active(base_candidate):
            return False

        airframe_key = candidate_airframe_key(base_candidate)
        announced_keys = self._announced_event_keys_by_airframe.setdefault(
            airframe_key,
            set(),
        )
        if base_candidate.event_key in announced_keys:
            previous = self._last_announced_by_airframe.get(airframe_key)
            if previous is not None:
                followup = build_followup_announcement(previous, base_candidate)
                if followup:
                    base_candidate.announcement = followup
                    base_candidate.announcement_kind = "followup"
                    self._last_announced_by_airframe[airframe_key] = base_candidate
                    self.hass.bus.async_fire(EVENT_CANDIDATE, base_candidate.as_dict())
                    self._last_event_key = base_candidate.event_key
                    return True
            return False

        should_fire = True
        previous = self._last_announced_by_airframe.get(airframe_key)
        if previous is not None:
            if movement_family(previous.phase) == movement_family(base_candidate.phase):
                followup = build_followup_announcement(previous, base_candidate)
                if followup:
                    base_candidate.announcement = followup
                    base_candidate.announcement_kind = "followup"
                else:
                    should_fire = False

        if should_fire:
            announced_keys.add(base_candidate.event_key)
            self._last_announced_by_airframe[airframe_key] = base_candidate
            self.hass.bus.async_fire(EVENT_CANDIDATE, base_candidate.as_dict())
            self._last_event_key = base_candidate.event_key
        return should_fire

    def _apply_routine_hex_announcement_hold(
        self,
        candidate: AircraftCandidate,
    ) -> AircraftCandidate:
        """Suppress sensor announcements while waiting briefly for a real callsign."""
        if not self._routine_hex_announcement_hold_active(candidate):
            return candidate
        return replace(
            candidate,
            announcement="",
            announcement_suppressed=True,
            announcement_suppression_reason=ROUTINE_HEX_HOLD_SUPPRESSION_REASON,
        )

    def _routine_hex_announcement_hold_active(self, candidate: AircraftCandidate) -> bool:
        """Return true when a weak hex-only routine announcement should wait."""
        airframe_key = candidate_airframe_key(candidate)
        held_candidates = getattr(self, "_held_routine_hex_candidates", None)
        if held_candidates is None:
            held_candidates = self._held_routine_hex_candidates = {}
        if self._should_hold_routine_hex_candidate(candidate):
            now = time.monotonic()
            first_seen = held_candidates.setdefault(airframe_key, now)
            if now - first_seen < ROUTINE_HEX_HOLD_SECONDS:
                return True
            held_candidates.pop(airframe_key, None)
            return False
        held_candidates.pop(airframe_key, None)
        return False

    def _should_hold_routine_hex_candidate(self, candidate: AircraftCandidate) -> bool:
        """Return true when a hex-only routine candidate should wait for callsign."""
        if candidate.phase not in {
            "positioned_approach",
            "positioned_landing",
            "positioned_takeoff",
            "positioned_runway_staging",
            "positioned_low_nearby",
        }:
            return False
        if candidate_has_real_flight(candidate):
            return False
        return not has_route_details(candidate.as_dict())

    async def _async_backfill_no_position_rows(
        self,
        aircraft_rows: list[dict[str, Any]],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        """Backfill missing live positions from local SkyAware history snapshots."""
        targets = [
            row
            for row in aircraft_rows
            if row.get("lat") is None
            and row.get("lon") is None
            and str(row.get("hex") or "").strip()
        ]
        if not targets:
            return aircraft_rows

        session = async_get_clientsession(self.hass)
        history_payloads: list[dict[str, Any]] = []
        started = time.monotonic()
        for index in range(120):
            if time.monotonic() - started > 0.8:
                break
            try:
                async with session.get(
                    self._history_url(source, index),
                    timeout=aiohttp.ClientTimeout(total=0.2),
                ) as response:
                    if response.status != 200:
                        continue
                    payload = await response.json()
            except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                history_payloads.append(payload)
        if not history_payloads:
            return aircraft_rows

        changed = False
        backfilled_rows: list[dict[str, Any]] = []
        for row in aircraft_rows:
            backfilled = backfill_position_from_history(row, history_payloads)
            changed = changed or backfilled is not row
            backfilled_rows.append(backfilled)
        return backfilled_rows if changed else aircraft_rows

    @staticmethod
    def _history_url(source: str, index: int) -> str:
        """Return the dump1090/SkyAware history URL next to aircraft.json."""
        parts = urlsplit(source)
        path = parts.path
        if path.endswith("/aircraft.json"):
            path = f"{path.removesuffix('/aircraft.json')}/history_{index}.json"
        else:
            path = f"/data/history_{index}.json"
        return urlunsplit((parts.scheme, parts.netloc, path, "", ""))

    async def _async_pick_interest_candidate(
        self,
        aircraft_rows: list[dict[str, Any]],
        *,
        source: str,
        enable_enrichment: bool,
    ) -> AircraftCandidate | None:
        """Return the best emergency, route, or military aircraft visible in the feed."""
        best: AircraftCandidate | None = None
        for aircraft in aircraft_rows:
            raw_candidate = interest_candidate(
                aircraft,
                enrichment={},
                source=source,
                aircraft_count=len(aircraft_rows),
                settings=self.runtime_settings,
            )
            if raw_candidate is None or raw_candidate.phase not in {
                "emergency_squawk",
                "special_interest",
            }:
                continue
            enrichment = (
                await self._async_enrich_aircraft(aircraft, cache_only=True)
                if enable_enrichment
                else {}
            )
            candidate = interest_candidate(
                aircraft,
                enrichment=enrichment,
                source=source,
                aircraft_count=len(aircraft_rows),
                settings=self.runtime_settings,
            )
            if (
                candidate is not None
                and candidate.phase == "emergency_squawk"
                and not self._emergency_squawk_confirmed(aircraft)
            ):
                continue
            if candidate is not None and (
                best is None or candidate.confidence > best.confidence
            ):
                best = candidate
        if not enable_enrichment:
            return best

        for aircraft in aircraft_rows[:12]:
            if interest_candidate(
                aircraft,
                enrichment={},
                source=source,
                aircraft_count=len(aircraft_rows),
                settings=self.runtime_settings,
            ) is not None:
                continue
            try:
                seen = float(aircraft.get("seen") or 999.0)
                seen_pos = (
                    None
                    if aircraft.get("seen_pos") is None
                    else float(aircraft.get("seen_pos") or 999.0)
                )
            except (TypeError, ValueError):
                continue
            if seen > 20.0 and (seen_pos is None or seen_pos > 60.0):
                continue
            enrichment = await self._async_enrich_aircraft(aircraft, cache_only=True)
            candidate = interest_candidate(
                aircraft,
                enrichment=enrichment,
                source=source,
                aircraft_count=len(aircraft_rows),
                settings=self.runtime_settings,
            )
            if candidate is not None and (
                best is None or candidate.confidence > best.confidence
            ):
                best = candidate
        return best

    def _emergency_squawk_confirmed(self, aircraft: dict[str, Any]) -> bool:
        """Return true after an emergency squawk persists across fresh snapshots."""
        squawk = str(aircraft.get("squawk") or "").strip().zfill(4)
        hex_id = str(aircraft.get("hex") or "").strip().lower()
        if not hex_id or squawk not in {"7500", "7600", "7700"}:
            return False

        now = time.monotonic()
        key = f"{hex_id}:{squawk}"
        messages = parse_float(aircraft.get("messages")) or 0.0
        observations = getattr(self, "_emergency_squawk_observations", None)
        if observations is None:
            observations = self._emergency_squawk_observations = {}

        stale_before = now - self._EMERGENCY_SQUAWK_CONFIRM_SECONDS
        for observed_key, observed in list(observations.items()):
            if observed.get("last_seen", 0.0) < stale_before:
                observations.pop(observed_key, None)

        observed = observations.get(key)
        if observed is None:
            observed = {
                "first_seen": now,
                "last_seen": now,
                "snapshots": 1.0,
                "first_messages": messages,
                "last_messages": messages,
            }
            observations[key] = observed
            return False

        observed["last_seen"] = now
        observed["snapshots"] = observed.get("snapshots", 0.0) + 1.0
        observed["last_messages"] = max(messages, observed.get("last_messages", 0.0))
        message_delta = observed["last_messages"] - observed.get("first_messages", messages)
        return (
            observed["snapshots"] >= self._EMERGENCY_SQUAWK_CONFIRM_SNAPSHOTS
            and message_delta >= self._EMERGENCY_SQUAWK_CONFIRM_MESSAGE_DELTA
        )

    async def _async_cache(self) -> dict[str, Any]:
        """Load persistent enrichment cache."""
        if self._cache is None:
            self._cache = await self._store.async_load() or {}
        return self._cache

    async def _async_save_cache(self) -> None:
        """Save persistent enrichment cache."""
        if self._cache is not None:
            _prune_expired_cache_entries(self._cache)
            await self._store.async_save(self._cache)

    async def _async_mapping_review_items(self) -> list[dict[str, Any]]:
        """Return persisted missing speech-mapping review items."""
        cache = await self._async_cache()
        items = cache.get(MAPPING_REVIEW_CACHE_KEY)
        return list(items) if isinstance(items, list) else []

    async def _async_record_mapping_review_items(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge newly seen speech-mapping review items into the persistent queue."""
        cache = await self._async_cache()
        existing = cache.get(MAPPING_REVIEW_CACHE_KEY)
        merged: dict[str, dict[str, Any]] = {}
        if isinstance(existing, list):
            for item in existing:
                if (
                    isinstance(item, dict)
                    and str(item.get("key") or "")
                    and self._mapping_review_item_still_unmapped(item)
                ):
                    merged[str(item["key"])] = dict(item)
        now = int(time.time())
        for item in items:
            key = str(item.get("key") or "")
            if not key:
                continue
            stored = merged.get(key, {})
            count = int(stored.get("count") or 0) + 1
            merged[key] = {
                **stored,
                **item,
                "count": count,
                "first_seen": int(stored.get("first_seen") or now),
                "last_seen": now,
            }
        sorted_items = sorted(
            merged.values(),
            key=lambda item: (int(item.get("last_seen") or 0), int(item.get("count") or 0)),
            reverse=True,
        )[:MAPPING_REVIEW_MAX_ITEMS]
        cache[MAPPING_REVIEW_CACHE_KEY] = sorted_items
        await self._async_save_cache()
        return sorted_items

    @staticmethod
    def _mapping_review_item_still_unmapped(item: dict[str, Any]) -> bool:
        """Return true if a persisted review item still needs a speech mapping."""
        kind = str(item.get("kind") or "")
        value = str(item.get("value") or "").strip()
        key = str(item.get("key") or "")
        if kind == "airline":
            return bool(value) and not has_airline_speech_mapping(value)
        if kind in {"origin_airport", "destination_airport", "route_airport"}:
            parts = key.split(":", 2)
            direction = parts[1] if len(parts) == 3 else "route"
            if direction not in {"from", "to", "route"}:
                direction = "route"
            lookup = parts[2] if len(parts) == 3 else ""
            code = lookup.upper() if re.fullmatch(r"[A-Za-z]{3,4}", lookup) else ""
            name = value.split("(")[0].strip()
            airport = {"iata_code": code, "municipality": name, "name": name}
            return not has_airport_speech_mapping(airport, direction=direction)
        if kind == "aircraft_model":
            return bool(value) and not has_aircraft_model_speech_mapping(value)
        if kind == "callsign_prefix":
            return bool(value) and not has_callsign_prefix_speech_mapping(value)
        return True

    def _mapping_review_items_for_visible_aircraft(
        self,
        aircraft: dict[str, Any],
        attrs: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return missing speech mappings for one currently visible aircraft row."""
        view = window_view_attrs(
            aircraft,
            home_latitude=float(
                self.options.get(CONF_HOME_LATITUDE, self.hass.config.latitude)
            ),
            home_longitude=float(
                self.options.get(CONF_HOME_LONGITUDE, self.hass.config.longitude)
            ),
            settings=self.runtime_settings,
        )
        if not (
            view.get("window_visible")
            or view.get("window_preopen_needed")
            or view.get("window_runway_staging")
        ):
            return []

        flight = flight_label(aircraft).replace(" ", "").upper()
        hex_id = str(aircraft.get("hex") or "").strip().upper()
        context = {
            "flight": flight,
            "hex": hex_id,
            "route_summary": str(attrs.get("route_summary") or ""),
            "window_view_reason": str(view.get("window_view_reason") or ""),
        }
        items: list[dict[str, Any]] = []

        airline_name = str(attrs.get("airline_name") or "").strip()
        if airline_name and not has_airline_speech_mapping(airline_name):
            items.append(
                {
                    "key": f"airline:{airline_name.casefold()}",
                    "kind": "airline",
                    "value": airline_name,
                    "fallback_speech": airline_speech(airline_name),
                    "suggested_table": "AIRLINE_SPEECH_RU",
                    **context,
                }
            )

        for direction, speech_direction in (("origin", "from"), ("destination", "to")):
            name = str(attrs.get(f"{direction}_name") or "").strip()
            code = str(attrs.get(f"{direction}_iata") or "").strip().upper()
            if not name and not code:
                continue
            airport = {"iata_code": code, "municipality": name, "name": name}
            if not has_airport_speech_mapping(airport, direction=speech_direction):
                value = _mapping_review_airport_value(name, code)
                review_key = code or normalized_airport_city(name)
                items.append(
                    {
                        "key": f"airport:{speech_direction}:{review_key}",
                        "kind": f"{direction}_airport",
                        "value": value,
                        "fallback_speech": airport_speech(
                            airport,
                            direction=speech_direction,
                        ),
                        "suggested_table": (
                            "AIRPORT_CODE_FROM_RU/CITY_FROM_RU"
                            if speech_direction == "from"
                            else "AIRPORT_CODE_TO_RU/CITY_TO_RU"
                        ),
                        **context,
                    }
                )
            if not has_airport_speech_mapping(airport, direction="route"):
                value = _mapping_review_airport_value(name, code)
                items.append(
                    {
                        "key": f"airport:route:{code or normalized_airport_city(name)}",
                        "kind": "route_airport",
                        "value": value,
                        "fallback_speech": tts_cyrillic_text(name or code),
                        "suggested_table": "AIRPORT_CODE_ROUTE_RU/CITY_ROUTE_RU",
                        **context,
                    }
                )

        model = str(attrs.get("aircraft_model") or "").strip()
        aircraft_type = str(attrs.get("aircraft_type") or "").strip()
        if model and not has_aircraft_model_speech_mapping(model, aircraft_type):
            items.append(
                {
                    "key": f"model:{aircraft_type or model}".casefold(),
                    "kind": "aircraft_model",
                    "value": " ".join(part for part in (model, aircraft_type) if part),
                    "fallback_speech": spoken_model(model, aircraft_type),
                    "suggested_table": "spoken_model",
                    **context,
                }
            )

        if flight and re.fullmatch(r"[A-Z]{4,}\d+", flight):
            spoken = spoken_flight(flight)
            if not has_callsign_prefix_speech_mapping(flight):
                items.append(
                    {
                        "key": f"callsign:{re.match(r'[A-Z]+', flight).group(0)}",
                        "kind": "callsign_prefix",
                        "value": flight,
                        "fallback_speech": spoken,
                        "suggested_table": "CALLSIGN_PREFIX_SPEECH_RU",
                        **context,
                    }
                )

        return items

    async def _async_get_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        *,
        cache_key: str,
        ttl_seconds: int,
        timeout: aiohttp.ClientTimeout,
        cache_only: bool = False,
        deadline: float | None = None,
    ) -> dict[str, Any]:
        """Return cached JSON or fetch it."""
        cache = await self._async_cache()
        now = int(time.time())
        cached = cache.get(cache_key)
        if isinstance(cached, dict):
            cache_ttl_seconds = (
                EXTERNAL_LOOKUP_ERROR_CACHE_SECONDS
                if cached.get("error") is True
                else ttl_seconds
            )
        else:
            cache_ttl_seconds = ttl_seconds
        if isinstance(cached, dict) and now - int(cached.get("fetched_at", 0)) < cache_ttl_seconds:
            payload = cached.get("payload")
            return payload if isinstance(payload, dict) else {}
        if cache_only:
            return {}

        request_timeout = timeout
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining < MIN_EXTERNAL_LOOKUP_TIMEOUT_SECONDS:
                return {}
            request_timeout = aiohttp.ClientTimeout(
                total=min(timeout.total or remaining, remaining)
            )

        try:
            async with session.get(
                url,
                headers={
                    "User-Agent": "HomeAssistantAircraftWindow/1.0 "
                    "(+https://github.com/Komzpa/ha-aircraft-window)",
                },
                timeout=request_timeout,
            ) as response:
                if response.status == 404:
                    payload = {}
                else:
                    response.raise_for_status()
                    payload = await response.json()
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
            payload = {}
        cache[cache_key] = {"fetched_at": now, "payload": payload, "error": not bool(payload)}
        await self._async_save_cache()
        return payload

    async def _async_batumi_airport_board_leg(
        self,
        session: aiohttp.ClientSession,
        *,
        today: str,
        flight_leg: str,
        request_raw_url: str,
        cache_only: bool = False,
        deadline: float | None = None,
    ) -> dict[str, Any]:
        """Return one Batumi Airport live-board leg."""
        cache_key = f"batumi-airport-board:{today}:{flight_leg.lower()}"
        cache = await self._async_cache()
        now = int(time.time())
        cached = cache.get(cache_key)
        if (
            isinstance(cached, dict)
            and now - int(cached.get("fetched_at", 0)) < AIRPORT_BOARD_CACHE_SECONDS
        ):
            payload = cached.get("payload")
            return payload if isinstance(payload, dict) else {}
        if cache_only:
            return {}

        payload: dict[str, Any] = {}
        request_timeout = 1.2
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining < MIN_EXTERNAL_LOOKUP_TIMEOUT_SECONDS:
                return {}
            request_timeout = min(request_timeout, remaining)
        params = {
            "flightLeg": flight_leg,
            "date": today,
            "destination": "",
            "airline": "",
            "requestRawUrl": request_raw_url,
        }
        providers = self.runtime_settings.providers
        try:
            async with session.get(
                providers.batumi_airport_board_base_url,
                params=params,
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Referer": f"https://batumiairport.com{request_raw_url}",
                    "User-Agent": "HomeAssistantAircraftWindow/1.0",
                    "X-Requested-With": "XMLHttpRequest",
                },
                timeout=aiohttp.ClientTimeout(total=request_timeout),
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
            payload = {}
        cache[cache_key] = {"fetched_at": now, "payload": payload, "error": not bool(payload)}
        await self._async_save_cache()
        return payload

    async def _async_batumi_airport_board(
        self,
        session: aiohttp.ClientSession,
        *,
        cache_only: bool = False,
        deadline: float | None = None,
    ) -> dict[str, Any]:
        """Return the current Batumi Airport live board for arrivals and departures."""
        if self.runtime_settings.local_airport.board_provider != "batumi_airport_board":
            return {}
        today = datetime.now(self.runtime_settings.local_airport.timezone).strftime("%d.%m.%Y")
        flights: list[dict[str, Any]] = []
        current_time = ""
        for flight_leg, request_raw_url in (
            self.runtime_settings.providers.batumi_airport_board_legs.items()
        ):
            payload = await self._async_batumi_airport_board_leg(
                session,
                today=today,
                flight_leg=flight_leg,
                request_raw_url=request_raw_url,
                cache_only=cache_only,
                deadline=deadline,
            )
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            if not current_time:
                current_time = str(data.get("currentTime") or "")
            rows = data.get("flights")
            if isinstance(rows, list):
                flights.extend(row for row in rows if isinstance(row, dict))
        return {"data": {"currentTime": current_time, "flights": flights}}

    def _airport_board_match(
        self,
        payload: dict[str, Any],
        flight: str,
        *,
        preferred_leg: str = "",
    ) -> dict[str, Any]:
        """Match a callsign to a Batumi Airport board row."""
        token = flight.strip().replace(" ", "").upper()
        match = re.fullmatch(r"([A-Z]{2,3})([A-Z0-9]+)", token)
        if not match:
            return {}
        prefix, number = match.groups()
        board_airline = CALLSIGN_PREFIX_TO_BOARD_AIRLINE.get(prefix, prefix)
        rows = (((payload.get("data") or {}).get("flights")) or [])
        if not isinstance(rows, list):
            return {}
        matches: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("flightNumber") or "").strip().upper().lstrip("0") != number.lstrip("0"):
                continue
            airline_iata = str(row.get("airlineIata") or "").strip().upper()
            airline_icao = str(row.get("airlineIcao") or "").strip().upper()
            if board_airline not in {airline_iata, airline_icao} and prefix not in {
                airline_iata,
                airline_icao,
            }:
                continue
            matches.append(row)
        if preferred_leg:
            for row in matches:
                if str(row.get("flightLeg") or "").strip().upper() == preferred_leg:
                    return row
        if matches:
            if preferred_leg:
                return {}
            for row in matches:
                if str(row.get("flightLeg") or "").strip().upper() == "DEPARTURE":
                    return row
            return matches[0]

        suffix_has_digits = any(char.isdigit() for char in number)
        suffix_is_numeric = number.isdigit()
        if suffix_has_digits and not suffix_is_numeric and preferred_leg:
            airline_leg_matches = [
                row
                for row in rows
                if isinstance(row, dict)
                and str(row.get("flightLeg") or "").strip().upper() == preferred_leg
                and (
                    board_airline
                    in {
                        str(row.get("airlineIata") or "").strip().upper(),
                        str(row.get("airlineIcao") or "").strip().upper(),
                    }
                    or prefix
                    in {
                        str(row.get("airlineIata") or "").strip().upper(),
                        str(row.get("airlineIcao") or "").strip().upper(),
                    }
                )
            ]
            if len(airline_leg_matches) == 1:
                return airline_leg_matches[0]
        return {}

    @staticmethod
    def _airport_board_leg_for_phase(phase: str) -> str:
        """Return the board leg that matches a candidate movement phase."""
        if phase in {"positioned_landing", "positioned_approach"}:
            return "ARRIVAL"
        if phase == "positioned_takeoff":
            return "DEPARTURE"
        return ""

    def _route_matches_local_phase(
        self,
        phase: str,
        origin_iata: str,
        destination_iata: str,
    ) -> bool:
        """Return true when route direction matches the configured local movement."""
        origin = origin_iata.strip().upper()
        destination = destination_iata.strip().upper()
        local_iata = self.runtime_settings.local_airport.iata.upper()
        if phase in {"positioned_landing", "positioned_approach"}:
            return destination == local_iata
        if phase == "positioned_takeoff":
            return origin == local_iata
        return True

    @staticmethod
    def _airport_board_city(data: dict[str, Any], key: str, suffix: str) -> str:
        """Return a compact city label from Batumi Airport board path data."""
        value = str(data.get(f"{key}En") or data.get(f"{key}Iata") or "").strip()
        if not value:
            return ""
        city = normalized_airport_city(value)
        iata = str(data.get(f"{key}Iata") or "").strip()
        return f"{city} ({iata})" if iata and iata not in city else city

    def _apply_airport_board_route(
        self,
        attrs: dict[str, Any],
        row: dict[str, Any],
        *,
        phase: str = "",
    ) -> None:
        """Apply route fields from a matched Batumi Airport board row."""
        path = row.get("path") if isinstance(row.get("path"), dict) else {}
        origin = path.get("origin") if isinstance(path.get("origin"), dict) else {}
        destination = path.get("destination") if isinstance(path.get("destination"), dict) else {}
        if not origin or not destination:
            return
        origin_iata = str(origin.get("originIata") or "").strip()
        destination_iata = str(destination.get("destinationIata") or "").strip()
        if phase and not self._route_matches_local_phase(
            phase,
            origin_iata,
            destination_iata,
        ):
            return
        attrs["airline_name"] = str(row.get("airlineName") or attrs["airline_name"]).strip()
        attrs["origin_iata"] = origin_iata
        attrs["origin_name"] = self._airport_board_city(origin, "origin", "from")
        attrs["origin_speech"] = airport_speech(
            {
                "iata_code": attrs["origin_iata"],
                "municipality": attrs["origin_name"].split(" (")[0],
            },
            direction="from",
        )
        attrs["destination_iata"] = destination_iata
        attrs["destination_name"] = self._airport_board_city(destination, "destination", "to")
        attrs["destination_speech"] = airport_speech(
            {
                "iata_code": attrs["destination_iata"],
                "municipality": attrs["destination_name"].split(" (")[0],
            },
            direction="to",
        )
        if attrs["origin_iata"] and attrs["destination_iata"]:
            attrs["route_summary"] = f"{attrs['origin_iata']} → {attrs['destination_iata']}"
        attrs["route_source"] = "batumi_airport_board"
        attrs["scheduled_departure_local"] = str(row.get("stad") or "")[11:16]
        attrs["airport_board_remark"] = str((row.get("remark") or {}).get("remarkEn") or "")
        attrs["airport_board_estimated_local"] = str(row.get("etad") or "")
        self._add_enrichment_source(attrs, "airport_board")

    @staticmethod
    def _row_iata(row: dict[str, Any], direction: str) -> str:
        """Return origin or destination IATA from a Batumi Airport board row."""
        path = row.get("path") if isinstance(row.get("path"), dict) else {}
        data = path.get(direction) if isinstance(path.get(direction), dict) else {}
        key = f"{direction}Iata"
        return str(data.get(key) or "").strip().upper()

    @staticmethod
    def _row_airport_name(row: dict[str, Any], direction: str) -> str:
        """Return origin or destination label from a Batumi Airport board row."""
        path = row.get("path") if isinstance(row.get("path"), dict) else {}
        data = path.get(direction) if isinstance(path.get(direction), dict) else {}
        key = f"{direction}En"
        value = str(data.get(key) or data.get(f"{direction}Iata") or "").strip()
        return normalized_airport_city(value)

    def _parse_board_time(self, value: str, now: datetime) -> datetime | None:
        """Parse an airport board timestamp into the configured airport local time."""
        value = value.strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
            return parsed.replace(tzinfo=self.runtime_settings.local_airport.timezone)
        for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
            try:
                parsed = datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
            return parsed.replace(tzinfo=self.runtime_settings.local_airport.timezone)
        if re.fullmatch(r"\d{2}:\d{2}", value):
            hour, minute = (int(part) for part in value.split(":"))
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return None

    def _scheduled_preopen_result(
        self,
        board: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Return curtain preopen state from the configured airport board."""
        now = now or datetime.now(self.runtime_settings.local_airport.timezone)
        rows = (((board.get("data") or {}).get("flights")) or [])
        candidates: list[dict[str, Any]] = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            if str(row.get("flightLeg") or "").strip().upper() != "DEPARTURE":
                continue
            departure = self._parse_board_time(str(row.get("etad") or row.get("stad") or ""), now)
            if departure is None:
                continue
            seconds_until = int((departure - now).total_seconds())
            if seconds_until < -SCHEDULED_PREOPEN_AFTER_SECONDS:
                continue
            candidates.append(
                {
                    "row": row,
                    "departure": departure,
                    "seconds_until": seconds_until,
                }
            )
        candidates.sort(key=lambda item: abs(item["seconds_until"]))
        active = bool(
            candidates
            and -SCHEDULED_PREOPEN_AFTER_SECONDS
            <= candidates[0]["seconds_until"]
            <= SCHEDULED_PREOPEN_BEFORE_SECONDS
        )
        selected = candidates[0] if candidates else {}
        row = selected.get("row") if isinstance(selected.get("row"), dict) else {}
        destination_iata = self._row_iata(row, "destination") if row else ""
        destination_name = self._row_airport_name(row, "destination") if row else ""
        return {
            "state": "on" if active else "off",
            "phase": (
                "scheduled_departure_preopen" if active else "scheduled_departure_waiting"
            ),
            "confidence": 0.7 if active else 0.0,
            "confidence_reason": (
                "scheduled departure inside curtain preopen window"
                if active
                else "no scheduled departure inside curtain preopen window"
            ),
            "flight": (
                f"{row.get('airlineIcao') or row.get('airlineIata') or ''}"
                f"{row.get('flightNumber') or ''}"
            ).strip(),
            "flight_number": str(row.get("flightNumber") or ""),
            "airline_iata": str(row.get("airlineIata") or ""),
            "airline_icao": str(row.get("airlineIcao") or ""),
            "airline_name": str(row.get("airlineName") or ""),
            "origin_iata": self._row_iata(row, "origin") if row else "",
            "destination_iata": destination_iata,
            "destination_name": destination_name,
            "scheduled_departure_local": (
                selected["departure"].strftime("%H:%M") if selected else ""
            ),
            "seconds_until_departure": selected.get("seconds_until"),
            "scheduled_preopen_before_seconds": SCHEDULED_PREOPEN_BEFORE_SECONDS,
            "scheduled_preopen_after_seconds": SCHEDULED_PREOPEN_AFTER_SECONDS,
            "scheduled_candidates": len(candidates),
            "source": "batumi_airport_board",
            "updated_at": int(time.time()),
        }

    @staticmethod
    def _add_enrichment_source(attrs: dict[str, Any], source: str) -> None:
        """Append an enrichment source once, preserving earlier providers."""
        sources = [item for item in str(attrs.get("enrichment_source") or "").split("+") if item]
        if source not in sources:
            sources.append(source)
        attrs["enrichment_source"] = "+".join(sources)

    def _apply_airplanes_live_aircraft(
        self,
        attrs: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        """Apply aircraft metadata from Airplanes.live ADS-B rows."""
        rows = payload.get("ac")
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            return
        row = rows[0]
        attrs["aircraft_model"] = attrs["aircraft_model"] or str(row.get("desc") or "").strip()
        attrs["aircraft_type"] = attrs["aircraft_type"] or str(row.get("t") or "").strip()
        attrs["registration"] = attrs["registration"] or str(row.get("r") or "").strip()
        if attrs["aircraft_model"] or attrs["aircraft_type"] or attrs["registration"]:
            self._add_enrichment_source(attrs, "airplanes_live")

    async def _async_airport_data_year(
        self,
        session: aiohttp.ClientSession,
        registration: str,
        timeout: aiohttp.ClientTimeout,
        *,
        cache_only: bool = False,
        deadline: float | None = None,
    ) -> int | None:
        """Fetch or return cached built year for a registration."""
        registration = registration.strip().upper()
        if not registration:
            return None
        if registration in KNOWN_BUILT_YEAR_BY_REGISTRATION:
            return KNOWN_BUILT_YEAR_BY_REGISTRATION[registration]

        cache = await self._async_cache()
        now = int(time.time())
        cache_key = f"airport-data-year:{registration}"
        cached = cache.get(cache_key)
        if (
            isinstance(cached, dict)
            and now - int(cached.get("fetched_at", 0)) < BUILT_YEAR_CACHE_SECONDS
        ):
            year = cached.get("year")
            return int(year) if isinstance(year, int) else None
        if cache_only:
            return None

        year = None
        url = f"https://airport-data.com/aircraft/{quote(registration)}.html"
        request_timeout = timeout
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining < MIN_EXTERNAL_LOOKUP_TIMEOUT_SECONDS:
                return None
            request_timeout = aiohttp.ClientTimeout(
                total=min(timeout.total or remaining, remaining)
            )
        try:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 HomeAssistantAircraftWindow/1.0"},
                timeout=request_timeout,
            ) as response:
                response.raise_for_status()
                year = extract_airport_data_year(await response.text())
        except (aiohttp.ClientError, TimeoutError):
            return None

        cache[cache_key] = {"fetched_at": now, "year": year}
        await self._async_save_cache()
        return year

    async def _async_enrich_aircraft(
        self,
        aircraft: dict[str, Any],
        *,
        phase: str = "",
        cache_only: bool = False,
        deadline: float | None = None,
    ) -> dict[str, Any]:
        """Enrich aircraft with route, airline, model and built year."""
        options = self.options
        timeout = aiohttp.ClientTimeout(
            total=float(
                options.get(
                    CONF_ENRICHMENT_TIMEOUT_SECONDS,
                    DEFAULT_ENRICHMENT_TIMEOUT_SECONDS,
                )
            )
        )
        flight = flight_label(aircraft).replace(" ", "").upper()
        hex_id = str(aircraft.get("hex") or "").strip().upper()
        attrs: dict[str, Any] = {
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
            "aircraft_model": "",
            "aircraft_type": "",
            "aircraft_model_speech": "",
            "registration": "",
            "registered_owner": "",
            "operator_flag_code": "",
            "owner_country": "",
            "built_year": None,
            "built_year_speech": "",
            "enrichment_source": "",
            "interest_reason": "",
            "novelty_reason": "",
            "unusual_aircraft": False,
            "spoken_flight": spoken_flight(flight),
            "adsb_category": str(aircraft.get("category") or "").strip().upper(),
            "service_type": "unknown",
            "service_type_confidence": 0.0,
            "service_type_reason": "",
        }

        session = async_get_clientsession(self.hass)
        if flight and flight != "UNKNOWN" and not flight.lower().startswith(hex_id.lower()):
            board = await self._async_batumi_airport_board(
                session,
                cache_only=cache_only,
                deadline=deadline,
            )
            board_row = self._airport_board_match(
                board,
                flight,
                preferred_leg=self._airport_board_leg_for_phase(phase),
            )
            if board_row:
                self._apply_airport_board_route(attrs, board_row, phase=phase)

        if flight and flight != "UNKNOWN" and not flight.lower().startswith(hex_id.lower()):
            providers = self.runtime_settings.providers
            route_payload = await self._async_get_json(
                session,
                f"{providers.adsbdb_base_url}/callsign/{quote(flight)}",
                cache_key=f"callsign:{flight}",
                ttl_seconds=ROUTE_CACHE_SECONDS,
                timeout=timeout,
                cache_only=cache_only,
                deadline=deadline,
            )
            route = ((route_payload or {}).get("response") or {}).get("flightroute")
            if isinstance(route, dict) and attrs["route_source"] != "batumi_airport_board":
                airline = route.get("airline") if isinstance(route.get("airline"), dict) else {}
                origin = route.get("origin") if isinstance(route.get("origin"), dict) else {}
                destination = (
                    route.get("destination") if isinstance(route.get("destination"), dict) else {}
                )
                attrs["airline_name"] = str(airline.get("name") or "").strip()
                origin_iata = str(origin.get("iata_code") or "").strip()
                destination_iata = str(destination.get("iata_code") or "").strip()
                if self._route_matches_local_phase(phase, origin_iata, destination_iata):
                    attrs["origin_iata"] = origin_iata
                    attrs["origin_name"] = airport_label(origin)
                    attrs["origin_speech"] = airport_speech(origin, direction="from")
                    attrs["destination_iata"] = destination_iata
                    attrs["destination_name"] = airport_label(destination)
                    attrs["destination_speech"] = airport_speech(destination, direction="to")
                    if attrs["origin_iata"] and attrs["destination_iata"]:
                        attrs["route_summary"] = (
                            f"{attrs['origin_iata']} → {attrs['destination_iata']}"
                        )
                        attrs["route_source"] = "adsbdb"
                attrs["spoken_flight"] = spoken_flight(
                    flight,
                    airline_icao=str(airline.get("icao") or ""),
                    airline_iata=str(airline.get("iata") or ""),
                )
                if attrs["airline_name"] or attrs["route_summary"]:
                    self._add_enrichment_source(attrs, "adsbdb")

        fallback_airline, fallback_prefix = known_airline_for_callsign(flight)
        if fallback_airline:
            if not attrs["airline_name"]:
                attrs["airline_name"] = fallback_airline
                self._add_enrichment_source(attrs, "callsign")
            if fallback_prefix:
                attrs["spoken_flight"] = spoken_flight(flight, airline_icao=fallback_prefix)

        fallback_route = known_route_for_callsign(flight)
        if fallback_route and not attrs["route_summary"]:
            for key, value in fallback_route.items():
                if key == "airline_name" and value:
                    attrs[key] = value
                elif value and not attrs.get(key):
                    attrs[key] = value
            self._add_enrichment_source(attrs, "local_route")

        if hex_id:
            providers = self.runtime_settings.providers
            aircraft_payload = await self._async_get_json(
                session,
                f"{providers.adsbdb_base_url}/aircraft/{quote(hex_id)}",
                cache_key=f"aircraft:{hex_id}",
                ttl_seconds=AIRCRAFT_CACHE_SECONDS,
                timeout=timeout,
                cache_only=cache_only,
                deadline=deadline,
            )
            aircraft_info = ((aircraft_payload or {}).get("response") or {}).get("aircraft")
            if isinstance(aircraft_info, dict):
                attrs["aircraft_model"] = str(aircraft_info.get("type") or "").strip()
                attrs["aircraft_type"] = str(aircraft_info.get("icao_type") or "").strip()
                attrs["registration"] = str(aircraft_info.get("registration") or "").strip()
                attrs["registered_owner"] = str(aircraft_info.get("registered_owner") or "").strip()
                attrs["operator_flag_code"] = str(
                    aircraft_info.get("registered_owner_operator_flag_code") or ""
                ).strip()
                if attrs["operator_flag_code"]:
                    attrs["spoken_flight"] = spoken_flight(
                        flight,
                        airline_icao=attrs["operator_flag_code"],
                    )
                attrs["owner_country"] = str(
                    aircraft_info.get("registered_owner_country_name") or ""
                ).strip()
                if attrs["aircraft_model"] or attrs["registration"]:
                    self._add_enrichment_source(attrs, "adsbdb")

        if hex_id and (not attrs["aircraft_model"] or not attrs["registration"]):
            providers = self.runtime_settings.providers
            hexdb_payload = await self._async_get_json(
                session,
                f"{providers.hexdb_base_url}/aircraft/{quote(hex_id)}",
                cache_key=f"hexdb-aircraft:{hex_id}",
                ttl_seconds=AIRCRAFT_CACHE_SECONDS,
                timeout=timeout,
                cache_only=cache_only,
                deadline=deadline,
            )
            attrs["aircraft_model"] = attrs["aircraft_model"] or str(
                hexdb_payload.get("Type") or ""
            ).strip()
            attrs["aircraft_type"] = attrs["aircraft_type"] or str(
                hexdb_payload.get("ICAOTypeCode") or ""
            ).strip()
            attrs["registration"] = attrs["registration"] or str(
                hexdb_payload.get("Registration") or ""
            ).strip()
            attrs["registered_owner"] = attrs.get("registered_owner") or str(
                hexdb_payload.get("RegisteredOwners") or ""
            ).strip()
            attrs["operator_flag_code"] = attrs.get("operator_flag_code") or str(
                hexdb_payload.get("OperatorFlagCode") or ""
            ).strip()
            if attrs["operator_flag_code"]:
                attrs["spoken_flight"] = spoken_flight(
                    flight,
                    airline_icao=attrs["operator_flag_code"],
                )
            if attrs["aircraft_model"] or attrs["registration"]:
                self._add_enrichment_source(attrs, "hexdb")

        if hex_id and (not attrs["aircraft_model"] or not attrs["registration"]):
            providers = self.runtime_settings.providers
            airplanes_live_payload = await self._async_get_json(
                session,
                f"{providers.airplanes_live_base_url}/hex/{quote(hex_id)}",
                cache_key=f"airplanes-live-aircraft:{hex_id}",
                ttl_seconds=AIRCRAFT_CACHE_SECONDS,
                timeout=timeout,
                cache_only=cache_only,
                deadline=deadline,
            )
            self._apply_airplanes_live_aircraft(attrs, airplanes_live_payload)

        attrs["aircraft_model_speech"] = spoken_model(
            attrs["aircraft_model"],
            attrs["aircraft_type"],
        )
        built_year = await self._async_airport_data_year(
            session,
            attrs["registration"],
            timeout,
            cache_only=cache_only,
            deadline=deadline,
        )
        attrs["built_year"] = built_year
        attrs["built_year_speech"] = spoken_year(built_year)
        service_type, service_confidence, service_reason = classify_service_type(attrs)
        attrs["service_type"] = service_type
        attrs["service_type_confidence"] = service_confidence
        attrs["service_type_reason"] = service_reason

        return attrs


class EnrichmentPrefetchCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Warm the enrichment cache away from the hot candidate scan."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        aircraft: AircraftWindowCoordinator,
    ) -> None:
        """Initialize the background prefetch coordinator."""
        self.entry = entry
        self.aircraft = aircraft
        options = aircraft.options
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_enrichment_prefetch",
            update_interval=timedelta(
                seconds=options.get(
                    CONF_BACKGROUND_INTERVAL_SECONDS,
                    DEFAULT_BACKGROUND_INTERVAL_SECONDS,
                )
            ),
        )

    @property
    def options(self) -> dict[str, Any]:
        """Return merged config entry data and options."""
        return self.aircraft.options

    async def _async_update_data(self) -> dict[str, Any]:
        """Prefetch route and aircraft enrichment under a shared deadline."""
        started = time.monotonic()
        options = self.options
        budget_seconds = float(
            options.get(
                CONF_PREFETCH_BUDGET_SECONDS,
                DEFAULT_PREFETCH_BUDGET_SECONDS,
            )
        )
        deadline = started + budget_seconds if budget_seconds > 0 else None
        dump1090_url = options.get(CONF_DUMP1090_URL, DEFAULT_DUMP1090_URL)
        session = async_get_clientsession(self.hass)
        rows: list[dict[str, Any]] = []
        try:
            async with session.get(
                dump1090_url,
                timeout=aiohttp.ClientTimeout(total=3),
            ) as response:
                response.raise_for_status()
                payload = await response.json()
            aircraft_rows = payload.get("aircraft") if isinstance(payload, dict) else []
            if isinstance(aircraft_rows, list):
                rows = [row for row in aircraft_rows if isinstance(row, dict)]
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
            rows = []

        limit = int(options.get(CONF_PREFETCH_LIMIT, DEFAULT_PREFETCH_LIMIT))
        selected = _select_prefetch_rows(rows, limit)
        semaphore = asyncio.Semaphore(4)
        warmed: list[str] = []
        failed = 0
        skipped = 0
        mapping_review_new: list[dict[str, Any]] = []
        collect_mapping_review = bool(
            options.get(CONF_COLLECT_MAPPING_REVIEW, DEFAULT_COLLECT_MAPPING_REVIEW)
        )

        async def prefetch_one(row: dict[str, Any]) -> None:
            nonlocal failed, skipped
            if (
                deadline is not None
                and deadline - time.monotonic() < MIN_EXTERNAL_LOOKUP_TIMEOUT_SECONDS
            ):
                skipped += 1
                return
            async with semaphore:
                if (
                    deadline is not None
                    and deadline - time.monotonic() < MIN_EXTERNAL_LOOKUP_TIMEOUT_SECONDS
                ):
                    skipped += 1
                    return
                try:
                    attrs = await self.aircraft._async_enrich_aircraft(
                        row,
                        cache_only=False,
                        deadline=deadline,
                    )
                except Exception:
                    failed += 1
                    return
                if collect_mapping_review:
                    mapping_review_new.extend(
                        self.aircraft._mapping_review_items_for_visible_aircraft(row, attrs)
                    )
                label = flight_label(row).replace(" ", "").upper()
                source = str(attrs.get("enrichment_source") or "").strip()
                if label and source:
                    warmed.append(f"{label}:{source}")
                elif label:
                    warmed.append(label)

        await asyncio.gather(*(prefetch_one(row) for row in selected))
        mapping_review = (
            await self.aircraft._async_record_mapping_review_items(mapping_review_new)
            if collect_mapping_review
            else await self.aircraft._async_mapping_review_items()
        )
        elapsed_ms = round((time.monotonic() - started) * 1000)
        board = await self.aircraft._async_batumi_airport_board(
            session,
            cache_only=False,
            deadline=deadline,
        )
        schedule_preopen = self.aircraft._scheduled_preopen_result(board)
        cache = await self.aircraft._async_cache()
        cache_pruned = _prune_expired_cache_entries(cache)
        if cache_pruned:
            await self.aircraft._async_save_cache()
        prefetch_status = {
            "state": "ok",
            "prefetch_candidates": len(rows),
            "prefetch_selected": len(selected),
            "prefetch_limit": limit,
            "prefetch_warmed": len(warmed),
            "prefetch_failed": failed,
            "prefetch_skipped": skipped + max(0, len(selected) - len(warmed) - failed - skipped),
            "prefetch_budget_seconds": budget_seconds,
            "prefetch_elapsed_ms": elapsed_ms,
            "prefetch_items": ", ".join(warmed[:20]),
            "mapping_review_enabled": collect_mapping_review,
            "mapping_review_count": len(mapping_review),
            "mapping_review_new": len(mapping_review_new),
            "mapping_review_items": mapping_review[:20],
            "cache_entries": len(cache),
            "cache_pruned": cache_pruned,
            "updated_at": int(time.time()),
        }
        return {
            "state": "ok",
            "enrichment_prefetch": prefetch_status,
            "schedule_preopen": schedule_preopen,
            "updated_at": int(time.time()),
        }
