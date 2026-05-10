"""Aircraft detection and enrichment logic for Aircraft Window."""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any

CITY_FROM_RU = {
    "Almaty": "Алматы",
    "Amman": "Аммана",
    "Astana": "Астаны",
    "Baku": "Баку",
    "Batumi": "Батуми",
    "Dubai": "Дубая",
    "Erbil": "Эрбиля",
    "Istanbul": "Стамбула",
    "Jeddah": "Джидды",
    "Kazan": "Казани",
    "Kopitnari": "Кутаиси",
    "Larnaca": "Ларнаки",
    "Minsk": "Минска",
    "Moscow": "Москвы",
    "Natakhtari": "Натахтари",
    "Riga": "Риги",
    "Riyadh": "Эр-Рияда",
    "Shiraz": "Шираза",
    "Sochi": "Сочи",
    "Tashkent": "Ташкента",
    "Tbilisi": "Тбилиси",
    "Tehran": "Тегерана",
    "Tel Aviv": "Тель-Авива",
    "Yerevan": "Еревана",
}

CITY_TO_RU = {
    "Almaty": "Алматы",
    "Amman": "Амман",
    "Astana": "Астану",
    "Baku": "Баку",
    "Batumi": "Батуми",
    "Dubai": "Дубай",
    "Erbil": "Эрбиль",
    "Istanbul": "Стамбул",
    "Jeddah": "Джидду",
    "Kazan": "Казань",
    "Kopitnari": "Кутаиси",
    "Larnaca": "Ларнаку",
    "Minsk": "Минск",
    "Moscow": "Москву",
    "Natakhtari": "Натахтари",
    "Riga": "Ригу",
    "Riyadh": "Эр-Рияд",
    "Shiraz": "Шираз",
    "Sochi": "Сочи",
    "Tashkent": "Ташкент",
    "Tbilisi": "Тбилиси",
    "Tehran": "Тегеран",
    "Tel Aviv": "Тель-Авив",
    "Yerevan": "Ереван",
}

AIRLINE_SPEECH_RU = {
    "Air Astana": "Эйр Астана",
    "Air Baltic": "Эйр Балтик",
    "Arkia Israel Airlines": "Аркия",
    "Arkia Israeli Airlines": "Аркия",
    "Armenian Airlines": "Армениан Эйрлайнс",
    "Azerbaijan Airlines": "Азербайджанские авиалинии",
    "Azerbaijan Airlines (Buta Airways)": "Азербайджанские авиалинии",
    "Azimuth Airlines": "Азимут",
    "Belavia": "Белавиа",
    "Centrum Air": "Центрум Эйр",
    "El-Al Israel Airlines": "Эль Аль",
    "El Al": "Эль Аль",
    "FlyArystan": "Флай Арыстан",
    "flydubai": "Флай Дубай",
    "Flydubai": "Флай Дубай",
    "Fly Lili": "Флай Лили",
    "Flynas": "Флай Нас",
    "FlyOne Armenia": "Флай Уан Армения",
    "Georgian Wings": "Джорджиан Вингс",
    "Iran Aseman Airlines": "Иран Асеман",
    "Iraq Airways": "Иракские авиалинии",
    "Israir": "Исра Эйр",
    "Israir Airlines": "Исра Эйр",
    "Jazeera Airways": "Джазира",
    "Jordan Aviation": "Джордан Авиейшен",
    "Kish Air": "Киш Эйр",
    "Pars Air": "Парс Эйр",
    "Pegasus Airlines": "Пегасус",
    "Qeshm Air": "Кешм Эйр",
    "Red Wings": "Ред Вингс",
    "SCAT Airlines": "Скат",
    "Scat": "Скат",
    "Turkish Airlines": "Туркиш",
    "Uzbekistan Airways": "Узбекистон",
    "Varesh Airlines": "Вареш",
    "Van Air Europe": "Ван Эйр Европа",
    "Wizz Air": "Визз Эйр",
}

KNOWN_AIRLINE_BY_CALLSIGN_PREFIX = {
    "VAA": "Van Air Europe",
}

