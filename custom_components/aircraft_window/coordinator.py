"""Coordinator for Aircraft Window."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
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
    airport_label,
    airport_speech,
    backfill_position_from_history,
    build_followup_announcement,
    candidate_airframe_key,
    candidate_has_real_flight,
    classify_service_type,
    extract_airport_data_year,
    flight_label,
    has_route_details,
    idle_candidate,
    interest_candidate,
    known_airline_for_callsign,
    known_route_for_callsign,
    make_key,
    movement_family,
    normalized_airport_city,
    pick_candidate,
    spoken_flight,
    spoken_model,
    spoken_year,
)

_LOGGER = logging.getLogger(__name__)

ADSBDB_BASE_URL = "https://api.adsbdb.com/v0"
HEXDB_BASE_URL = "https://hexdb.io/api/v1"
AIRPLANES_LIVE_BASE_URL = "https://api.airplanes.live/v2"
LOCAL_AIRPORT_IATA = "BUS"
ROUTE_CACHE_SECONDS = 6 * 60 * 60
AIRCRAFT_CACHE_SECONDS = 24 * 60 * 60
BUILT_YEAR_CACHE_SECONDS = 30 * 24 * 60 * 60
AIRPORT_BOARD_CACHE_SECONDS = 5 * 60
ROUTINE_HEX_HOLD_SECONDS = 10.0
ROUTINE_HEX_HOLD_SUPPRESSION_REASON = "waiting briefly for callsign"
BATUMI_AIRPORT_BOARD_BASE_URL = "https://batumiairport.com/Home/searchFlights"
TBILISI_TIMEZONE = timezone(timedelta(hours=4))
BATUMI_AIRPORT_BOARD_LEGS = {
    "DEPARTURE": "/en-EN/flights/departure-flights",
    "ARRIVAL": "/en-EN/flights/arrival-flights",
}
EXTERNAL_LOOKUP_ERROR_CACHE_SECONDS = 10 * 60
MIN_EXTERNAL_LOOKUP_TIMEOUT_SECONDS = 0.25

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

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}")
        self._cache: dict[str, Any] | None = None
        self._last_event_key = ""
        self._last_announced_by_airframe: dict[str, AircraftCandidate] = {}
        self._announced_event_keys_by_airframe: dict[str, set[str]] = {}
        self._held_routine_hex_candidates: dict[str, float] = {}
        options = self.options
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
            )
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
            )
            if candidate is not None and (
                best is None or candidate.confidence > best.confidence
            ):
                best = candidate
        return best

    async def _async_cache(self) -> dict[str, Any]:
        """Load persistent enrichment cache."""
        if self._cache is None:
            self._cache = await self._store.async_load() or {}
        return self._cache

    async def _async_save_cache(self) -> None:
        """Save persistent enrichment cache."""
        if self._cache is not None:
            await self._store.async_save(self._cache)

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
        try:
            async with session.get(
                BATUMI_AIRPORT_BOARD_BASE_URL,
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
        today = datetime.now(TBILISI_TIMEZONE).strftime("%d.%m.%Y")
        flights: list[dict[str, Any]] = []
        current_time = ""
        for flight_leg, request_raw_url in BATUMI_AIRPORT_BOARD_LEGS.items():
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
            return {}
        for row in matches:
            if str(row.get("flightLeg") or "").strip().upper() == "DEPARTURE":
                return row
        return matches[0] if matches else {}

    @staticmethod
    def _airport_board_leg_for_phase(phase: str) -> str:
        """Return the board leg that matches a candidate movement phase."""
        if phase in {"positioned_landing", "positioned_approach"}:
            return "ARRIVAL"
        if phase == "positioned_takeoff":
            return "DEPARTURE"
        return ""

    @staticmethod
    def _route_matches_local_phase(phase: str, origin_iata: str, destination_iata: str) -> bool:
        """Return true when route direction matches the local Batumi movement."""
        origin = origin_iata.strip().upper()
        destination = destination_iata.strip().upper()
        if phase in {"positioned_landing", "positioned_approach"}:
            return destination == LOCAL_AIRPORT_IATA
        if phase == "positioned_takeoff":
            return origin == LOCAL_AIRPORT_IATA
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

    @staticmethod
    def _parse_board_time(value: str, now: datetime) -> datetime | None:
        """Parse a Batumi board timestamp into Tbilisi local time."""
        value = value.strip()
        if not value:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
            return parsed.replace(tzinfo=TBILISI_TIMEZONE)
        for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
            try:
                parsed = datetime.strptime(value[:19], fmt)
            except ValueError:
                continue
            return parsed.replace(tzinfo=TBILISI_TIMEZONE)
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
        """Return curtain preopen state from the Batumi Airport board."""
        now = now or datetime.now(TBILISI_TIMEZONE)
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
            route_payload = await self._async_get_json(
                session,
                f"{ADSBDB_BASE_URL}/callsign/{quote(flight)}",
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
            aircraft_payload = await self._async_get_json(
                session,
                f"{ADSBDB_BASE_URL}/aircraft/{quote(hex_id)}",
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
            hexdb_payload = await self._async_get_json(
                session,
                f"{HEXDB_BASE_URL}/aircraft/{quote(hex_id)}",
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
            airplanes_live_payload = await self._async_get_json(
                session,
                f"{AIRPLANES_LIVE_BASE_URL}/hex/{quote(hex_id)}",
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
        selected = rows if limit == 0 else rows[:limit]
        semaphore = asyncio.Semaphore(4)
        warmed: list[str] = []
        failed = 0
        skipped = 0

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
                label = flight_label(row).replace(" ", "").upper()
                source = str(attrs.get("enrichment_source") or "").strip()
                if label and source:
                    warmed.append(f"{label}:{source}")
                elif label:
                    warmed.append(label)

        await asyncio.gather(*(prefetch_one(row) for row in selected))
        elapsed_ms = round((time.monotonic() - started) * 1000)
        board = await self.aircraft._async_batumi_airport_board(
            session,
            cache_only=False,
            deadline=deadline,
        )
        schedule_preopen = self.aircraft._scheduled_preopen_result(board)
        prefetch_status = {
            "state": "ok",
            "prefetch_candidates": len(rows),
            "prefetch_limit": limit,
            "prefetch_warmed": len(warmed),
            "prefetch_failed": failed,
            "prefetch_skipped": skipped + max(0, len(selected) - len(warmed) - failed - skipped),
            "prefetch_budget_seconds": budget_seconds,
            "prefetch_elapsed_ms": elapsed_ms,
            "prefetch_items": ", ".join(warmed[:20]),
            "updated_at": int(time.time()),
        }
        return {
            "state": "ok",
            "enrichment_prefetch": prefetch_status,
            "schedule_preopen": schedule_preopen,
            "updated_at": int(time.time()),
        }
