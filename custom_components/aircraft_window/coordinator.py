"""Coordinator for Aircraft Window."""

from __future__ import annotations

import json
import logging
import time
from datetime import timedelta
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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
    EVENT_CANDIDATE,
)
from .logic import (
    KNOWN_BUILT_YEAR_BY_REGISTRATION,
    AircraftCandidate,
    airport_label,
    airport_speech,
    backfill_position_from_history,
    build_followup_announcement,
    candidate_airframe_key,
    extract_airport_data_year,
    flight_label,
    idle_candidate,
    interest_candidate,
    make_key,
    pick_candidate,
    spoken_flight,
    spoken_model,
    spoken_year,
)

_LOGGER = logging.getLogger(__name__)

ADSBDB_BASE_URL = "https://api.adsbdb.com/v0"
HEXDB_BASE_URL = "https://hexdb.io/api/v1"
ROUTE_CACHE_SECONDS = 6 * 60 * 60
AIRCRAFT_CACHE_SECONDS = 24 * 60 * 60
BUILT_YEAR_CACHE_SECONDS = 30 * 24 * 60 * 60


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
                enrichment = await self._async_enrich_aircraft(row)
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

        if options.get(CONF_ENABLE_ENRICHMENT, True):
            special_candidate = await self._async_pick_interest_candidate(
                aircraft_rows,
                source=dump1090_url,
            )
            if (
                special_candidate is not None
                and (
                    not base_candidate.active
                    or special_candidate.confidence > base_candidate.confidence
                    or (
                        special_candidate.phase == "military_visible"
                        and base_candidate.phase
                        not in {"positioned_landing", "positioned_takeoff", "positioned_approach"}
                    )
                )
            ):
                base_candidate = special_candidate

        if base_candidate.active:
            airframe_key = candidate_airframe_key(base_candidate)
            announced_keys = self._announced_event_keys_by_airframe.setdefault(
                airframe_key,
                set(),
            )
            if base_candidate.event_key not in announced_keys:
                previous = self._last_announced_by_airframe.get(airframe_key)
                if previous is not None:
                    followup = build_followup_announcement(previous, base_candidate)
                    if followup:
                        base_candidate.announcement = followup
                self.hass.bus.async_fire(EVENT_CANDIDATE, base_candidate.as_dict())
                self._last_event_key = base_candidate.event_key
                announced_keys.add(base_candidate.event_key)
                self._last_announced_by_airframe[airframe_key] = base_candidate
        elif not base_candidate.active:
            self._last_event_key = ""
        return base_candidate

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
    ) -> AircraftCandidate | None:
        """Return the best route or military aircraft visible in the receiver feed."""
        best: AircraftCandidate | None = None
        for aircraft in aircraft_rows[:12]:
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
            enrichment = await self._async_enrich_aircraft(aircraft)
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
    ) -> dict[str, Any]:
        """Return cached JSON or fetch it."""
        cache = await self._async_cache()
        now = int(time.time())
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and now - int(cached.get("fetched_at", 0)) < ttl_seconds:
            payload = cached.get("payload")
            return payload if isinstance(payload, dict) else {}

        try:
            async with session.get(
                url,
                headers={"User-Agent": "HomeAssistantAircraftWindow/1.0"},
                timeout=timeout,
            ) as response:
                if response.status == 404:
                    payload = {}
                else:
                    response.raise_for_status()
                    payload = await response.json()
        except (aiohttp.ClientError, TimeoutError, json.JSONDecodeError):
            payload = {}
        cache[cache_key] = {"fetched_at": now, "payload": payload}
        await self._async_save_cache()
        return payload

    async def _async_airport_data_year(
        self,
        session: aiohttp.ClientSession,
        registration: str,
        timeout: aiohttp.ClientTimeout,
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

        year = None
        url = f"https://airport-data.com/aircraft/{quote(registration)}.html"
        try:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 HomeAssistantAircraftWindow/1.0"},
                timeout=timeout,
            ) as response:
                response.raise_for_status()
                year = extract_airport_data_year(await response.text())
        except (aiohttp.ClientError, TimeoutError):
            return None

        cache[cache_key] = {"fetched_at": now, "year": year}
        await self._async_save_cache()
        return year

    async def _async_enrich_aircraft(self, aircraft: dict[str, Any]) -> dict[str, Any]:
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
        }

        session = async_get_clientsession(self.hass)
        if flight and flight != "UNKNOWN" and not flight.lower().startswith(hex_id.lower()):
            route_payload = await self._async_get_json(
                session,
                f"{ADSBDB_BASE_URL}/callsign/{quote(flight)}",
                cache_key=f"callsign:{flight}",
                ttl_seconds=ROUTE_CACHE_SECONDS,
                timeout=timeout,
            )
            route = ((route_payload or {}).get("response") or {}).get("flightroute")
            if isinstance(route, dict):
                airline = route.get("airline") if isinstance(route.get("airline"), dict) else {}
                origin = route.get("origin") if isinstance(route.get("origin"), dict) else {}
                destination = (
                    route.get("destination") if isinstance(route.get("destination"), dict) else {}
                )
                attrs["airline_name"] = str(airline.get("name") or "").strip()
                attrs["origin_iata"] = str(origin.get("iata_code") or "").strip()
                attrs["origin_name"] = airport_label(origin)
                attrs["origin_speech"] = airport_speech(origin, direction="from")
                attrs["destination_iata"] = str(destination.get("iata_code") or "").strip()
                attrs["destination_name"] = airport_label(destination)
                attrs["destination_speech"] = airport_speech(destination, direction="to")
                if attrs["origin_iata"] and attrs["destination_iata"]:
                    attrs["route_summary"] = f"{attrs['origin_iata']} → {attrs['destination_iata']}"
                attrs["spoken_flight"] = spoken_flight(
                    flight,
                    airline_icao=str(airline.get("icao") or ""),
                    airline_iata=str(airline.get("iata") or ""),
                )
                if attrs["airline_name"] or attrs["route_summary"]:
                    attrs["enrichment_source"] = "adsbdb"

        if hex_id:
            aircraft_payload = await self._async_get_json(
                session,
                f"{ADSBDB_BASE_URL}/aircraft/{quote(hex_id)}",
                cache_key=f"aircraft:{hex_id}",
                ttl_seconds=AIRCRAFT_CACHE_SECONDS,
                timeout=timeout,
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
                attrs["owner_country"] = str(
                    aircraft_info.get("registered_owner_country_name") or ""
                ).strip()
                if attrs["aircraft_model"] or attrs["registration"]:
                    attrs["enrichment_source"] = "adsbdb"

        if hex_id and (not attrs["aircraft_model"] or not attrs["registration"]):
            hexdb_payload = await self._async_get_json(
                session,
                f"{HEXDB_BASE_URL}/aircraft/{quote(hex_id)}",
                cache_key=f"hexdb-aircraft:{hex_id}",
                ttl_seconds=AIRCRAFT_CACHE_SECONDS,
                timeout=timeout,
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
            if attrs["aircraft_model"] or attrs["registration"]:
                attrs["enrichment_source"] = (
                    "adsbdb+hexdb" if attrs["enrichment_source"] else "hexdb"
                )

        attrs["aircraft_model_speech"] = spoken_model(
            attrs["aircraft_model"],
            attrs["aircraft_type"],
        )
        built_year = await self._async_airport_data_year(session, attrs["registration"], timeout)
        attrs["built_year"] = built_year
        attrs["built_year_speech"] = spoken_year(built_year)

        return attrs