MILITARY_OPERATOR_SPEECH_RU = {
    "PLF": "Польские ВВС",
    "RCH": "военный транспорт США",
    "RRR": "Королевские ВВС",
    "ASY": "австралийские ВВС",
    "IAM": "итальянские ВВС",
    "GAF": "немецкие ВВС",
    "FAF": "французские ВВС",
    "AME": "испанские ВВС",
    "THK": "турецкие ВВС",
}

MILITARY_OWNER_TOKENS = (
    "air force",
    "airforce",
    "army",
    "navy",
    "military",
    "defence",
    "defense",
    "ministerio de defensa",
    "nato",
)

MILITARY_TYPE_CODES = {
    "A124",
    "A225",
    "A400",
    "C130",
    "C160",
    "C17",
    "C295",
    "E3CF",
    "IL76",
    "K35R",
    "K35A",
    "P8",
    "T154",
}

DIGIT_RU = {
    "0": "ноль",
    "1": "один",
    "2": "два",
    "3": "три",
    "4": "четыре",
    "5": "пять",
    "6": "шесть",
    "7": "семь",
    "8": "восемь",
    "9": "девять",
}

YEAR_RU = {
    1990: "тысяча девятьсот девяностого года",
    2000: "двухтысячного года",
    2001: "две тысячи первого года",
    2002: "две тысячи второго года",
    2003: "две тысячи третьего года",
    2004: "две тысячи четвёртого года",
    2005: "две тысячи пятого года",
    2006: "две тысячи шестого года",
    2007: "две тысячи седьмого года",
    2008: "две тысячи восьмого года",
    2009: "две тысячи девятого года",
    2010: "две тысячи десятого года",
    2011: "две тысячи одиннадцатого года",
    2012: "две тысячи двенадцатого года",
    2013: "две тысячи тринадцатого года",
    2014: "две тысячи четырнадцатого года",
    2015: "две тысячи пятнадцатого года",
    2016: "две тысячи шестнадцатого года",
    2017: "две тысячи семнадцатого года",
    2018: "две тысячи восемнадцатого года",
    2019: "две тысячи девятнадцатого года",
    2020: "две тысячи двадцатого года",
    2021: "две тысячи двадцать первого года",
    2022: "две тысячи двадцать второго года",
    2023: "две тысячи двадцать третьего года",
    2024: "две тысячи двадцать четвёртого года",
    2025: "две тысячи двадцать пятого года",
    2026: "две тысячи двадцать шестого года",
}

KNOWN_BUILT_YEAR_BY_REGISTRATION: dict[str, int] = {
    "OK-VAA": 1990,
}


@dataclass(slots=True)
class AircraftCandidate:
    """Current aircraft candidate exposed by the integration."""

    state: str = "idle"
    phase: str = "idle"
    confidence: float = 0.0
    confidence_reason: str = "not updated yet"
    event_key: str = ""
    hex: str = ""
    flight: str = ""
    announcement: str = ""
    lat: float | None = None
    lon: float | None = None
    altitude_ft: float | None = None
    vertical_rate_fpm: float | None = None
    ground_speed_kt: float | None = None
    track: float | None = None
    distance_km: float | None = None
    position_source: str = ""
    position_age_seconds: float | None = None
    seen: float | None = None
    seen_pos: float | None = None
    rssi: float | None = None
    messages: float | None = None
    aircraft_count: int = 0
    source: str = ""
    airline_name: str = ""
    origin_iata: str = ""
    origin_name: str = ""
    origin_speech: str = ""
    destination_iata: str = ""
    destination_name: str = ""
    destination_speech: str = ""
    route_summary: str = ""
    aircraft_model: str = ""
    aircraft_type: str = ""
    aircraft_model_speech: str = ""
    registration: str = ""
    registered_owner: str = ""
    operator_flag_code: str = ""
    owner_country: str = ""
    built_year: int | None = None
    built_year_speech: str = ""
    enrichment_source: str = ""
    interest_reason: str = ""
    novelty_reason: str = ""
    unusual_aircraft: bool = False
    spoken_flight: str = ""
    updated_at: int = field(default_factory=lambda: int(time.time()))

    @property
    def active(self) -> bool:
        """Return true when the candidate is a real event."""
        return self.state != "idle"

    def as_dict(self) -> dict[str, Any]:
        """Return state attributes."""
        return {
            key: getattr(self, key)
            for key in self.__dataclass_fields__
            if key != "state"
        }


