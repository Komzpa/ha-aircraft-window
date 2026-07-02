"""Built-in Russian speech tables for Aircraft Window."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SPEECH_RU_AIRPORTS_DATA_FILE = "data/speech_ru_airports.json"
SPEECH_RU_AIRLINES_DATA_FILE = "data/speech_ru_airlines.json"


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

AIRPORT_CODE_FROM_RU = {
    "ASB": "Ашхабада",
    "ATH": "Афин",
    "BJV": "Бодрума",
    "BEY": "Бейрута",
    "BRQ": "Брно",
    "CAN": "Гуанчжоу",
    "CDG": "Парижа, Шарль-де-Голль",
    "CGK": "Джакарты",
    "CIT": "Шымкента",
    "CPH": "Копенгагена",
    "EIN": "Эйндховена",
    "ESB": "Анкары",
    "FCO": "Рима",
    "GNY": "Шанлыурфы",
    "HKG": "Гонконга",
    "ICN": "Сеула",
    "IST": "Стамбула",
    "ISB": "Исламабада",
    "KIV": "Кишинёва",
    "KEJ": "Кемерова",
    "KTW": "Катовиц",
    "KWI": "Кувейта",
    "KRR": "Краснодара",
    "LHE": "Лахора",
    "LHR": "Лондона, Хитроу",
    "MAN": "Манчестера",
    "MRV": "Минеральных Вод",
    "MUC": "Мюнхена",
    "OGU": "Орду",
    "OSL": "Осло",
    "PKX": "Пекина, Дасин",
    "PVG": "Шанхая, Пудун",
    "SAW": "Стамбула, Сабиха Гёкчен",
    "SCO": "Актау",
    "SGN": "Хошимина",
    "SKX": "Саранска",
    "SVX": "Екатеринбурга",
    "STR": "Штутгарта",
    "TIV": "Тивата",
    "TIA": "Тираны",
    "TLV": "Бен Гуриона",
    "UFA": "Уфы",
    "ULN": "Улан-Батора",
    "VIE": "Вены",
    "VOG": "Волгограда",
    "WAW": "Варшавы",
    "WRO": "Вроцлава",
    "ZRH": "Цюриха",
    "ZIA": "подмосковного Жуковского",
}

AIRPORT_CODE_TO_RU = {
    "ASB": "Ашхабад",
    "ATH": "Афины",
    "BJV": "Бодрум",
    "BEY": "Бейрут",
    "BRQ": "Брно",
    "CAN": "Гуанчжоу",
    "CDG": "Париж, Шарль-де-Голль",
    "CGK": "Джакарту",
    "CIT": "Шымкент",
    "CPH": "Копенгаген",
    "EIN": "Эйндховен",
    "ESB": "Анкару",
    "FCO": "Рим",
    "GNY": "Шанлыурфу",
    "HKG": "Гонконг",
    "ICN": "Сеул",
    "IST": "Стамбул",
    "ISB": "Исламабад",
    "KIV": "Кишинёв",
    "KEJ": "Кемерово",
    "KTW": "Катовице",
    "KWI": "Кувейт",
    "KRR": "Краснодар",
    "LHE": "Лахор",
    "LHR": "Лондон, Хитроу",
    "MAN": "Манчестер",
    "MRV": "Минеральные Воды",
    "MUC": "Мюнхен",
    "OGU": "Орду",
    "OSL": "Осло",
    "PKX": "Пекин, Дасин",
    "PVG": "Шанхай, Пудун",
    "SAW": "Стамбул, Сабиха Гёкчен",
    "SCO": "Актау",
    "SGN": "Хошимин",
    "SKX": "Саранск",
    "SVX": "Екатеринбург",
    "STR": "Штутгарт",
    "TIV": "Тиват",
    "TIA": "Тирану",
    "TLV": "Бен Гурион",
    "UFA": "Уфу",
    "ULN": "Улан-Батор",
    "VIE": "Вену",
    "VOG": "Волгоград",
    "WAW": "Варшаву",
    "WRO": "Вроцлав",
    "ZRH": "Цюрих",
    "ZIA": "подмосковный Жуковский",
}

AIRPORT_CODE_ROUTE_RU = {
    "AES": "Алесунд",
    "ASB": "Ашхабад",
    "ARN": "Стокгольм",
    "ATH": "Афины",
    "BJV": "Бодрум",
    "BOM": "Мумбаи",
    "BEY": "Бейрут",
    "BRQ": "Брно",
    "BUS": "Батуми",
    "CAN": "Гуанчжоу",
    "CDG": "Париж, Шарль-де-Голль",
    "CGK": "Джакарта",
    "CIT": "Шымкент",
    "CPH": "Копенгаген",
    "DME": "Москва, Домодедово",
    "EIN": "Эйндховен",
    "ESB": "Анкара",
    "EVN": "Ереван, Звартноц",
    "FCO": "Рим",
    "GNY": "Шанлыурфа",
    "HAM": "Гамбург",
    "HKG": "Гонконг",
    "ICN": "Сеул",
    "IST": "Стамбул",
    "ISB": "Исламабад",
    "KEJ": "Кемерово",
    "KIV": "Кишинёв",
    "KRK": "Краков",
    "KRR": "Краснодар",
    "KTW": "Катовице",
    "KUT": "Кутаиси",
    "KWI": "Кувейт",
    "LCA": "Ларнака",
    "LHE": "Лахор",
    "LHR": "Лондон, Хитроу",
    "MAD": "Мадрид",
    "MAN": "Манчестер",
    "MRV": "Минеральные Воды",
    "MUC": "Мюнхен",
    "MXP": "Милан",
    "OGU": "Орду",
    "OSL": "Осло",
    "OVB": "Новосибирск",
    "PKX": "Пекин, Дасин",
    "PVG": "Шанхай, Пудун",
    "RIX": "Рига",
    "SAW": "Стамбул, Сабиха Гёкчен",
    "SCO": "Актау",
    "SGN": "Хошимин",
    "SKG": "Салоники",
    "SKP": "Скопье",
    "SKX": "Саранск",
    "SVO": "Москва, Шереметьево",
    "SVX": "Екатеринбург",
    "STR": "Штутгарт",
    "TIV": "Тиват",
    "TIA": "Тирана",
    "TLV": "Бен Гурион",
    "UFA": "Уфа",
    "ULN": "Улан-Батор",
    "VIE": "Вена",
    "VKO": "Москва, Внуково",
    "VOG": "Волгоград",
    "WAW": "Варшава",
    "WRO": "Вроцлав",
    "ZRH": "Цюрих",
    "ZIA": "подмосковный Жуковский",
}

AIRPORT_DETAIL_SPEECH_RU = {
    "DME": "Домодедово",
    "EVN": "Звартноц",
    "SVO": "Шереметьево",
    "VKO": "Внуково",
}

AIRPORT_NAME_DETAIL_SPEECH_RU = {
    "Domodedovo International Airport": "Домодедово",
    "Moscow Domodedovo Airport": "Домодедово",
    "Moscow Sheremetyevo Airport": "Шереметьево",
    "Moscow Vnukovo Airport": "Внуково",
    "Sheremetyevo International Airport": "Шереметьево",
    "Vnukovo International Airport": "Внуково",
    "Zvartnots International Airport": "Звартноц",
}

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


AIRLINE_SPEECH_RU, AIRLINE_SPEECH_ALIASES_RU = load_airline_speech_data()

MILITARY_OPERATOR_SPEECH_RU = {
    "PLF": "Польские ВВС",
    "RCH": "военный транспорт США",
    "RRR": "Королевские ВВС",
    "ASY": "австралийские ВВС",
    "IAM": "итальянские ВВС",
    "GAF": "немецкие ВВС",
    "FAF": "французские ВВС",
    "CTM": "французские ВВС",
    "AME": "испанские ВВС",
    "THK": "турецкие ВВС",
}

MILITARY_OWNER_SPEECH_RU = {
    "french air force": "французские ВВС",
    "united states air force": "ВВС США",
    "us air force": "ВВС США",
    "u.s. air force": "ВВС США",
    "turkish air force": "ВВС Турции",
    "romanian air force": "ВВС Румынии",
    "united states army": "Армия США",
    "us army": "Армия США",
    "united states navy": "ВМС США",
    "us navy": "ВМС США",
}

CALLSIGN_PREFIX_SPEECH_RU = load_callsign_prefix_speech_data()

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


MODEL_SPEECH_RULES_RU: tuple[tuple[tuple[str, ...], str], ...] = (
    (("C-130", "C130", "C30J", "HERCULES"), "Си-сто тридцать Геркулес"),
    (("C-12", "C12", "HURON"), "Си-двенадцать Хьюрон"),
    (("C-146", "C146"), "Си-сто сорок шесть"),
    (("A400",), "Аэробус А-четыреста"),
    (("TU-204", "T204"), "Ту-двести четыре"),
    (("TU-214", "T214"), "Ту-двести четырнадцать"),
    (("A220", "BCS3", "BCS1"), "Аэробус А-двести двадцать"),
    (("A19N", "A319"), "Аэробус триста девятнадцать"),
    (("A20N", "A320"), "Аэробус триста двадцать"),
    (("A21N", "A321"), "Аэробус триста двадцать один"),
    (("A332", "A330"), "Аэробус триста тридцать"),
    (("A35K", "A350"), "Аэробус триста пятьдесят"),
    (
        ("B38M", "737 MAX 8", "re:\\b737-8(?!00)\\b"),
        "Боинг семьсот тридцать семь Макс восемь",
    ),
    (
        ("B39M", "737 MAX 9", "re:\\b737-9(?!00)\\b"),
        "Боинг семьсот тридцать семь Макс девять",
    ),
    (("B737", "B738", "B739", "737"), "Боинг семьсот тридцать семь"),
    (("B752", "757"), "Боинг семьсот пятьдесят семь"),
    (("B763", "767"), "Боинг семьсот шестьдесят семь"),
    (("B77", "777"), "Боинг семьсот семьдесят семь"),
    (("B78", "787"), "Боинг семьсот восемьдесят семь"),
    (("IL76", "IL-76"), "Ил-семьдесят шесть"),
    (("E190",), "Эмбраер сто девяносто"),
    (("E195",), "Эмбраер сто девяносто пять"),
    (("E170", "E75"), "Эмбраер сто семьдесят"),
    (("CRJ",), "Си-ар-джей"),
    (("PA-46", "M500"), "Пайпер M500"),
    (("ASTRA", "1125"), "Астра эс-пи-икс"),
    (("FALCON 2000",), "Дассо Фалькон две тысячи"),
    (("CHALLENGER 300", "CL30"), "Бомбардье Челленджер трёхсотый"),
    (("CHALLENGER 350", "CL35"), "Бомбардье Челленджер триста пятидесятый"),
    (("CHALLENGER 604",), "Бомбардье Челленджер шестьсот четвёртый"),
    (("CHALLENGER 605",), "Бомбардье Челленджер шестьсот пятый"),
    (("CHALLENGER 650",), "Бомбардье Челленджер шестьсот пятидесятый"),
    (("CHALLENGER", "CL60", "CL65"), "Бомбардье Челленджер"),
    (("GL6T", "GLOBAL 6000"), "Бомбардье Глобал шесть тысяч"),
    (("GL5T", "GLOBAL 5000"), "Бомбардье Глобал пять тысяч"),
    (("G650", "GLF6"), "Гольфстрим Джи-шестьсот пятьдесят"),
    (("G550", "GLF5"), "Гольфстрим Джи-пятьсот пятьдесят"),
    (("GLF4",), "Гольфстрим четыре"),
    (("GULFSTREAM", "GLF"), "Гольфстрим"),
    (("H25B", "850XP"), "Хокер восемьсот пятьдесят икс пи"),
    (("SU95", "SSJ"), "Суперджет"),
    (("C208", "CARAVAN"), "Цессна Караван"),
    (("EUROFOX", "AEROPRO"), "Еврофокс"),
    (
        ("L410", "LET"),
        "Лет четыреста десять Турболет, небольшой двухмоторный турбовинтовой",
    ),
)


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
    model_rules=MODEL_SPEECH_RULES_RU,
    year=YEAR_RU,
)
