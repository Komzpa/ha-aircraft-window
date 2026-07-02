"""Built-in callsign and route fallback tables for Aircraft Window."""

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