def parse_float(value: Any) -> float | None:
    """Parse a finite float from dump1090 data."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def altitude_ft(aircraft: dict[str, Any]) -> float | None:
    """Extract barometric or geometric altitude in feet."""
    for key in ("alt_baro", "alt_geom"):
        value = aircraft.get(key)
        if value == "ground":
            return 0.0
        number = parse_float(value)
        if number is not None:
            return number
    return None


def backfill_position_from_history(
    aircraft: dict[str, Any],
    history_payloads: list[dict[str, Any]],
    *,
    max_age_seconds: float = 120.0,
) -> dict[str, Any]:
    """Copy a recent position for the same hex from local SkyAware history."""
    if aircraft.get("lat") is not None and aircraft.get("lon") is not None:
        return aircraft
    hex_id = str(aircraft.get("hex") or "").strip().lower()
    if not hex_id:
        return aircraft

    best: tuple[float, dict[str, Any], float] | None = None
    for payload in history_payloads:
        snapshot_now = parse_float(payload.get("now"))
        rows = payload.get("aircraft")
        if snapshot_now is None or not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("hex") or "").strip().lower() != hex_id:
                continue
            lat = parse_float(row.get("lat"))
            lon = parse_float(row.get("lon"))
            seen_pos = parse_float(row.get("seen_pos")) or 0.0
            if lat is None or lon is None or seen_pos > max_age_seconds:
                continue
            position_time = snapshot_now - seen_pos
            if best is None or position_time > best[0]:
                best = (position_time, row, seen_pos)

    if best is None:
        return aircraft
    _, row, position_age = best
    merged = dict(aircraft)
    for key in ("lat", "lon", "nav_heading", "track", "gs", "alt_baro", "alt_geom"):
        if merged.get(key) is None and row.get(key) is not None:
            merged[key] = row[key]
    merged["seen_pos"] = row.get("seen_pos")
    merged["position_source"] = "skyaware_history"
    merged["position_age_seconds"] = round(position_age, 1)
    return merged


def vertical_rate_fpm(aircraft: dict[str, Any]) -> float | None:
    """Extract vertical rate in feet per minute."""
    for key in ("baro_rate", "geom_rate"):
        number = parse_float(aircraft.get(key))
        if number is not None:
            return number
    return None


def flight_label(aircraft: dict[str, Any]) -> str:
    """Return a human fallback flight label."""
    flight = str(aircraft.get("flight") or "").strip()
    return flight or str(aircraft.get("hex") or "").strip() or "unknown"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in kilometres."""
    radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    )
    return 2.0 * radius_km * math.asin(math.sqrt(a))


def make_key(aircraft: dict[str, Any], phase: str) -> str:
    """Make a stable event key for deduplication in automations."""
    hex_id = str(aircraft.get("hex") or "unknown").strip().lower()
    flight = flight_label(aircraft).replace(" ", "")
    return f"{phase}:{hex_id}:{flight}"[:240]


def candidate_airframe_key(candidate: AircraftCandidate) -> str:
    """Return a stable key for follow-up announcements about the same aircraft pass."""
    if candidate.hex:
        return f"{candidate.phase}:{candidate.hex.strip().lower()}"
    return candidate.event_key


def _is_hex_token(value: str) -> bool:
    """Return true when a flight label is just the transponder hex fallback."""
    token = value.strip().lower()
    return bool(token) and bool(re.fullmatch(r"[0-9a-f]{6}", token))


def candidate_has_real_flight(candidate: AircraftCandidate) -> bool:
    """Return true when the candidate has a real callsign, not a hex fallback."""
    flight = candidate.flight.strip()
    return bool(flight) and not _is_hex_token(flight)


