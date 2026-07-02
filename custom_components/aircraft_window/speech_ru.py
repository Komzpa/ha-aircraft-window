"""Built-in Russian speech tables for Aircraft Window."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SPEECH_RU_AIRPORTS_DATA_FILE = "data/speech_ru_airports.json"
SPEECH_RU_AIRLINES_DATA_FILE = "data/speech_ru_airlines.json"
SPEECH_RU_MILITARY_DATA_FILE = "data/speech_ru_military.json"
SPEECH_RU_MODELS_DATA_FILE = "data/speech_ru_models.json"


def _load_speech_data_file(filename: str) -> Any:
    """Load one packaged speech data JSON file."""
    raw_text = (Path(__file__).resolve().parent / filename).read_text(encoding="utf-8")
    return json.loads(raw_text)


def _speech_string_map(raw: Any, *, fold_keys: bool = False) -> dict[str, str]:
    """Return a string-to-string speech map loaded from packaged data."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        normalized_key = str(key).strip()
        normalized_value = str(value).strip()
        if not normalized_key or not normalized_value:
            continue
        if fold_keys:
            normalized_key = normalized_key.casefold()
        result[normalized_key] = normalized_value
    return result


def load_airport_speech_data(
    filename: str = SPEECH_RU_AIRPORTS_DATA_FILE,
) -> tuple[
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, str],
]:
    """Load built-in Russian airport and city speech tables from packaged data."""
    raw_data = _load_speech_data_file(filename)
    if not isinstance(raw_data, dict):
        return {}, {}, {}, {}, {}, {}, {}, {}
    return (
        _speech_string_map(raw_data.get("city_from")),
        _speech_string_map(raw_data.get("city_to")),
        _speech_string_map(raw_data.get("city_route")),
        _speech_string_map(raw_data.get("airport_code_from")),
        _speech_string_map(raw_data.get("airport_code_to")),
        _speech_string_map(raw_data.get("airport_code_route")),
        _speech_string_map(raw_data.get("airport_detail")),
        _speech_string_map(raw_data.get("airport_name_detail")),
    )


(
    CITY_FROM_RU,
    CITY_TO_RU,
    CITY_ROUTE_RU,
    AIRPORT_CODE_FROM_RU,
    AIRPORT_CODE_TO_RU,
    AIRPORT_CODE_ROUTE_RU,
    AIRPORT_DETAIL_SPEECH_RU,
    AIRPORT_NAME_DETAIL_SPEECH_RU,
) = load_airport_speech_data()


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

LATIN_LETTER_RE = re.compile(r"[A-Za-z\u00c0-\u024f]")
LATIN_TOKEN_RE = re.compile(r"[A-Za-z\u00c0-\u024f][A-Za-z0-9.+/\-\u00c0-\u024f]*")

LATIN_LETTER_SPEECH_RU = {
    "A": "эй",
    "B": "би",
    "C": "си",
    "D": "ди",
    "E": "и",
    "F": "эф",
    "G": "джи",
    "H": "эйч",
    "I": "ай",
    "J": "джей",
    "K": "кей",
    "L": "эл",
    "M": "эм",
    "N": "эн",
    "O": "оу",
    "P": "пи",
    "Q": "кью",
    "R": "ар",
    "S": "эс",
    "T": "ти",
    "U": "ю",
    "V": "ви",
    "W": "дабл-ю",
    "X": "икс",
    "Y": "уай",
    "Z": "зет",
}

LATIN_TOKEN_SPEECH_RU = {
    "MAX": "Макс",
    "NEO": "нео",
    "XP": "икс пи",
}

LATIN_WORD_TRANSLITERATION_RU = {
    "air": "эйр",
    "airbus": "Аэробус",
    "airlines": "авиалинии",
    "aviation": "авиэйшн",
    "bombardier": "Бомбардье",
    "challenger": "Челленджер",
    "example": "экзампл",
    "gulf": "Галф",
    "gulfstream": "Гольфстрим",
    "havacilik": "хаваджылык",
    "holdings": "холдингс",
    "hyperion": "Хайперион",
    "jet": "джет",
    "lufthansa": "Люфтганза",
    "new": "нью",
    "polish": "польские",
    "ural": "Уральские",
}

LATIN_TRANSLITERATION_DIGRAPHS_RU = (
    ("sch", "щ"),
    ("sh", "ш"),
    ("ch", "ч"),
    ("zh", "ж"),
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    ("ye", "е"),
    ("kh", "х"),
    ("ts", "ц"),
    ("th", "т"),
    ("ph", "ф"),
    ("ck", "к"),
)

LATIN_TRANSLITERATION_CHARS_RU = {
    "a": "а",
    "b": "б",
    "c": "к",
    "d": "д",
    "e": "е",
    "f": "ф",
    "g": "г",
    "h": "х",
    "i": "и",
    "j": "дж",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "q": "к",
    "r": "р",
    "s": "с",
    "t": "т",
    "u": "у",
    "v": "в",
    "w": "в",
    "x": "кс",
    "y": "и",
    "z": "з",
}

LATIN_SPECIAL_BASE_CHARS = str.maketrans(
    {
        "Æ": "Ae",
        "æ": "ae",
        "Ð": "D",
        "ð": "d",
        "Đ": "D",
        "đ": "d",
        "Ł": "L",
        "ł": "l",
        "Ø": "O",
        "ø": "o",
        "Œ": "Oe",
        "œ": "oe",
        "Þ": "Th",
        "þ": "th",
        "ß": "ss",
        "İ": "I",
        "ı": "i",
    }
)

