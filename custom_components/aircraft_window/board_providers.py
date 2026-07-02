"""Airport board provider helpers for Aircraft Window."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .logic import normalized_airport_city

BATUMI_AIRPORT_BOARD_PROVIDER = "batumi_airport_board"
JSON_AIRPORT_BOARD_PROVIDER = "json_airport_board"
DISABLED_AIRPORT_BOARD_PROVIDER = ""
AIRPORT_BOARD_PROVIDERS_DATA_FILE = "data/airport_board_providers.json"


@dataclass(frozen=True, slots=True)
class AirportBoardProvider:
    """Configured airport-board provider descriptor."""

    provider_id: str
    title: str
    cache_prefix: str = ""
    callsign_prefix_to_board_airline: dict[str, str] | None = None


def _load_board_provider_data_file(filename: str) -> Any:
    """Load one packaged airport-board provider data JSON file."""
    raw_text = (Path(__file__).resolve().parent / filename).read_text(encoding="utf-8")
    return json.loads(raw_text)


def load_airport_board_providers_from_data_file(
    filename: str = AIRPORT_BOARD_PROVIDERS_DATA_FILE,
) -> tuple[AirportBoardProvider, ...]:
    """Load built-in airport-board provider descriptors from packaged data."""
    raw_data = _load_board_provider_data_file(filename)
    if not isinstance(raw_data, dict):
        return ()
    raw_providers = raw_data.get("providers")
    if not isinstance(raw_providers, list):
        return ()
    providers: list[AirportBoardProvider] = []
    for raw_provider in raw_providers:
        if not isinstance(raw_provider, dict):
            continue
        provider_id = str(raw_provider.get("provider_id", "")).strip()
        title = str(raw_provider.get("title") or provider_id or "Disabled").strip()
        raw_prefix_map = raw_provider.get("callsign_prefix_to_board_airline")
        prefix_map = (
            {
                str(key).strip().upper(): str(value).strip().upper()
                for key, value in raw_prefix_map.items()
                if str(key).strip() and str(value).strip()
            }
            if isinstance(raw_prefix_map, dict)
            else {}
        )
        providers.append(
            AirportBoardProvider(
                provider_id=provider_id,
                title=title,
                cache_prefix=str(raw_provider.get("cache_prefix") or "").strip(),
                callsign_prefix_to_board_airline=prefix_map,
            )
        )
    return tuple(providers)


AIRPORT_BOARD_PROVIDERS = load_airport_board_providers_from_data_file()
AIRPORT_BOARD_PROVIDER_IDS = tuple(provider.provider_id for provider in AIRPORT_BOARD_PROVIDERS)
AIRPORT_BOARD_PROVIDERS_BY_ID = {
    provider.provider_id: provider for provider in AIRPORT_BOARD_PROVIDERS
}
BATUMI_AIRPORT_BOARD_CACHE_PREFIX = (
    AIRPORT_BOARD_PROVIDERS_BY_ID.get(
        BATUMI_AIRPORT_BOARD_PROVIDER,
        AirportBoardProvider(BATUMI_AIRPORT_BOARD_PROVIDER, ""),
    ).cache_prefix
    or "batumi-airport-board:"
)
GENERIC_AIRPORT_BOARD_CACHE_PREFIX = (
    AIRPORT_BOARD_PROVIDERS_BY_ID.get(
        JSON_AIRPORT_BOARD_PROVIDER,
        AirportBoardProvider(JSON_AIRPORT_BOARD_PROVIDER, ""),
    ).cache_prefix
    or "airport-board:"
)
AIRPORT_BOARD_CACHE_PREFIXES = tuple(
    dict.fromkeys(
        prefix
        for prefix in (
            *(provider.cache_prefix for provider in AIRPORT_BOARD_PROVIDERS),
            GENERIC_AIRPORT_BOARD_CACHE_PREFIX,
        )
        if prefix
    )
)


def is_airport_board_provider(provider_id: str) -> bool:
    """Return true when the provider id is supported and enabled."""
    return bool(provider_id) and provider_id in AIRPORT_BOARD_PROVIDERS_BY_ID


@dataclass(frozen=True, slots=True)
class AirportBoardLegRequest:
    """HTTP request details for one provider board leg."""

    url: str
    params: dict[str, str]
    headers: dict[str, str]


def airport_board_cache_key(provider_id: str, today: str, flight_leg: str) -> str:
    """Return a stable cache key for one provider board leg."""
    if provider_id == BATUMI_AIRPORT_BOARD_PROVIDER:
        return f"{BATUMI_AIRPORT_BOARD_CACHE_PREFIX}{today}:{flight_leg.lower()}"
    normalized_provider = provider_id.strip().replace("_", "-") or "airport-board"
    return f"{GENERIC_AIRPORT_BOARD_CACHE_PREFIX}{normalized_provider}:{today}:{flight_leg.lower()}"


def batumi_airport_board_leg_request(
    *,
    base_url: str,
    today: str,
    flight_leg: str,
    request_raw_url: str,
) -> AirportBoardLegRequest:
    """Return the built-in airport board request shape for one leg."""
    return AirportBoardLegRequest(
        url=base_url,
        params={
            "flightLeg": flight_leg,
            "date": today,
            "destination": "",
            "airline": "",
            "requestRawUrl": request_raw_url,
        },
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": f"https://batumiairport.com{request_raw_url}",
            "User-Agent": "HomeAssistantAircraftWindow/1.0",
            "X-Requested-With": "XMLHttpRequest",
        },
    )


def json_airport_board_request(*, url: str) -> AirportBoardLegRequest:
    """Return the canonical JSON airport board request shape."""
    return AirportBoardLegRequest(
        url=url,
        params={},
        headers={
            "Accept": "application/json",
            "User-Agent": "HomeAssistantAircraftWindow/1.0",
        },
    )


def airport_board_leg_for_phase(phase: str) -> str:
    """Return the board leg that matches a candidate movement phase."""
    if phase in {"positioned_landing", "positioned_approach"}:
        return "ARRIVAL"
    if phase == "positioned_takeoff":
        return "DEPARTURE"
    return ""


def match_airport_board_row(
    payload: dict[str, Any],
    flight: str,
    *,
    provider_id: str = "",
    preferred_leg: str = "",
) -> dict[str, Any]:
    """Match a callsign to an airport board row."""
    if not is_airport_board_provider(provider_id):
        return {}
    token = flight.strip().replace(" ", "").upper()
    match = re.fullmatch(r"([A-Z]{2,3})([A-Z0-9]+)", token)
    if not match:
        return {}
    prefix, number = match.groups()
    provider = AIRPORT_BOARD_PROVIDERS_BY_ID.get(provider_id)
    prefix_map = provider.callsign_prefix_to_board_airline if provider else {}
    board_airline = (prefix_map or {}).get(prefix, prefix)
    rows = (((payload.get("data") or {}).get("flights")) or [])
    if not isinstance(rows, list):
        return {}
    matches: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("flightNumber") or "").strip().upper().lstrip("0") != number.lstrip(
            "0"
        ):
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


def airport_board_city(data: dict[str, Any], key: str) -> str:
    """Return a compact city label from provider path data."""
    value = str(data.get(f"{key}En") or data.get(f"{key}Iata") or "").strip()
    if not value:
        return ""
    city = normalized_airport_city(value)
    iata = str(data.get(f"{key}Iata") or "").strip()
    return f"{city} ({iata})" if iata and iata not in city else city