def is_military_aircraft(enrichment: dict[str, Any]) -> bool:
    """Return true when public owner/type metadata suggests a military aircraft."""
    owner = str(
        enrichment.get("registered_owner") or enrichment.get("airline_name") or ""
    ).lower()
    operator = str(enrichment.get("operator_flag_code") or "").upper()
    aircraft_type = str(enrichment.get("aircraft_type") or "").upper()
    model = str(enrichment.get("aircraft_model") or "").upper()
    if operator in MILITARY_OPERATOR_SPEECH_RU:
        return True
    if any(token in owner for token in MILITARY_OWNER_TOKENS):
        return True
    return aircraft_type in MILITARY_TYPE_CODES or any(
        code in model for code in MILITARY_TYPE_CODES
    )


def military_operator_speech(enrichment: dict[str, Any]) -> str:
    """Return a Russian label for a military operator when known."""
    operator = str(enrichment.get("operator_flag_code") or "").upper()
    if operator in MILITARY_OPERATOR_SPEECH_RU:
        return MILITARY_OPERATOR_SPEECH_RU[operator]
    owner = str(enrichment.get("registered_owner") or "").strip()
    return owner


def spoken_flight(flight: str, airline_icao: str = "", airline_iata: str = "") -> str:
    """Turn AIZ414/RWZ553 into a short TTS-friendly flight number."""
    token = flight.strip().replace(" ", "").upper()
    for prefix in (airline_icao.strip().upper(), airline_iata.strip().upper()):
        if prefix and token.startswith(prefix):
            token = token[len(prefix):]
            break
    if token and token.isdigit():
        return " ".join(DIGIT_RU.get(char, char) for char in token)
    if len(token) > 3 and token[:3].isalpha() and token[3:].isdigit():
        return " ".join(DIGIT_RU.get(char, char) for char in token[3:])
    return flight.strip()


def known_airline_for_callsign(flight: str) -> tuple[str, str]:
    """Return known airline name and callsign prefix for route API gaps."""
    token = flight.strip().replace(" ", "").upper()
    for prefix, airline_name in KNOWN_AIRLINE_BY_CALLSIGN_PREFIX.items():
        if token.startswith(prefix):
            return airline_name, prefix
    return "", ""


def spoken_model(model: str, aircraft_type: str = "") -> str:
    """Turn common aircraft model strings into Russian TTS-friendly text."""
    text = f"{model} {aircraft_type}".upper()
    if "TU-204" in text or "T204" in text:
        return "Ту-двести четыре"
    if "TU-214" in text or "T214" in text:
        return "Ту-двести четырнадцать"
    if "A220" in text or "BCS3" in text or "BCS1" in text:
        return "Аэробус A-двести двадцать"
    if "A19N" in text or "A319" in text:
        return "Аэробус триста девятнадцать"
    if "A20N" in text or "A320" in text:
        return "Аэробус триста двадцать"
    if "A21N" in text or "A321" in text:
        return "Аэробус триста двадцать один"
    if "A332" in text or "A330" in text:
        return "Аэробус триста тридцать"
    if "B38M" in text or "737 MAX 8" in text or "737-8" in text:
        return "Боинг семьсот тридцать семь MAX восемь"
    if "B39M" in text or "737 MAX 9" in text or "737-9" in text:
        return "Боинг семьсот тридцать семь MAX девять"
    if "B737" in text or "B738" in text or "B739" in text or "737" in text:
        return "Боинг семьсот тридцать семь"
    if "B752" in text or "757" in text:
        return "Боинг семьсот пятьдесят семь"
    if "B763" in text or "767" in text:
        return "Боинг семьсот шестьдесят семь"
    if "E190" in text:
        return "Эмбраер сто девяносто"
    if "E195" in text:
        return "Эмбраер сто девяносто пять"
    if "E170" in text or "E75" in text:
        return "Эмбраер сто семьдесят"
    if "CRJ" in text:
        return "Си-ар-джей"
    if "SU95" in text or "SSJ" in text:
        return "Суперджет"
    if "C208" in text or "CARAVAN" in text:
        return "Цессна Караван"
    if "L410" in text or "LET" in text:
        return "Лет четыреста десять Турболет, небольшой двухмоторный турбовинтовой"
    return model.strip()


def spoken_year(year: int | None) -> str:
    """Return a Russian TTS-friendly year phrase."""
    if year is None:
        return ""
    return YEAR_RU.get(year, f"{year} года")