def load_airline_speech_data(
    filename: str = SPEECH_RU_AIRLINES_DATA_FILE,
) -> tuple[dict[str, str], dict[str, str]]:
    """Load built-in Russian airline speech tables from packaged data."""
    raw_data = _load_speech_data_file(filename)
    if not isinstance(raw_data, dict):
        return {}, {}
    return (
        _speech_string_map(raw_data.get("airline")),
        _speech_string_map(raw_data.get("airline_aliases"), fold_keys=True),
    )


def load_callsign_prefix_speech_data(
    filename: str = SPEECH_RU_AIRLINES_DATA_FILE,
) -> dict[str, str]:
    """Load built-in Russian callsign prefix speech from packaged data."""
    raw_data = _load_speech_data_file(filename)
    if not isinstance(raw_data, dict):
        return {}
    return _speech_string_map(raw_data.get("callsign_prefix"))


def load_model_speech_rules_data(
    filename: str = SPEECH_RU_MODELS_DATA_FILE,
) -> tuple[tuple[tuple[str, ...], str], ...]:
    """Load built-in Russian aircraft model speech rules from packaged data."""
    raw_data = _load_speech_data_file(filename)
    if not isinstance(raw_data, list):
        return ()
    rules: list[tuple[tuple[str, ...], str]] = []
    for raw_rule in raw_data:
        if not isinstance(raw_rule, dict):
            continue
        raw_tokens = raw_rule.get("tokens")
        speech = str(raw_rule.get("speech", "")).strip()
        if not isinstance(raw_tokens, list) or not speech:
            continue
        tokens = tuple(str(token).strip() for token in raw_tokens if str(token).strip())
        if not tokens:
            continue
        rules.append((tokens, speech))
    return tuple(rules)


def load_military_speech_data(
    filename: str = SPEECH_RU_MILITARY_DATA_FILE,
) -> tuple[dict[str, str], dict[str, str]]:
    """Load built-in Russian military operator and owner speech tables."""
    raw_data = _load_speech_data_file(filename)
    if not isinstance(raw_data, dict):
        return {}, {}
    return (
        _speech_string_map(raw_data.get("operator")),
        _speech_string_map(raw_data.get("owner"), fold_keys=True),
    )


AIRLINE_SPEECH_RU, AIRLINE_SPEECH_ALIASES_RU = load_airline_speech_data()

CALLSIGN_PREFIX_SPEECH_RU = load_callsign_prefix_speech_data()
MILITARY_OPERATOR_SPEECH_RU, MILITARY_OWNER_SPEECH_RU = load_military_speech_data()

YEAR_RU = {
    1990: "тысяча девятьсот девяностого года",
    1997: "тысяча девятьсот девяносто седьмого года",
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


MODEL_SPEECH_RULES_RU = load_model_speech_rules_data()


@dataclass(frozen=True, slots=True)
class RussianSpeechPack:
    """Russian speech lookup tables used by announcement rendering."""

    city_from: dict[str, str]
    city_to: dict[str, str]
    city_route: dict[str, str]
    airport_code_from: dict[str, str]
    airport_code_to: dict[str, str]
    airport_code_route: dict[str, str]
    airport_detail: dict[str, str]
    airport_name_detail: dict[str, str]
    airline: dict[str, str]
    airline_aliases: dict[str, str]
    callsign_prefix: dict[str, str]
    military_operator: dict[str, str]
    military_owner: dict[str, str]
    model_rules: tuple[tuple[tuple[str, ...], str], ...]
    year: dict[int, str]

    def with_overrides(
        self,
        *,
        city_from: dict[str, str] | None = None,
        city_to: dict[str, str] | None = None,
        city_route: dict[str, str] | None = None,
        airline: dict[str, str] | None = None,
        airline_aliases: dict[str, str] | None = None,
        airport_code_from: dict[str, str] | None = None,
        airport_code_to: dict[str, str] | None = None,
        airport_code_route: dict[str, str] | None = None,
        callsign_prefix: dict[str, str] | None = None,
    ) -> RussianSpeechPack:
        """Return a pack with user-maintained override tables merged in."""
        return RussianSpeechPack(
            city_from={**self.city_from, **(city_from or {})},
            city_to={**self.city_to, **(city_to or {})},
            city_route={**self.city_route, **(city_route or {})},
            airport_code_from={**self.airport_code_from, **(airport_code_from or {})},
            airport_code_to={**self.airport_code_to, **(airport_code_to or {})},
            airport_code_route={**self.airport_code_route, **(airport_code_route or {})},
            airport_detail=self.airport_detail,
            airport_name_detail=self.airport_name_detail,
            airline={**self.airline, **(airline or {})},
            airline_aliases={**self.airline_aliases, **(airline_aliases or {})},
            callsign_prefix={**self.callsign_prefix, **(callsign_prefix or {})},
            military_operator=self.military_operator,
            military_owner=self.military_owner,
            model_rules=self.model_rules,
            year=self.year,
        )


DEFAULT_RUSSIAN_SPEECH_PACK = RussianSpeechPack(
    city_from=CITY_FROM_RU,
    city_to=CITY_TO_RU,
    city_route=CITY_ROUTE_RU,
    airport_code_from=AIRPORT_CODE_FROM_RU,
    airport_code_to=AIRPORT_CODE_TO_RU,
    airport_code_route=AIRPORT_CODE_ROUTE_RU,
    airport_detail=AIRPORT_DETAIL_SPEECH_RU,
    airport_name_detail=AIRPORT_NAME_DETAIL_SPEECH_RU,
    airline=AIRLINE_SPEECH_RU,
    airline_aliases=AIRLINE_SPEECH_ALIASES_RU,
    callsign_prefix=CALLSIGN_PREFIX_SPEECH_RU,
    military_operator=MILITARY_OPERATOR_SPEECH_RU,
    military_owner=MILITARY_OWNER_SPEECH_RU,
    model_rules=MODEL_SPEECH_RULES_RU,
    year=YEAR_RU,
)
