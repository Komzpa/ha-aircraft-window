"""Built-in callsign and route fallback tables for Aircraft Window."""

from __future__ import annotations

from dataclasses import dataclass

KNOWN_AIRLINE_BY_CALLSIGN_PREFIX = {
    "4L": "OneClick Airways",
    "TGZ": "Georgian Airways",
    "VAA": "Van Air Europe",
    "JZR": "Jazeera Airways",
}

KNOWN_ROUTE_BY_CALLSIGN = {
    "VAA020": {
        "airline_name": "Vanilla Sky",
        "origin_iata": "",
        "origin_name": "Natakhtari",
        "origin_speech": "Натахтари",
        "destination_iata": "BUS",
        "destination_name": "Batumi (BUS)",
        "destination_speech": "Батуми",
        "route_summary": "Natakhtari → BUS",
        "route_source": "vanilla_sky_schedule",
        "scheduled_departure_local": "12:30",
    },
    "VAA021": {
        "airline_name": "Vanilla Sky",
        "origin_iata": "BUS",
        "origin_name": "Batumi (BUS)",
        "origin_speech": "Батуми",
        "destination_iata": "",
        "destination_name": "Natakhtari",
        "destination_speech": "Натахтари",
        "route_summary": "BUS → Natakhtari",
        "route_source": "vanilla_sky_schedule",
        "scheduled_departure_local": "14:00",
    },
}


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


DEFAULT_ROUTE_FALLBACKS = RouteFallbacks(
    airline_by_callsign_prefix=KNOWN_AIRLINE_BY_CALLSIGN_PREFIX,
    route_by_callsign=KNOWN_ROUTE_BY_CALLSIGN,
)