def airport_label(airport: dict[str, Any] | None) -> str:
    """Return a short airport label."""
    if not isinstance(airport, dict):
        return ""
    code = str(airport.get("iata_code") or airport.get("icao_code") or "").strip()
    municipality = str(airport.get("municipality") or "").strip()
    name = str(airport.get("name") or "").strip()
    if code and municipality:
        return f"{municipality} ({code})"
    return municipality or code or name


def airport_speech(airport: dict[str, Any] | None, *, direction: str) -> str:
    """Return a TTS-friendly city name for origin/destination."""
    if not isinstance(airport, dict):
        return ""
    municipality = str(airport.get("municipality") or "").strip()
    city_map = CITY_TO_RU if direction == "to" else CITY_FROM_RU
    if municipality in city_map:
        return city_map[municipality]
    return municipality or str(airport.get("iata_code") or airport.get("icao_code") or "").strip()


def novelty_reason(enrichment: dict[str, Any], phase: str) -> str:
    """Return why a candidate should be announced as unusual."""
    reasons: list[str] = []
    airline_name = str(enrichment.get("airline_name") or "").strip()
    if airline_name and airline_name not in AIRLINE_SPEECH_RU:
        reasons.append(f"новая авиакомпания {airline_name}")
    model = str(enrichment.get("aircraft_model") or enrichment.get("aircraft_type") or "").strip()
    model_speech = str(enrichment.get("aircraft_model_speech") or "").strip()
    if model and (not model_speech or model_speech == model):
        reasons.append(f"новый тип {model}")
    if phase == "no_position_nearby" and not model and not airline_name:
        reasons.append("самолёт без координат и без справочных данных")
    return "; ".join(reasons)


def build_announcement(
    aircraft: dict[str, Any],
    phase: str,
    confidence: float,
    enrichment: dict[str, Any],
) -> str:
    """Build the short spoken announcement."""
    label = flight_label(aircraft)
    airline_name = str(enrichment.get("airline_name") or "").strip()
    airline = AIRLINE_SPEECH_RU.get(airline_name, airline_name)
    model = str(
        enrichment.get("aircraft_model_speech")
        or enrichment.get("aircraft_model")
        or enrichment.get("aircraft_type")
        or ""
    ).strip()
    built_year = str(enrichment.get("built_year_speech") or "").strip()
    origin = str(enrichment.get("origin_speech") or enrichment.get("origin_name") or "").strip()
    destination = str(
        enrichment.get("destination_speech") or enrichment.get("destination_name") or ""
    ).strip()
    flight_number = str(enrichment.get("spoken_flight") or label).strip()

    if phase == "military_visible":
        base = "Военный самолёт в зоне видимости"
    elif phase == "kutaisi_route":
        if str(enrichment.get("destination_iata") or "").upper() == "KUT":
            base = "Информация для наблюдения: рейс на Кутаиси"
        elif str(enrichment.get("origin_iata") or "").upper() == "KUT":
            base = "Информация для наблюдения: рейс из Кутаиси"
        else:
            base = "Информация для наблюдения: рейс через Кутаиси"
    elif phase == "no_position_nearby":
        base = "Рядом самолёт без координат"
    elif phase == "positioned_approach":
        base = "Заходит на посадку"
    elif phase == "positioned_landing":
        base = "Заходит на посадку"
    elif phase == "positioned_takeoff":
        base = "Вылетает"
    elif phase == "positioned_low_nearby":
        base = "Самолёт рядом"
    else:
        base = "Самолёт"

    if phase == "military_visible":
        operator = military_operator_speech(enrichment)
        subject = " ".join(part for part in [operator, flight_number] if part)
    else:
        subject = " ".join(part for part in [airline, flight_number] if part)
    if phase in {"positioned_approach", "positioned_landing", "positioned_takeoff"}:
        sentence = f"{base} рейс {subject or label}."
    else:
        sentence = f"{base}: {subject or label}."
    reason = novelty_reason(enrichment, phase)
    if reason:
        sentence = f"Особое объявление. {sentence}"

    extra: list[str] = []
    if phase == "military_visible":
        route = str(enrichment.get("route_summary") or "").strip()
        if route:
            extra.append(route)
    elif phase == "kutaisi_route":
        if origin and destination:
            extra.append(f"{origin} - {destination}")
    elif phase == "no_position_nearby":
        extra.append("локальный приём сильный")
        if origin and destination:
            extra.append(f"{origin} - {destination}")
    elif phase in {"positioned_approach", "positioned_landing"} and origin:
        extra.append(f"Из {origin}")
    elif phase == "positioned_takeoff" and destination:
        extra.append(f"В {destination}")
    elif origin and destination:
        extra.append(f"{origin} - {destination}")
    if model:
        extra.append(model)
    if built_year:
        extra.append(built_year)
    if extra:
        sentence = f"{sentence} {', '.join(extra)}."
    return sentence


