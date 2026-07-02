"""Built-in callsign and route fallback tables for Aircraft Window."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROUTE_FALLBACKS_DATA_FILE = "data/route_fallbacks_ru.json"


def _string_map(raw: Any) -> dict[str, str]:
    """Return a normalized string map from package data."""
    if not isinstance(raw, dict):
        return {}
    return {
        str(key).strip().upper(): str(value).strip()
        for key, value in raw.items()
        if str(key).strip() and str(value).strip()
    }


def _route_map(raw: Any) -> dict[str, dict[str, str]]:
    """Return a normalized callsign-to-route map from package data."""
    if not isinstance(raw, dict):
        return {}
    routes: dict[str, dict[str, str]] = {}
    for callsign, route in raw.items():
        token = str(callsign).strip().upper()
        if not token or not isinstance(route, dict):
            continue
        route_values = {
            str(key).strip(): str(value).strip()
            for key, value in route.items()
            if str(key).strip() and str(value).strip()
        }
        if route_values:
            routes[token] = route_values
    return routes


def load_route_fallbacks_from_data_file(
    filename: str = ROUTE_FALLBACKS_DATA_FILE,
) -> RouteFallbacks:
    """Load built-in route fallback tables from packaged data."""
    raw_text = (Path(__file__).resolve().parent / filename).read_text(encoding="utf-8")
    raw_data = json.loads(raw_text)
    if not isinstance(raw_data, dict):
        return RouteFallbacks(airline_by_callsign_prefix={}, route_by_callsign={})
    return RouteFallbacks(
        airline_by_callsign_prefix=_string_map(
            raw_data.get("airline_by_callsign_prefix"),
        ),
        route_by_callsign=_route_map(raw_data.get("route_by_callsign")),
    )


@dataclass(frozen=True, slots=True)
class RouteFallbacks:
    """Known route and airline fallbacks for public API gaps."""

    airline_by_callsign_prefix: dict[str, str]
    route_by_callsign: dict[str, dict[str, str]]

    def with_overrides(
        self,
        *,
        airline_by_callsign_prefix: dict[str, str] | None = None,
        route_by_callsign: dict[str, dict[str, str]] | None = None,
    ) -> RouteFallbacks:
        """Return fallbacks with user-maintained override tables merged in."""
        return RouteFallbacks(
            airline_by_callsign_prefix={
                **self.airline_by_callsign_prefix,
                **(airline_by_callsign_prefix or {}),
            },
            route_by_callsign={
                **self.route_by_callsign,
                **(route_by_callsign or {}),
            },
        )


DEFAULT_ROUTE_FALLBACKS = load_route_fallbacks_from_data_file()