def build_followup_announcement(
    previous: AircraftCandidate,
    current: AircraftCandidate,
) -> str:
    """Build a short update when more details arrive after the first sighting."""
    if candidate_airframe_key(previous) != candidate_airframe_key(current):
        return ""

    details: list[str] = []
    if (
        candidate_has_real_flight(current)
        and (
            current.flight != previous.flight
            or (current.airline_name and current.airline_name != previous.airline_name)
        )
    ):
        airline = AIRLINE_SPEECH_RU.get(current.airline_name, current.airline_name)
        flight = current.spoken_flight or current.flight
        identity = " ".join(part for part in [airline, flight] if part)
        if identity:
            details.append(f"это {identity}")

    if current.phase == "positioned_landing":
        route = current.origin_speech or current.origin_name
        if route and route != (previous.origin_speech or previous.origin_name):
            details.append(f"из {route}")
    elif current.phase == "positioned_takeoff":
        route = current.destination_speech or current.destination_name
        if route and route != (previous.destination_speech or previous.destination_name):
            details.append(f"в {route}")
    else:
        origin = current.origin_speech or current.origin_name
        destination = current.destination_speech or current.destination_name
        if origin and destination and (
            origin != (previous.origin_speech or previous.origin_name)
            or destination != (previous.destination_speech or previous.destination_name)
        ):
            details.append(f"{origin} - {destination}")

    model = current.aircraft_model_speech or current.aircraft_model or current.aircraft_type
    previous_model = (
        previous.aircraft_model_speech or previous.aircraft_model or previous.aircraft_type
    )
    if model and model != previous_model:
        details.append(model)

    if current.built_year_speech and current.built_year_speech != previous.built_year_speech:
        details.append(current.built_year_speech)

    if not details:
        return ""
    return f"Дополнение: {', '.join(details)}."


def idle_candidate(reason: str, *, source: str = "", aircraft_count: int = 0) -> AircraftCandidate:
    """Return an idle candidate."""
    return AircraftCandidate(
        confidence_reason=reason,
        source=source,
        aircraft_count=aircraft_count,
    )


def positioned_candidate(
    aircraft: dict[str, Any],
    *,
    home_latitude: float,
    home_longitude: float,
    max_distance_km: float,
    max_approach_distance_km: float,
    max_approach_altitude_ft: float,
) -> dict[str, Any] | None:
    """Classify a positioned aircraft near home."""
    lat = parse_float(aircraft.get("lat"))
    lon = parse_float(aircraft.get("lon"))
    if lat is None or lon is None:
        return None

    seen = parse_float(aircraft.get("seen")) or 999.0
    seen_pos = parse_float(aircraft.get("seen_pos")) or 999.0
    if seen > 8.0 or seen_pos > 12.0:
        return None

    distance_km = haversine_km(home_latitude, home_longitude, lat, lon)
    if distance_km > max(max_distance_km, max_approach_distance_km):
        return None

    altitude = altitude_ft(aircraft)
    vertical_rate = vertical_rate_fpm(aircraft)
    ground_speed = parse_float(aircraft.get("gs"))
    rssi = parse_float(aircraft.get("rssi"))
    if altitude is None:
        return None

    phase = None
    confidence = 0.0
    reason_parts = [f"position {distance_km:.1f} km from home", f"alt {altitude:.0f} ft"]

    if altitude <= 2800 and vertical_rate is not None and vertical_rate <= -160:
        phase = "positioned_landing"
        confidence = 0.62
        reason_parts.append(f"descending {vertical_rate:.0f} fpm")
    elif altitude <= 3200 and vertical_rate is not None and vertical_rate >= 160:
        phase = "positioned_takeoff"
        confidence = 0.62
        reason_parts.append(f"climbing {vertical_rate:.0f} fpm")
    elif altitude <= 900 and ground_speed is not None and 35 <= ground_speed <= 190:
        phase = "positioned_low_nearby"
        confidence = 0.52
        reason_parts.append(f"low nearby at {ground_speed:.0f} kt")
    elif (
        distance_km <= max_approach_distance_km
        and altitude <= max_approach_altitude_ft
        and vertical_rate is not None
        and vertical_rate <= -160
    ):
        phase = "positioned_approach"
        confidence = 0.55
        reason_parts.append(f"approach descent {vertical_rate:.0f} fpm")

    if phase is None:
        return None

    if distance_km <= 3.0:
        confidence += 0.15
    elif distance_km <= 5.0:
        confidence += 0.08
    elif phase == "positioned_approach" and distance_km <= 20.0:
        confidence += 0.07
    elif phase == "positioned_approach" and distance_km <= 40.0:
        confidence += 0.03
    if altitude <= 1200:
        confidence += 0.1
    if rssi is not None and rssi >= -8.0:
        confidence += 0.05

    return {
        "phase": phase,
        "confidence": round(min(confidence, 0.95), 3),
        "distance_km": round(distance_km, 3),
        "reason": "; ".join(reason_parts),
    }


def no_position_candidate(
    aircraft: dict[str, Any],
    *,
    max_seen_seconds: float,
) -> dict[str, Any] | None:
    """Classify a recent no-position aircraft with strong local receiver evidence."""
    if (
        parse_float(aircraft.get("lat")) is not None
        and parse_float(aircraft.get("lon")) is not None
    ):
        return None

    seen = parse_float(aircraft.get("seen")) or 999.0
    if seen > max_seen_seconds:
        return None

    rssi = parse_float(aircraft.get("rssi"))
    messages = parse_float(aircraft.get("messages")) or 0.0
    altitude = altitude_ft(aircraft)
    flight = str(aircraft.get("flight") or "").strip()

    confidence = 0.0
    reason_parts = ["no coordinates from transponder"]
    if rssi is not None:
        reason_parts.append(f"rssi {rssi:.1f} dBFS")
        if rssi >= -5.0:
            confidence += 0.45
        elif rssi >= -9.0:
            confidence += 0.35
        elif rssi >= -13.0:
            confidence += 0.25

    if altitude is not None and altitude <= 2500:
        confidence += 0.22
        reason_parts.append(f"low alt {altitude:.0f} ft")
    elif altitude is not None:
        reason_parts.append(f"alt {altitude:.0f} ft")
    if flight:
        confidence += 0.08
        reason_parts.append(f"callsign {flight}")
    if messages >= 20:
        confidence += 0.05
        reason_parts.append(f"{messages:.0f} messages")

    if confidence < 0.42:
        return None

    return {
        "phase": "no_position_nearby",
        "confidence": round(min(confidence, 0.72), 3),
        "distance_km": None,
        "reason": "; ".join(reason_parts),
    }


def interest_candidate(
    aircraft: dict[str, Any],
    *,
    enrichment: dict[str, Any],
    source: str,
    aircraft_count: int,
) -> AircraftCandidate | None:
    """Classify route and military aircraft visible in receiver range."""
    seen = parse_float(aircraft.get("seen")) or 999.0
    seen_pos = parse_float(aircraft.get("seen_pos"))
    if seen > 20.0 and (seen_pos is None or seen_pos > 60.0):
        return None

    phase = ""
    confidence = 0.0
    reason = ""
    origin_iata = str(enrichment.get("origin_iata") or "").upper()
    destination_iata = str(enrichment.get("destination_iata") or "").upper()
    if is_military_aircraft(enrichment):
        phase = "military_visible"
        confidence = 0.86
        operator = military_operator_speech(enrichment) or "unknown operator"
        reason = f"military metadata: {operator}"
    elif "KUT" in {origin_iata, destination_iata}:
        phase = "kutaisi_route"
        confidence = 0.64
        reason = f"route includes KUT: {origin_iata or '?'}-{destination_iata or '?'}"

    if not phase:
        return None
    if seen <= 5.0:
        confidence += 0.04
    if seen_pos is not None and seen_pos <= 20.0:
        confidence += 0.03
    classifier = {
        "phase": phase,
        "confidence": round(min(confidence, 0.95), 3),
        "distance_km": None,
        "reason": reason,
    }
    return candidate_from_aircraft(
        aircraft,
        classifier,
        source=source,
        aircraft_count=aircraft_count,
        enrichment=enrichment,
    )


def candidate_from_aircraft(
    aircraft: dict[str, Any],
    classifier: dict[str, Any],
    *,
    source: str,
    aircraft_count: int,
    enrichment: dict[str, Any],
) -> AircraftCandidate:
    """Build the dataclass from aircraft row, classifier, and enrichment."""
    phase = str(classifier["phase"])
    confidence = float(classifier["confidence"])
    reason = novelty_reason(enrichment, phase)
    if enrichment:
        enrichment["novelty_reason"] = reason
        enrichment["unusual_aircraft"] = bool(reason)
        enrichment["interest_reason"] = str(classifier.get("reason") or "")
    announcement = build_announcement(aircraft, phase, confidence, enrichment)

    return AircraftCandidate(
        state=make_key(aircraft, phase),
        phase=phase,
        confidence=confidence,
        confidence_reason=str(classifier["reason"]),
        event_key=make_key(aircraft, phase),
        hex=str(aircraft.get("hex") or ""),
        flight=flight_label(aircraft),
        announcement=announcement,
        lat=parse_float(aircraft.get("lat")),
        lon=parse_float(aircraft.get("lon")),
        altitude_ft=altitude_ft(aircraft),
        vertical_rate_fpm=vertical_rate_fpm(aircraft),
        ground_speed_kt=parse_float(aircraft.get("gs")),
        track=parse_float(aircraft.get("track")),
        distance_km=classifier["distance_km"],
        position_source=str(aircraft.get("position_source") or ""),
        position_age_seconds=parse_float(aircraft.get("position_age_seconds")),
        seen=parse_float(aircraft.get("seen")),
        seen_pos=parse_float(aircraft.get("seen_pos")),
        rssi=parse_float(aircraft.get("rssi")),
        messages=parse_float(aircraft.get("messages")),
        aircraft_count=aircraft_count,
        source=source,
        **enrichment,
    )


def pick_candidate(
    aircraft_rows: list[dict[str, Any]],
    *,
    home_latitude: float,
    home_longitude: float,
    max_positioned_distance_km: float,
    max_approach_distance_km: float,
    max_approach_altitude_ft: float,
    max_no_position_seen_seconds: float,
    source: str,
    enrich: Any | None = None,
) -> AircraftCandidate:
    """Pick the best current aircraft candidate."""
    best: tuple[float, dict[str, Any], dict[str, Any]] | None = None
    for aircraft in aircraft_rows:
        classifier = positioned_candidate(
            aircraft,
            home_latitude=home_latitude,
            home_longitude=home_longitude,
            max_distance_km=max_positioned_distance_km,
            max_approach_distance_km=max_approach_distance_km,
            max_approach_altitude_ft=max_approach_altitude_ft,
        )
        if classifier is None:
            classifier = no_position_candidate(
                aircraft,
                max_seen_seconds=max_no_position_seen_seconds,
            )
        if classifier is None:
            continue
        score = float(classifier["confidence"])
        if best is None or score > best[0]:
            best = (score, aircraft, classifier)

    if best is None:
        return idle_candidate(
            "no nearby landing/takeoff candidate",
            source=source,
            aircraft_count=len(aircraft_rows),
        )

    _, aircraft, classifier = best
    enrichment = enrich(aircraft) if enrich is not None else {}
    return candidate_from_aircraft(
        aircraft,
        classifier,
        source=source,
        aircraft_count=len(aircraft_rows),
        enrichment=enrichment,
    )


def extract_airport_data_year(html: str) -> int | None:
    """Extract airport-data.com built year from an aircraft HTML page."""
    match = re.search(r"<b>Year built:</b></td><td>(\d{4})</td>", html)
    return int(match.group(1)) if match else None
