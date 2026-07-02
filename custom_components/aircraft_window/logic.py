"""Aircraft detection and enrichment logic for Aircraft Window."""

from __future__ import annotations

import math
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any

CITY_FROM_RU = {
    "Almaty": "Алматы",
    "Amman": "Аммана",
    "Amsterdam": "Амстердама",
    "Ankara": "Анкары",
    "Antalya": "Антальи",
    "Arnavutköy, Istanbul": "Стамбула",
    "Athens": "Афин",
    "Astana": "Астаны",
    "Atyrau": "Атырау",
    "Ashgabat": "Ашхабада",
    "Baku": "Баку",
    "Bangkok": "Бангкока",
    "Barcelona": "Барселоны",
    "Batumi": "Батуми",
    "Berlin": "Берлина",
    "Beijing": "Пекина",
    "Beirut": "Бейрута",
    "Bodrum": "Бодрума",
    "Brno": "Брно",
    "Chelyabinsk": "Челябинска",
    "Chişinău": "Кишинёва",
    "Chișinău": "Кишинёва",
    "Chisinau": "Кишинёва",
    "Copenhagen": "Копенгагена",
    "Dubai": "Дубая",
    "Ekaterinburg": "Екатеринбурга",
    "Eindhoven": "Эйндховена",
    "Erbil": "Эрбиля",
    "Frankfurt Am Main": "Франкфурта-на-Майне",
    "Guangzhou": "Гуанчжоу",
    "Hamburg": "Гамбурга",
    "Hanoi": "Ханоя",
    "Hong Kong": "Гонконга",
    "Ho Chi Minh City": "Хошимина",
    "Hurghada": "Хургады",
    "Islamabad": "Исламабада",
    "Istanbul": "Стамбула",
    "Jakarta": "Джакарты",
    "Jeddah": "Джидды",
    "Katowice": "Катовиц",
    "Kazan": "Казани",
    "Konya": "Коньи",
    "Kopitnari": "Кутаиси",
    "Krasnodar International Airport": "Краснодара",
    "Krakow": "Кракова",
    "Kuwait": "Кувейта",
    "Lahore": "Лахора",
    "Larnaca": "Ларнаки",
    "London": "Лондона",
    "Madrid": "Мадрида",
    "Milan": "Милана",
    "Mineralnyye Vody": "Минеральных Вод",
    "Minsk": "Минска",
    "Moscow": "Москвы",
    "Moscow Zhukovsky": "подмосковного Жуковского",
    "Mumbai": "Мумбаи",
    "Manchester": "Манчестера",
    "Munich": "Мюнхена",
    "Natakhtari": "Натахтари",
    "New Delhi": "Нью-Дели",
    "Novosibirsk": "Новосибирска",
    "Nur Sultan": "Нур-Султана",
    "Ordu": "Орду",
    "Oslo": "Осло",
    "Paris": "Парижа",
    "Pendik, Istanbul": "Стамбула, Сабиха Гёкчен",
    "Perm": "Перми",
    "Riga": "Риги",
    "Riyadh": "Эр-Рияда",
    "Rome": "Рима",
    "Saint Petersburg": "Санкт-Петербурга",
    "Samara": "Самары",
    "Saransk": "Саранска",
    "Seoul": "Сеула",
    "Sharm El Sheikh": "Шарм-эш-Шейха",
    "Shiraz": "Шираза",
    "Skopje": "Скопье",
    "Shanghai": "Шанхая",
    "Shanghai (Pudong)": "Шанхая, Пудун",
    "Sochi": "Сочи",
    "Sok Son, Hanoi": "Ханоя",
    "St. Petersburg": "Санкт-Петербурга",
    "Stockholm": "Стокгольма",
    "Shymkent": "Шымкента",
    "Stuttgart": "Штутгарта",
    "Şanlıurfa": "Шанлыурфы",
    "Tashkent": "Ташкента",
    "Tbilisi": "Тбилиси",
    "Tehran": "Тегерана",
    "Tel Aviv": "Тель-Авива",
    "Thessaloniki": "Салоник",
    "Tirana": "Тираны",
    "Tivat": "Тивата",
    "Ufa": "Уфы",
    "Ulaanbaatar": "Улан-Батора",
    "Vienna": "Вены",
    "Volgograd": "Волгограда",
    "Warsaw": "Варшавы",
    "Wrocław": "Вроцлава",
    "Wroclaw": "Вроцлава",
    "Yekaterinburg": "Екатеринбурга",
    "Yerevan": "Еревана",
    "Zurich": "Цюриха",
    "Zhukovsky": "подмосковного Жуковского",
}

CITY_TO_RU = {
    "Almaty": "Алматы",
    "Amman": "Амман",
    "Amsterdam": "Амстердам",
    "Ankara": "Анкару",
    "Antalya": "Анталью",
    "Arnavutköy, Istanbul": "Стамбул",
    "Athens": "Афины",
    "Astana": "Астану",
    "Atyrau": "Атырау",
    "Ashgabat": "Ашхабад",
    "Baku": "Баку",
    "Bangkok": "Бангкок",
    "Barcelona": "Барселону",
    "Batumi": "Батуми",
    "Berlin": "Берлин",
    "Beijing": "Пекин",
    "Beirut": "Бейрут",
    "Bodrum": "Бодрум",
    "Brno": "Брно",
    "Chelyabinsk": "Челябинск",
    "Chişinău": "Кишинёв",
    "Chișinău": "Кишинёв",
    "Chisinau": "Кишинёв",
    "Copenhagen": "Копенгаген",
    "Dubai": "Дубай",
    "Ekaterinburg": "Екатеринбург",
    "Eindhoven": "Эйндховен",
    "Erbil": "Эрбиль",
    "Frankfurt Am Main": "Франкфурт-на-Майне",
    "Guangzhou": "Гуанчжоу",
    "Hamburg": "Гамбург",
    "Hanoi": "Ханой",
    "Hong Kong": "Гонконг",
    "Ho Chi Minh City": "Хошимин",
    "Hurghada": "Хургаду",
    "Islamabad": "Исламабад",
    "Istanbul": "Стамбул",
    "Jakarta": "Джакарту",
    "Jeddah": "Джидду",
    "Katowice": "Катовице",
    "Kazan": "Казань",
    "Konya": "Конью",
    "Kopitnari": "Кутаиси",
    "Krasnodar International Airport": "Краснодар",
    "Krakow": "Краков",
    "Kuwait": "Кувейт",
    "Lahore": "Лахор",
    "Larnaca": "Ларнаку",
    "London": "Лондон",
    "Madrid": "Мадрид",
    "Milan": "Милан",
    "Mineralnyye Vody": "Минеральные Воды",
    "Minsk": "Минск",
    "Moscow": "Москву",
    "Moscow Zhukovsky": "подмосковный Жуковский",
    "Mumbai": "Мумбаи",
    "Manchester": "Манчестер",
    "Munich": "Мюнхен",
    "Natakhtari": "Натахтари",
    "New Delhi": "Нью-Дели",
    "Novosibirsk": "Новосибирск",
    "Nur Sultan": "Нур-Султан",
    "Ordu": "Орду",
    "Oslo": "Осло",
    "Paris": "Париж",
    "Pendik, Istanbul": "Стамбул, Сабиха Гёкчен",
    "Perm": "Пермь",
    "Riga": "Ригу",
    "Riyadh": "Эр-Рияд",
    "Rome": "Рим",
    "Saint Petersburg": "Санкт-Петербург",
    "Samara": "Самару",
    "Saransk": "Саранск",
    "Seoul": "Сеул",
    "Sharm El Sheikh": "Шарм-эш-Шейх",
    "Shiraz": "Шираз",
    "Skopje": "Скопье",
    "Shanghai": "Шанхай",
    "Shanghai (Pudong)": "Шанхай, Пудун",
    "Sochi": "Сочи",
    "Sok Son, Hanoi": "Ханой",
    "St. Petersburg": "Санкт-Петербург",
    "Stockholm": "Стокгольм",
    "Shymkent": "Шымкент",
    "Stuttgart": "Штутгарт",
    "Şanlıurfa": "Шанлыурфу",
    "Tashkent": "Ташкент",
    "Tbilisi": "Тбилиси",
    "Tehran": "Тегеран",
    "Tel Aviv": "Тель-Авив",
    "Thessaloniki": "Салоники",
    "Tirana": "Тирану",
    "Tivat": "Тиват",
    "Ufa": "Уфу",
    "Ulaanbaatar": "Улан-Батор",
    "Vienna": "Вену",
    "Volgograd": "Волгоград",
    "Warsaw": "Варшаву",
    "Wrocław": "Вроцлав",
    "Wroclaw": "Вроцлав",
    "Yekaterinburg": "Екатеринбург",
    "Yerevan": "Ереван",
    "Zurich": "Цюрих",
    "Zhukovsky": "подмосковный Жуковский",
}

CITY_ROUTE_RU = {
    "Almaty": "Алматы",
    "Amman": "Амман",
    "Amsterdam": "Амстердам",
    "Ankara": "Анкара",
    "Antalya": "Анталья",
    "Arnavutköy, Istanbul": "Стамбул",
    "Athens": "Афины",
    "Astana": "Астана",
    "Atyrau": "Атырау",
    "Ashgabat": "Ашхабад",
    "Baku": "Баку",
    "Bangkok": "Бангкок",
    "Barcelona": "Барселона",
    "Batumi": "Батуми",
    "Berlin": "Берлин",
    "Beijing": "Пекин",
    "Beirut": "Бейрут",
    "Bodrum": "Бодрум",
    "Brno": "Брно",
    "Chelyabinsk": "Челябинск",
    "Chişinău": "Кишинёв",
    "Chișinău": "Кишинёв",
    "Chisinau": "Кишинёв",
    "Copenhagen": "Копенгаген",
    "Dubai": "Дубай",
    "Ekaterinburg": "Екатеринбург",
    "Eindhoven": "Эйндховен",
    "Erbil": "Эрбиль",
    "Frankfurt Am Main": "Франкфурт-на-Майне",
    "Guangzhou": "Гуанчжоу",
    "Hamburg": "Гамбург",
    "Hanoi": "Ханой",
    "Hong Kong": "Гонконг",
    "Ho Chi Minh City": "Хошимин",
    "Hurghada": "Хургада",
    "Islamabad": "Исламабад",
    "Istanbul": "Стамбул",
    "Jakarta": "Джакарта",
    "Jeddah": "Джидда",
    "Katowice": "Катовице",
    "Kazan": "Казань",
    "Konya": "Конья",
    "Kopitnari": "Кутаиси",
    "Krasnodar International Airport": "Краснодар",
    "Krakow": "Краков",
    "Kuwait": "Кувейт",
    "Lahore": "Лахор",
    "Larnaca": "Ларнака",
    "London": "Лондон",
    "Madrid": "Мадрид",
    "Milan": "Милан",
    "Mineralnyye Vody": "Минеральные Воды",
    "Minsk": "Минск",
    "Moscow": "Москва",
    "Moscow Zhukovsky": "подмосковный Жуковский",
    "Mumbai": "Мумбаи",
    "Manchester": "Манчестер",
    "Munich": "Мюнхен",
    "Natakhtari": "Натахтари",
    "New Delhi": "Нью-Дели",
    "Novosibirsk": "Новосибирск",
    "Nur Sultan": "Нур-Султан",
    "Ordu": "Орду",
    "Oslo": "Осло",
    "Paris": "Париж",
    "Pendik, Istanbul": "Стамбул, Сабиха Гёкчен",
    "Perm": "Пермь",
    "Riga": "Рига",
    "Riyadh": "Эр-Рияд",
    "Rome": "Рим",
    "Saint Petersburg": "Санкт-Петербург",
    "Samara": "Самара",
    "Saransk": "Саранск",
    "Seoul": "Сеул",
    "Sharm El Sheikh": "Шарм-эш-Шейх",
    "Shiraz": "Шираз",
    "Skopje": "Скопье",
    "Shanghai": "Шанхай",
    "Shanghai (Pudong)": "Шанхай, Пудун",
    "Sochi": "Сочи",
    "Sok Son, Hanoi": "Ханой",
    "St. Petersburg": "Санкт-Петербург",
    "Stockholm": "Стокгольм",
    "Shymkent": "Шымкент",
    "Stuttgart": "Штутгарт",
    "Şanlıurfa": "Шанлыурфа",
    "Tashkent": "Ташкент",
    "Tbilisi": "Тбилиси",
    "Tehran": "Тегеран",
    "Tel Aviv": "Тель-Авив",
    "Thessaloniki": "Салоники",
    "Tirana": "Тирана",
    "Tivat": "Тиват",
    "Ufa": "Уфа",
    "Ulaanbaatar": "Улан-Батор",
    "Vienna": "Вена",
    "Volgograd": "Волгоград",
    "Warsaw": "Варшава",
    "Wrocław": "Вроцлав",
    "Wroclaw": "Вроцлав",
    "Yekaterinburg": "Екатеринбург",
    "Yerevan": "Ереван",
    "Zurich": "Цюрих",
    "Zhukovsky": "подмосковный Жуковский",
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

AIRLINE_SPEECH_RU = {
    "Air Astana": "Эйр Астана",
    "Air Baltic": "Эйр Балтик",
    "Air Cairo": "Эйр Каиро",
    "Aeroflot": "Аэрофлот",
    "Aeroflot Russian Airlines": "Аэрофлот",
    "AnadoluJet": "АнадолуДжет",
    "Arkia Israel Airlines": "Аркия",
    "Arkia Israeli Airlines": "Аркия",
    "ARKIA ISRAEL AIRLINES": "Аркия",
    "Armenian Airlines": "Армениан Эйрлайнс",
    "Asiana Airlines": "Азиана",
    "Atlantis European Airways": "Атлантис Европиан Эйрвейз",
    "Austrian Airlines": "Австрийские авиалинии",
    "Azov Avia Airlines": "Азов Авиа",
    "Azerbaijan Airlines": "Азербайджанские авиалинии",
    "Azerbaijan Airlines (Buta Airways)": "Азербайджанские авиалинии",
    "AZAL": "Азал",
    "Azimuth": "Азимут",
    "Azimuth Airlines": "Азимут",
    "Air Samarkand": "Эйр Самарканд",
    "Belavia": "Белавиа",
    "Belavia Belarusian Airlines": "Белавиа",
    "Carpatair": "Карпатэйр",
    "Centrum Air": "Центрум Эйр",
    "Cathay Pacific": "Катай Пасифик",
    "China Southern Airlines": "Чайна Саузерн",
    "EL AL": "Эль Аль",
    "EL-AL ISRAEL AIRLINES": "Эль Аль",
    "El Al Israel Airlines": "Эль Аль",
    "El-Al Israel Airlines": "Эль Аль",
    "El Al": "Эль Аль",
    "FlyArystan": "Флай Арыстан",
    "Fly One": "Флай Уан",
    "Fly One Armenia": "Флай Уан Армения",
    "flydubai": "Флай Дубай",
    "Flydubai": "Флай Дубай",
    "Fly Lili": "Флай Лили",
    "Flynas": "Флай Нас",
    "FlyOne Armenia": "Флай Уан Армения",
    "Emirates": "Эмирейтс",
    "Genel Havacilik": "Генел Хаваджылык",
    "Georgian Airways": "Джорджиан Эйрвейз",
    "Georgian Wings": "Джорджиан Вингс",
    "Iran Aseman Airlines": "Иран Асеман",
    "Iraq Airways": "Иракские авиалинии",
    "Iraqi Airways": "Иракские авиалинии",
    "Israir": "Исра Эйр",
    "Israir Airlines": "Исра Эйр",
    "Jazeera Airways": "Джазира",
    "Jordan Aviation": "Джордан Авиейшен",
    "Jordanian Aviation": "Джорданиан Авиейшен",
    "Kish Air": "Киш Эйр",
    "KLM Royal Dutch Airlines": "Кей-Эл-Эм",
    "Korean Air": "Кореан Эйр",
    "Nas Air": "Флай Нас",
    "Oneclick": "УанКлик",
    "OneClick Airways": "УанКлик",
    "Pars Air": "Парс Эйр",
    "Pegasus Airlines": "Пегасус",
    "Qeshm Air": "Кешм Эйр",
    "Red Wings": "Ред Вингс",
    "Red Wings Airlines": "Ред Вингс",
    "Rossiya - Russian Airlines": "Россия",
    "S7 Airlines": "Эс-семь",
    "S7 Airlines (Siberia Airlines)": "Эс-семь",
    "SCAT Air Company": "Скат",
    "SCAT Airlines": "Скат",
    "Scat": "Скат",
    "Scandinavian Airlines System": "Скандинавские авиалинии",
    "Silk Way Airlines": "Силк Вей",
    "Silk Way West Airlines": "Силк Вей",
    "Southwind Air Corporation": "Саутвинд",
    "SunExpress": "Санэкспресс",
    "Swiss International Air Lines": "Свисс",
    "Tarkim Havacilik": "Тарким Хаваджылык",
    "Thai Airways International": "Тайские авиалинии",
    "Trade Air": "Трейд Эйр",
    "Turkish Airlines": "Туркиш",
    "Turkmenistan Airlines": "Туркменистанские авиалинии",
    "Uzbekistan Airways": "Узбекистон",
    "Varesh Airlines": "Вареш",
    "Van Air Europe": "Ван Эйр",
    "Vanilla Sky": "Ванилла Скай",
    "Virgin Atlantic Airways": "Вёрджин Атлантик",
    "Wizz Air": "Визз Эйр",
    "Bonair Havacilik": "Бонэйр Хаваджылык",
    "Gulf Wings": "Галф Вингс",
    "Hyperion Aviation": "Хайперион Авиэйшн",
    "Lufthansa": "Люфтганза",
    "New Example Air": "Нью Экзампл Эйр",
    "Polish Air Force": "Польские ВВС",
    "Redstar Aviation": "Редстар Авиэйшн",
    "South West Air Corporation": "Саутвест Эйр",
    "Speedwings Executive Jet GmbH": "Спидвингс Экзекьютив Джет",
    "Tyrol Air Ambulance": "Тироль Эйр Амбуланс",
    "Ural Airlines": "Уральские авиалинии",
}

AIRLINE_SPEECH_ALIASES_RU = {
    "aeroflot russian airlines": "Аэрофлот",
    "arkia israel  airlines": "Аркия",
    "georgian airways": "Джорджиан Эйрвейз",
    "klm royal dutch airlines": "Кей-Эл-Эм",
    "red wings airlines": "Ред Вингс",
    "rossiya - russian airlines": "Россия",
    "s7 airlines (siberia airlines)": "Эс-семь",
    "scat air company": "Скат",
    "speedwings executive jet gmbh": "Спидвингс Экзекьютив Джет",
}

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

PASSENGER_AIRLINES = {
    "Air Astana",
    "Air Baltic",
    "Air Samarkand",
    "Arkia Israel Airlines",
    "Arkia Israeli Airlines",
    "Azimuth Airlines",
    "Azerbaijan Airlines",
    "Azerbaijan Airlines (Buta Airways)",
    "AZAL",
    "Belavia",
    "Belavia Belarusian Airlines",
    "Centrum Air",
    "EL AL",
    "El-Al Israel Airlines",
    "El Al",
    "FlyArystan",
    "flydubai",
    "Flydubai",
    "Flynas",
    "FlyOne Armenia",
    "Israir",
    "Israir Airlines",
    "Jazeera Airways",
    "KLM Royal Dutch Airlines",
    "Nas Air",
    "Pegasus Airlines",
    "Red Wings",
    "Rossiya - Russian Airlines",
    "S7 Airlines",
    "S7 Airlines (Siberia Airlines)",
    "SCAT Airlines",
    "Scat",
    "Thai Airways International",
    "Turkish Airlines",
    "Uzbekistan Airways",
    "Varesh Airlines",
    "Wizz Air",
}

CARGO_OPERATOR_TOKENS = (
    "cargo",
    "cargolux",
    "dhl",
    "fedex",
    "freight",
    "silk way",
    "silk way airlines",
    "silk way west",
    "sky cargo",
    "skycargo",
    "turkish cargo",
    "ups",
)

CARGO_TYPE_TOKENS = (
    " freighter",
    "cargo",
    "bdsf",
    "bcf",
    "pcf",
    "-sf",
    " sf ",
)

BUSINESS_JET_TYPE_CODES = {
    "BE40",
    "C25A",
    "C25B",
    "C25C",
    "C510",
    "C525",
    "C550",
    "C560",
    "C56X",
    "C650",
    "C680",
    "C700",
    "CL30",
    "CL35",
    "CL60",
    "CL65",
    "E50P",
    "E545",
    "E55P",
    "F2TH",
    "F900",
    "FA10",
    "FA20",
    "FA50",
    "G150",
    "G200",
    "G280",
    "GL5T",
    "GL6T",
    "GL7T",
    "GLF2",
    "GLF3",
    "GLF4",
    "GLF5",
    "GLF6",
    "GLEX",
    "H25A",
    "H25B",
    "H25C",
    "LJ31",
    "LJ35",
    "LJ45",
    "LJ55",
    "LJ60",
    "PRM1",
}

BUSINESS_JET_MODEL_TOKENS = (
    "125 850XP",
    "800XP",
    "850XP",
    "CHALLENGER",
    "CITATION",
    "FALCON",
    "GLOBAL",
    "GULFSTREAM",
    "HAWKER",
    "LEARJET",
)

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

CALLSIGN_PREFIX_SPEECH_RU = {
    "SPAR": "Спар",
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

DEFAULT_WINDOW_VIEW_LEAD_SECONDS = 240.0
DEFAULT_WINDOW_VIEW_PROJECTION_STEP_SECONDS = 15.0
DEFAULT_WINDOW_VIEW_RADIUS_KM = 80.0
DEFAULT_DAY_HUMAN_VISIBLE_RADIUS_KM = 12.0
DEFAULT_LOW_LIGHT_HUMAN_VISIBLE_RADIUS_KM = 35.0
DEFAULT_NIGHT_HUMAN_VISIBLE_RADIUS_KM = 45.0
WINDOW_VIEW_AZIMUTH_DEGREES = 290.0
WINDOW_VIEW_HALF_ANGLE_DEGREES = 90.0
BATUMI_RUNWAY_STAGING_LAT = 41.6103
BATUMI_RUNWAY_STAGING_LON = 41.6004
DEFAULT_RUNWAY_STAGING_RADIUS_KM = 3.0
DEFAULT_RUNWAY_STAGING_MAX_ALTITUDE_FT = 500.0
DEFAULT_RUNWAY_STAGING_MAX_SPEED_KT = 45.0
FEET_TO_KILOMETERS = 0.0003048
WINDOW_VIEW_POLYGON_LON_LAT = (
    (41.5906258, 41.6211806),
    (41.5759385, 41.6106128),
    (40.5297019, 40.8787998),
    (37.6439069, 39.8782721),
    (30.1070473, 40.9740093),
    (30.5487884, 46.1944223),
    (41.4123703, 45.3912115),
    (42.0420538, 42.0792269),
)

INTERESTING_SQUAWKS = {
    "7500": ("возможное незаконное вмешательство", "special squawk 7500"),
    "7600": ("потеря радиосвязи", "special squawk 7600"),
    "7700": ("аварийная ситуация", "special squawk 7700"),
}

MEDEVAC_TOKENS = (
    "air ambulance",
    "ambulance",
    "hems",
    "lifeguard",
    "medevac",
    "medical",
    "rescue",
)

POLICE_TOKENS = (
    "gendarmerie",
    "police",
    "polizei",
    "sheriff",
    "state police",
)

CALIBRATION_TOKENS = (
    "calibration",
    "calibrator",
    "flight check",
    "flightcheck",
    "nav check",
    "navaid",
    "radar calibration",
)

DRONE_TOKENS = (
    "bayraktar",
    "drone",
    "orlan",
    "rpa",
    "shahid",
    "shahed",
    "tb2",
    "uas",
    "uav",
    "unmanned",
)

TRANSPORT_AIRCRAFT_MODEL_RE = re.compile(
    r"\b(?:"
    r"A(?:19N|20N|21N|220|319|320|321|330|332)|"
    r"B(?:38M|39M|737|738|739|752|763|77[0-9]?|78[0-9]?)|"
    r"E(?:170|190|195)|E75[0-9]?|CRJ[0-9]*|"
    r"SU95|SSJ|T204|T214|IL-?76|C208|L410"
    r")\b"
)

TANKER_TOKENS = (
    "a330 mrtt",
    "kc-10",
    "kc-135",
    "kc-46",
    "k35a",
    "k35r",
    "mrtt",
    "tanker",
)

HELICOPTER_TOKENS = (
    "helicopter",
    "rotorcraft",
    "robinson",
    "airbus helicopters",
    "bell helicopter",
    "eurocopter",
    "sikorsky",
)

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

KNOWN_BUILT_YEAR_BY_REGISTRATION: dict[str, int] = {
    "EP-VAI": 1997,
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
    squawk: str = ""
    announcement: str = ""
    announcement_suppressed: bool = False
    announcement_suppression_reason: str = ""
    announcement_kind: str = "initial"
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
    route_source: str = ""
    scheduled_departure_local: str = ""
    airport_board_remark: str = ""
    airport_board_estimated_local: str = ""
    aircraft_model: str = ""
    aircraft_type: str = ""
    aircraft_model_speech: str = ""
    registration: str = ""
    registered_owner: str = ""
    operator_flag_code: str = ""
    owner_country: str = ""
    adsb_category: str = ""
    built_year: int | None = None
    built_year_speech: str = ""
    enrichment_source: str = ""
    interest_reason: str = ""
    interest_type: str = ""
    interest_label: str = ""
    interest_detail: str = ""
    squawk_label: str = ""
    novelty_reason: str = ""
    unusual_aircraft: bool = False
    spoken_flight: str = ""
    service_type: str = "unknown"
    service_type_confidence: float = 0.0
    service_type_reason: str = ""
    window_visible: bool = False
    window_preopen_needed: bool = False
    window_view_reason: str = ""
    window_runway_staging: bool = False
    window_view_projected_lat: float | None = None
    window_view_projected_lon: float | None = None
    window_view_lead_seconds: float | None = None
    window_view_radius_km: float | None = None
    window_distance_km: float | None = None
    window_bearing_degrees: float | None = None
    window_direction: str = ""
    window_elevation_degrees: float | None = None
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


def parse_float_or(value: Any, default: float) -> float:
    """Parse a float while preserving valid zero values."""
    parsed = parse_float(value)
    return default if parsed is None else parsed


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


def squawk_code(aircraft: dict[str, Any]) -> str:
    """Return the four-digit transponder code when present."""
    squawk = str(aircraft.get("squawk") or "").strip()
    return squawk.zfill(4) if squawk.isdigit() and len(squawk) <= 4 else squawk


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


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return initial bearing in degrees from point 1 to point 2."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    y = math.sin(delta_lon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def compass_ru(bearing: float) -> str:
    """Return a compact Russian compass direction."""
    directions = (
        "север",
        "северо-восток",
        "восток",
        "юго-восток",
        "юг",
        "юго-запад",
        "запад",
        "северо-запад",
    )
    return directions[int((bearing + 22.5) // 45) % 8]


def point_in_polygon(lon: float, lat: float, polygon: tuple[tuple[float, float], ...]) -> bool:
    """Return true when lon/lat is inside the configured window view polygon."""
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def inside_window_azimuth(bearing: float) -> bool:
    """Match the live apartment window azimuth model."""
    return abs(WINDOW_VIEW_AZIMUTH_DEGREES - bearing) < WINDOW_VIEW_HALF_ANGLE_DEGREES


def project_position(
    lat: float,
    lon: float,
    *,
    track_degrees: float,
    speed_kt: float,
    seconds: float,
) -> tuple[float, float]:
    """Project a position along current track and speed."""
    distance_km = max(speed_kt, 0.0) * 1.852 * seconds / 3600.0
    radius_km = 6371.0088
    angular_distance = distance_km / radius_km
    bearing = math.radians(track_degrees)
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), ((math.degrees(lon2) + 540.0) % 360.0) - 180.0


def human_visible_radius_km(
    *,
    outside_illuminance_lux: float | None = None,
    sun_elevation_degrees: float | None = None,
    weather_visibility_km: float | None = None,
) -> float:
    """Return the practical aircraft visibility radius for current light/weather."""
    daylight = False
    low_light = False
    if sun_elevation_degrees is not None:
        daylight = sun_elevation_degrees >= 4.0
        low_light = sun_elevation_degrees < 1.0
    if outside_illuminance_lux is not None:
        daylight = daylight or outside_illuminance_lux >= 5000.0
        low_light = low_light or outside_illuminance_lux < 1500.0

    if low_light and not daylight:
        radius = (
            DEFAULT_NIGHT_HUMAN_VISIBLE_RADIUS_KM
            if (
                sun_elevation_degrees is not None
                and sun_elevation_degrees < -4.0
            )
            or (
                outside_illuminance_lux is not None
                and outside_illuminance_lux < 250.0
            )
            else DEFAULT_LOW_LIGHT_HUMAN_VISIBLE_RADIUS_KM
        )
    elif daylight:
        radius = DEFAULT_DAY_HUMAN_VISIBLE_RADIUS_KM
    else:
        radius = DEFAULT_WINDOW_VIEW_RADIUS_KM
    if weather_visibility_km is not None and weather_visibility_km > 0:
        radius = min(radius, weather_visibility_km)
    return max(1.0, radius)


def runway_staging_preopen_needed(aircraft: dict[str, Any], lat: float, lon: float) -> bool:
    """Return true when an aircraft is active near the Batumi runway staging area."""
    altitude = altitude_ft(aircraft)
    speed_kt = parse_float(aircraft.get("gs"))
    seen_pos = parse_float_or(aircraft.get("seen_pos"), 999.0)
    seen = parse_float_or(aircraft.get("seen"), 999.0)
    distance_to_runway_km = haversine_km(
        BATUMI_RUNWAY_STAGING_LAT,
        BATUMI_RUNWAY_STAGING_LON,
        lat,
        lon,
    )
    return (
        seen <= 8.0
        and seen_pos <= 12.0
        and distance_to_runway_km <= DEFAULT_RUNWAY_STAGING_RADIUS_KM
        and altitude is not None
        and altitude <= DEFAULT_RUNWAY_STAGING_MAX_ALTITUDE_FT
        and (speed_kt is None or speed_kt <= DEFAULT_RUNWAY_STAGING_MAX_SPEED_KT)
    )


def window_view_attrs(
    aircraft: dict[str, Any],
    *,
    home_latitude: float,
    home_longitude: float,
    outside_illuminance_lux: float | None = None,
    sun_elevation_degrees: float | None = None,
    weather_visibility_km: float | None = None,
) -> dict[str, Any]:
    """Return window visibility and curtain preopen attributes for an aircraft."""
    lat = parse_float(aircraft.get("lat"))
    lon = parse_float(aircraft.get("lon"))
    radius_km = human_visible_radius_km(
        outside_illuminance_lux=outside_illuminance_lux,
        sun_elevation_degrees=sun_elevation_degrees,
        weather_visibility_km=weather_visibility_km,
    )
    if lat is None or lon is None:
        return {
            "window_visible": False,
            "window_preopen_needed": False,
            "window_runway_staging": False,
            "window_view_reason": "no position",
            "window_view_projected_lat": None,
            "window_view_projected_lon": None,
            "window_view_lead_seconds": DEFAULT_WINDOW_VIEW_LEAD_SECONDS,
            "window_view_radius_km": round(radius_km, 1),
            "window_distance_km": None,
            "window_bearing_degrees": None,
            "window_direction": "",
            "window_elevation_degrees": None,
        }

    distance_km = haversine_km(home_latitude, home_longitude, lat, lon)
    bearing = bearing_degrees(home_latitude, home_longitude, lat, lon)
    altitude = altitude_ft(aircraft)
    position_age_seconds = parse_float(aircraft.get("position_age_seconds"))
    stale_history_position = (
        aircraft.get("position_source") == "skyaware_history"
        and position_age_seconds is not None
        and position_age_seconds > 12.0
    )
    elevation_degrees = (
        math.degrees(math.atan((altitude * FEET_TO_KILOMETERS) / distance_km))
        if altitude is not None and distance_km > 0
        else None
    )
    inside_polygon = point_in_polygon(lon, lat, WINDOW_VIEW_POLYGON_LON_LAT)
    inside_azimuth = inside_window_azimuth(bearing)
    inside_radius = distance_km <= radius_km
    visible = inside_polygon and inside_azimuth and inside_radius and not stale_history_position
    runway_staging = runway_staging_preopen_needed(aircraft, lat, lon)

    projected_lat = None
    projected_lon = None
    projected_visible = False
    projected_lead_seconds = DEFAULT_WINDOW_VIEW_LEAD_SECONDS
    track = parse_float(aircraft.get("track"))
    speed = parse_float(aircraft.get("gs"))
    if not stale_history_position and track is not None and speed is not None and speed > 5:
        step = DEFAULT_WINDOW_VIEW_PROJECTION_STEP_SECONDS
        for sample_index in range(1, int(DEFAULT_WINDOW_VIEW_LEAD_SECONDS // step) + 1):
            lead_seconds = sample_index * step
            sample_lat, sample_lon = project_position(
                lat,
                lon,
                track_degrees=track,
                speed_kt=speed,
                seconds=lead_seconds,
            )
            sample_distance_km = haversine_km(
                home_latitude,
                home_longitude,
                sample_lat,
                sample_lon,
            )
            sample_bearing = bearing_degrees(
                home_latitude,
                home_longitude,
                sample_lat,
                sample_lon,
            )
            if (
                point_in_polygon(sample_lon, sample_lat, WINDOW_VIEW_POLYGON_LON_LAT)
                and inside_window_azimuth(sample_bearing)
                and sample_distance_km <= radius_km
            ):
                projected_lat = sample_lat
                projected_lon = sample_lon
                projected_lead_seconds = lead_seconds
                projected_visible = True
                break

    reason_parts: list[str] = []
    if stale_history_position:
        reason_parts.append(f"stale SkyAware history position {position_age_seconds:.0f}s old")
    elif visible:
        reason_parts.append("inside window view polygon")
    if projected_visible and not visible:
        reason_parts.append(f"projected into window view in {projected_lead_seconds:.0f}s")
    if runway_staging and not visible and not projected_visible:
        reason_parts.append("aircraft active on runway staging area")
    if inside_polygon and inside_radius and not inside_azimuth:
        reason_parts.append(
            "outside window azimuth "
            f"{WINDOW_VIEW_AZIMUTH_DEGREES:.0f}+/-{WINDOW_VIEW_HALF_ANGLE_DEGREES:.0f}"
        )
    if (inside_polygon or projected_visible) and not inside_radius:
        reason_parts.append(f"outside human-visible {radius_km:.0f} km window radius")
    if not reason_parts:
        reason_parts.append("outside window view polygon")
    if visible:
        projected_lead_seconds = 0.0

    return {
        "window_visible": visible,
        "window_preopen_needed": visible or projected_visible or runway_staging,
        "window_runway_staging": runway_staging,
        "window_view_reason": "; ".join(reason_parts),
        "window_view_projected_lat": round(projected_lat, 6) if projected_lat is not None else None,
        "window_view_projected_lon": round(projected_lon, 6) if projected_lon is not None else None,
        "window_view_lead_seconds": (
            0.0 if runway_staging and not projected_visible else projected_lead_seconds
        ),
        "window_view_radius_km": round(radius_km, 1),
        "window_distance_km": round(distance_km, 1),
        "window_bearing_degrees": round(bearing, 1),
        "window_direction": compass_ru(bearing),
        "window_elevation_degrees": (
            round(elevation_degrees, 1) if elevation_degrees is not None else None
        ),
    }


def make_key(aircraft: dict[str, Any], phase: str) -> str:
    """Make a stable event key for deduplication in automations."""
    hex_id = str(aircraft.get("hex") or "unknown").strip().lower()
    flight = flight_label(aircraft).replace(" ", "")
    if phase == "emergency_squawk":
        return f"{phase}:{hex_id}:{flight}:{squawk_code(aircraft)}"[:240]
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


def _metadata_text(aircraft: dict[str, Any], enrichment: dict[str, Any]) -> str:
    """Return searchable public metadata text for interest classification."""
    parts = [
        aircraft.get("flight"),
        aircraft.get("hex"),
        aircraft.get("category"),
        enrichment.get("airline_name"),
        enrichment.get("registered_owner"),
        enrichment.get("aircraft_model"),
        enrichment.get("aircraft_type"),
        enrichment.get("operator_flag_code"),
        enrichment.get("adsb_category"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _has_token(text: str, tokens: tuple[str, ...]) -> bool:
    """Return true when any configured token appears in text."""
    return any(token in text for token in tokens)


def _has_standalone_token(text: str, tokens: tuple[str, ...]) -> bool:
    """Return true when any configured token appears as a separate metadata token."""
    return any(
        re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text)
        for token in tokens
    )


def ident_active(aircraft: dict[str, Any]) -> bool:
    """Return true when the aircraft is pressing IDENT/SPI."""
    for key in ("spi", "ident", "special_position_identification"):
        value = aircraft.get(key)
        if value is True:
            return True
        if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes"}:
            return True
    return False


def is_non_icao_address(aircraft: dict[str, Any]) -> bool:
    """Return true for receiver-marked non-ICAO addresses."""
    return str(aircraft.get("hex") or "").strip().startswith("~")


def is_helicopter(aircraft: dict[str, Any], enrichment: dict[str, Any]) -> bool:
    """Return true when metadata suggests a helicopter or rotorcraft."""
    category = str(
        aircraft.get("category") or enrichment.get("adsb_category") or ""
    ).upper()
    text = _metadata_text(aircraft, enrichment)
    return category == "A7" or _has_standalone_token(text, HELICOPTER_TOKENS)


def is_military_aircraft(enrichment: dict[str, Any]) -> bool:
    """Return true when public owner/operator metadata identifies military traffic."""
    owner = str(
        enrichment.get("registered_owner") or enrichment.get("airline_name") or ""
    ).lower()
    operator = str(enrichment.get("operator_flag_code") or "").upper()
    if operator in MILITARY_OPERATOR_SPEECH_RU:
        return True
    return _has_standalone_token(owner, MILITARY_OWNER_TOKENS)


def is_military_tanker(enrichment: dict[str, Any]) -> bool:
    """Return true when military metadata points to an aerial refuelling aircraft."""
    text = " ".join(
        str(enrichment.get(key) or "")
        for key in (
            "airline_name",
            "registered_owner",
            "aircraft_model",
            "aircraft_type",
            "operator_flag_code",
        )
    ).lower()
    return is_military_aircraft(enrichment) and _has_standalone_token(
        text, TANKER_TOKENS
    )


def is_cargo_aircraft(enrichment: dict[str, Any]) -> bool:
    """Return true when operator/model metadata explicitly points to cargo service."""
    haystack = " ".join(
        str(enrichment.get(key) or "")
        for key in (
            "airline_name",
            "registered_owner",
            "aircraft_model",
            "aircraft_type",
            "operator_flag_code",
        )
    ).lower()
    padded = f" {haystack} "
    return _has_standalone_token(haystack, CARGO_OPERATOR_TOKENS) or any(
        token in padded for token in CARGO_TYPE_TOKENS
    )


def is_business_jet(enrichment: dict[str, Any]) -> bool:
    """Return true when model metadata points to a business jet family."""
    aircraft_type = str(enrichment.get("aircraft_type") or "").strip().upper()
    model = str(enrichment.get("aircraft_model") or "").strip().upper()
    return aircraft_type in BUSINESS_JET_TYPE_CODES or _has_standalone_token(
        model, BUSINESS_JET_MODEL_TOKENS
    )


def has_transport_aircraft_model(enrichment: dict[str, Any]) -> bool:
    """Return true when model/type metadata identifies a crewed transport aircraft."""
    text = " ".join(
        str(enrichment.get(key) or "")
        for key in ("aircraft_model", "aircraft_type", "aircraft_model_speech")
    ).upper()
    return bool(TRANSPORT_AIRCRAFT_MODEL_RE.search(text))


def classify_service_type(enrichment: dict[str, Any]) -> tuple[str, float, str]:
    """Classify flight service conservatively for spoken announcements."""
    if is_military_aircraft(enrichment):
        operator = military_operator_speech(enrichment) or "military metadata"
        return "military", 0.9, f"military metadata: {operator}"
    if is_cargo_aircraft(enrichment):
        return "cargo", 0.78, "cargo operator or freighter metadata"
    if is_business_jet(enrichment):
        aircraft_type = str(enrichment.get("aircraft_type") or "").strip()
        model = str(enrichment.get("aircraft_model") or "").strip()
        detail = aircraft_type or model or "business jet metadata"
        return "business_jet", 0.72, f"business jet metadata: {detail}"

    airline_name = str(enrichment.get("airline_name") or "").strip()
    if has_route_details(enrichment) and airline_name in PASSENGER_AIRLINES:
        route = str(enrichment.get("route_summary") or "").strip()
        return (
            "passenger",
            0.74,
            f"scheduled passenger airline with route {route or 'details'}",
        )

    category = str(enrichment.get("adsb_category") or "").upper()
    if category.startswith(("B", "C")):
        return "general_aviation", 0.42, f"ADS-B emitter category {category}"
    return "unknown", 0.0, ""


def _nav_mode_text(nav_modes: Any) -> str:
    if isinstance(nav_modes, list):
        return " ".join(str(item) for item in nav_modes)
    return str(nav_modes or "")


def _has_holding_or_orbit_nav_mode(nav_modes: Any) -> bool:
    items = nav_modes if isinstance(nav_modes, list) else [nav_modes]
    for item in items:
        text = re.sub(r"[_-]+", " ", str(item or "").lower()).strip()
        text = re.sub(r"\s+", " ", text)
        if not text:
            continue
        if text in {"althold", "alt hold", "altitude hold"}:
            continue
        if re.fullmatch(r"(?:autopilot )?(?:alt|altitude) hold(?: tcas)?", text):
            continue
        if re.search(r"\b(?:holding|orbit|orbiting|racetrack)\b", text):
            return True
        if re.search(r"\bhold\b", text) and not re.search(
            r"\b(?:alt|altitude)\s+hold\b", text
        ):
            return True
    return False


def _has_routine_transport_context(enrichment: dict[str, Any]) -> bool:
    """Return true when ordinary transport manoeuvres should not be special."""
    service_type = str(enrichment.get("service_type") or "").strip()
    if service_type == "passenger":
        return True
    return has_route_details(enrichment) or has_transport_aircraft_model(enrichment)


def classify_special_interest(
    aircraft: dict[str, Any],
    enrichment: dict[str, Any],
) -> tuple[str, str, str, float] | None:
    """Classify ADS-B events worth a short observation announcement."""
    altitude = altitude_ft(aircraft)
    vertical_rate = vertical_rate_fpm(aircraft)
    if vertical_rate is not None and vertical_rate <= -3500 and (
        altitude is None or altitude >= 1000
    ):
        if _has_routine_transport_context(enrichment):
            return None
        label = "резкое снижение"
        return (
            "rapid_descent",
            label,
            f"vertical rate {vertical_rate:.0f} fpm",
            0.78 if vertical_rate <= -5000 else 0.7,
        )

    nav_modes = aircraft.get("nav_modes")
    nav_text = _nav_mode_text(nav_modes).lower()
    track_rate = parse_float(aircraft.get("track_rate"))
    ground_speed = parse_float(aircraft.get("gs"))
    if _has_holding_or_orbit_nav_mode(nav_modes):
        return (
            "holding_or_orbit",
            "похоже на ожидание или круги",
            f"navigation mode {nav_text}",
            0.68,
        )
    if (
        track_rate is not None
        and abs(track_rate) >= 2.5
        and ground_speed is not None
        and 60 <= ground_speed <= 260
    ):
        if _has_routine_transport_context(enrichment):
            return None
        return (
            "orbiting",
            "похоже на круговой манёвр",
            f"track rate {track_rate:.1f} deg/s",
            0.58,
        )

    text = _metadata_text(aircraft, enrichment)
    if is_military_tanker(enrichment):
        return (
            "military_tanker",
            "военный самолёт-заправщик",
            "military tanker metadata",
            0.9,
        )
    if _has_standalone_token(text, MEDEVAC_TOKENS):
        return ("medevac", "медицинская или спасательная авиация", "medevac metadata", 0.82)
    if _has_standalone_token(text, POLICE_TOKENS):
        return ("police", "полицейский самолёт или вертолёт", "police metadata", 0.82)
    if _has_standalone_token(text, CALIBRATION_TOKENS):
        return (
            "calibration",
            "похоже на проверочный или калибровочный полёт",
            "calibration metadata",
            0.8,
        )
    if is_helicopter(aircraft, enrichment) and not str(aircraft.get("flight") or "").strip():
        return (
            "helicopter_no_callsign",
            "вертолёт без позывного",
            "helicopter metadata without callsign",
            0.72,
        )
    if _has_standalone_token(text, DRONE_TOKENS) and not has_transport_aircraft_model(
        enrichment
    ):
        return ("drone", "похоже на беспилотник", "drone metadata", 0.82)
    return None


def service_object_word(enrichment: dict[str, Any]) -> str:
    """Return a short object phrase that avoids overclaiming service type."""
    service_type = str(enrichment.get("service_type") or "unknown")
    confidence = parse_float(enrichment.get("service_type_confidence")) or 0.0
    if service_type == "passenger" and confidence >= 0.7 and has_route_details(enrichment):
        return "пассажирский рейс"
    if service_type == "cargo" and confidence >= 0.7:
        return "грузовой самолёт"
    if service_type == "business_jet" and confidence >= 0.65:
        return "бизнес-джет"
    if service_type == "general_aviation" and confidence >= 0.5:
        return "частный самолёт"
    return "рейс" if has_route_details(enrichment) else "самолёт"


def military_operator_speech(enrichment: dict[str, Any]) -> str:
    """Return a Russian label for a military operator when known."""
    operator = str(enrichment.get("operator_flag_code") or "").upper()
    if operator in MILITARY_OPERATOR_SPEECH_RU:
        return MILITARY_OPERATOR_SPEECH_RU[operator]
    owner = str(enrichment.get("registered_owner") or "").strip()
    owner_speech = MILITARY_OWNER_SPEECH_RU.get(owner.casefold())
    if owner_speech:
        return owner_speech
    return tts_cyrillic_text(owner)


def spell_alnum_token_ru(token: str) -> str:
    """Spell a compact Latin/digit token in Russian for TTS."""
    words: list[str] = []
    for char in token.strip().upper():
        if char in DIGIT_RU:
            words.append(DIGIT_RU[char])
        elif char in LATIN_LETTER_SPEECH_RU:
            words.append(LATIN_LETTER_SPEECH_RU[char])
    return " ".join(words)


def _transliterate_latin_word_ru(word: str) -> str:
    """Return a rough Cyrillic rendering for an unmapped Latin word."""
    if not word:
        return ""
    mapped = LATIN_WORD_TRANSLITERATION_RU.get(word.casefold())
    if mapped:
        return mapped

    normalized = unicodedata.normalize("NFKD", word.translate(LATIN_SPECIAL_BASE_CHARS))
    ascii_base = "".join(char for char in normalized if not unicodedata.combining(char))
    lower = ascii_base.casefold()
    result: list[str] = []
    index = 0
    while index < len(lower):
        for latin, cyrillic in LATIN_TRANSLITERATION_DIGRAPHS_RU:
            if lower.startswith(latin, index):
                result.append(cyrillic)
                index += len(latin)
                break
        else:
            result.append(LATIN_TRANSLITERATION_CHARS_RU.get(lower[index], lower[index]))
            index += 1

    transliterated = "".join(result)
    return transliterated[:1].upper() + transliterated[1:] if word[:1].isupper() else transliterated


def _latin_token_speech_ru(match: re.Match[str]) -> str:
    """Render one Latin token without leaving ASCII letters for TTS."""
    token = match.group(0)
    stripped = token.strip()
    leading = stripped[: len(stripped) - len(stripped.lstrip("([{"))]
    stripped_tail = stripped[len(leading) :]
    core = stripped_tail.rstrip(".,:;!?)]}")
    trailing = stripped_tail[len(core) :]
    upper = core.upper()
    mapped = LATIN_TOKEN_SPEECH_RU.get(upper)
    if mapped:
        return f"{leading}{mapped}{trailing}"
    if any(char.isdigit() for char in core):
        spoken = spell_alnum_token_ru(core)
        return f"{leading}{spoken or core}{trailing}"
    if core.isupper() and len(core) <= 8:
        spoken = spell_alnum_token_ru(core)
        return f"{leading}{spoken or core}{trailing}"
    return f"{leading}{_transliterate_latin_word_ru(core)}{trailing}"


def tts_cyrillic_text(text: str) -> str:
    """Remove Latin letters from announcement text before it reaches TTS."""
    if not LATIN_LETTER_RE.search(text):
        return text
    return LATIN_TOKEN_RE.sub(_latin_token_speech_ru, text)


def _speech_lookup_key(value: str) -> str:
    """Return a Unicode-stable key for public aviation names."""
    ascii_base = value.translate(LATIN_SPECIAL_BASE_CHARS)
    decomposed = unicodedata.normalize("NFKD", ascii_base)
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_marks.casefold().split())


def spoken_flight(flight: str, airline_icao: str = "", airline_iata: str = "") -> str:
    """Turn AIZ414/RWZ553 into a short TTS-friendly flight number."""
    token = flight.strip().replace(" ", "").upper()
    if token in {"", "UNKNOWN"}:
        return ""
    for prefix, prefix_speech in CALLSIGN_PREFIX_SPEECH_RU.items():
        if token.startswith(prefix) and token[len(prefix) :].isdigit():
            number = " ".join(DIGIT_RU.get(char, char) for char in token[len(prefix) :])
            return f"{prefix_speech} {number}".strip()
    for prefix in (airline_icao.strip().upper(), airline_iata.strip().upper()):
        if prefix and token.startswith(prefix):
            token = token[len(prefix):]
            break
    if token and token.isdigit():
        return " ".join(DIGIT_RU.get(char, char) for char in token)
    if len(token) > 3 and token[:3].isalpha() and token[3:].isdigit():
        return " ".join(DIGIT_RU.get(char, char) for char in token[3:])
    if token and token.isalnum() and LATIN_LETTER_RE.search(token):
        return spell_alnum_token_ru(token)
    return tts_cyrillic_text(flight.strip())


def has_callsign_prefix_speech_mapping(flight: str) -> bool:
    """Return true when a long callsign prefix has explicit speech mapping."""
    token = flight.strip().replace(" ", "").upper()
    match = re.fullmatch(r"([A-Z]{4,})\d+", token)
    return not match or match.group(1) in CALLSIGN_PREFIX_SPEECH_RU


def known_airline_for_callsign(flight: str) -> tuple[str, str]:
    """Return known airline name and callsign prefix for route API gaps."""
    token = flight.strip().replace(" ", "").upper()
    for prefix, airline_name in KNOWN_AIRLINE_BY_CALLSIGN_PREFIX.items():
        if token.startswith(prefix):
            return airline_name, prefix
    return "", ""


def known_route_for_callsign(flight: str) -> dict[str, str]:
    """Return known local route metadata for callsigns missing from public APIs."""
    token = flight.strip().replace(" ", "").upper()
    route = KNOWN_ROUTE_BY_CALLSIGN.get(token)
    return dict(route) if route is not None else {}


def airline_speech(airline_name: str) -> str:
    """Return a TTS-friendly airline name when we know one."""
    name = " ".join(airline_name.strip().split())
    if not name:
        return ""
    if name in AIRLINE_SPEECH_RU:
        return AIRLINE_SPEECH_RU[name]
    folded = _speech_lookup_key(name)
    if folded in AIRLINE_SPEECH_ALIASES_RU:
        return AIRLINE_SPEECH_ALIASES_RU[folded]
    for known_name, speech in AIRLINE_SPEECH_RU.items():
        if _speech_lookup_key(known_name) == folded:
            return speech
    return tts_cyrillic_text(name)


def spoken_model(model: str, aircraft_type: str = "") -> str:
    """Turn common aircraft model strings into Russian TTS-friendly text."""
    text = f"{model} {aircraft_type}".upper()
    if (
        "C-130" in text
        or "C130" in text
        or "C30J" in text
        or "HERCULES" in text
    ):
        return "Си-сто тридцать Геркулес"
    if "C-12" in text or "C12" in text or "HURON" in text:
        return "Си-двенадцать Хьюрон"
    if "C-146" in text or "C146" in text:
        return "Си-сто сорок шесть"
    if "A400" in text:
        return "Аэробус А-четыреста"
    if "TU-204" in text or "T204" in text:
        return "Ту-двести четыре"
    if "TU-214" in text or "T214" in text:
        return "Ту-двести четырнадцать"
    if "A220" in text or "BCS3" in text or "BCS1" in text:
        return "Аэробус А-двести двадцать"
    if "A19N" in text or "A319" in text:
        return "Аэробус триста девятнадцать"
    if "A20N" in text or "A320" in text:
        return "Аэробус триста двадцать"
    if "A21N" in text or "A321" in text:
        return "Аэробус триста двадцать один"
    if "A332" in text or "A330" in text:
        return "Аэробус триста тридцать"
    if "A35K" in text or "A350" in text:
        return "Аэробус триста пятьдесят"
    if "B38M" in text or "737 MAX 8" in text or re.search(r"\b737-8(?!00)\b", text):
        return "Боинг семьсот тридцать семь Макс восемь"
    if "B39M" in text or "737 MAX 9" in text or re.search(r"\b737-9(?!00)\b", text):
        return "Боинг семьсот тридцать семь Макс девять"
    if "B737" in text or "B738" in text or "B739" in text or "737" in text:
        return "Боинг семьсот тридцать семь"
    if "B752" in text or "757" in text:
        return "Боинг семьсот пятьдесят семь"
    if "B763" in text or "767" in text:
        return "Боинг семьсот шестьдесят семь"
    if "B77" in text or "777" in text:
        return "Боинг семьсот семьдесят семь"
    if "B78" in text or "787" in text:
        return "Боинг семьсот восемьдесят семь"
    if "IL76" in text or "IL-76" in text:
        return "Ил-семьдесят шесть"
    if "E190" in text:
        return "Эмбраер сто девяносто"
    if "E195" in text:
        return "Эмбраер сто девяносто пять"
    if "E170" in text or "E75" in text:
        return "Эмбраер сто семьдесят"
    if "CRJ" in text:
        return "Си-ар-джей"
    if "PA-46" in text or "M500" in text:
        return "Пайпер M500"
    if "ASTRA" in text or "1125" in text:
        return "Астра эс-пи-икс"
    if "FALCON 2000" in text:
        return "Дассо Фалькон две тысячи"
    if "CHALLENGER 300" in text or "CL30" in text:
        return "Бомбардье Челленджер трёхсотый"
    if "CHALLENGER 350" in text or "CL35" in text:
        return "Бомбардье Челленджер триста пятидесятый"
    if "CHALLENGER 604" in text:
        return "Бомбардье Челленджер шестьсот четвёртый"
    if "CHALLENGER 605" in text:
        return "Бомбардье Челленджер шестьсот пятый"
    if "CHALLENGER 650" in text:
        return "Бомбардье Челленджер шестьсот пятидесятый"
    if "CHALLENGER" in text or "CL60" in text or "CL65" in text:
        return "Бомбардье Челленджер"
    if "GL6T" in text or "GLOBAL 6000" in text:
        return "Бомбардье Глобал шесть тысяч"
    if "GL5T" in text or "GLOBAL 5000" in text:
        return "Бомбардье Глобал пять тысяч"
    if "G650" in text or "GLF6" in text:
        return "Гольфстрим Джи-шестьсот пятьдесят"
    if "G550" in text or "GLF5" in text:
        return "Гольфстрим Джи-пятьсот пятьдесят"
    if "GLF4" in text:
        return "Гольфстрим четыре"
    if "GULFSTREAM" in text or "GLF" in text:
        return "Гольфстрим"
    if "H25B" in text or "850XP" in text:
        return "Хокер восемьсот пятьдесят икс пи"
    if "SU95" in text or "SSJ" in text:
        return "Суперджет"
    if "C208" in text or "CARAVAN" in text:
        return "Цессна Караван"
    if "EUROFOX" in text or "AEROPRO" in text:
        return "Еврофокс"
    if "L410" in text or "LET" in text:
        return "Лет четыреста десять Турболет, небольшой двухмоторный турбовинтовой"
    return tts_cyrillic_text(model.strip())


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


def normalized_airport_city(value: str) -> str:
    """Return a stable lookup key from route API or airport-board city labels."""
    label = value.split("(")[0].replace("-", " ").strip()
    return " ".join(label.split()).title()


def airport_detail_speech(airport: dict[str, Any]) -> str:
    """Return a specific airport name when route data identifies one."""
    code = str(airport.get("iata_code") or "").strip().upper()
    if code in AIRPORT_DETAIL_SPEECH_RU:
        return AIRPORT_DETAIL_SPEECH_RU[code]
    name = normalized_airport_city(str(airport.get("name") or ""))
    return AIRPORT_NAME_DETAIL_SPEECH_RU.get(name, "")


def has_airline_speech_mapping(airline_name: str) -> bool:
    """Return true when an airline/operator has an explicit speech mapping."""
    name = " ".join(airline_name.strip().split())
    if not name:
        return True
    folded = _speech_lookup_key(name)
    if name in AIRLINE_SPEECH_RU or folded in AIRLINE_SPEECH_ALIASES_RU:
        return True
    return any(_speech_lookup_key(known_name) == folded for known_name in AIRLINE_SPEECH_RU)


def has_airport_speech_mapping(airport: dict[str, Any] | None, *, direction: str) -> bool:
    """Return true when an airport/city has an explicit Russian speech mapping."""
    if not isinstance(airport, dict):
        return True
    code = str(airport.get("iata_code") or airport.get("icao_code") or "").strip().upper()
    if direction == "route":
        if code in AIRPORT_CODE_ROUTE_RU:
            return True
    elif code in (AIRPORT_CODE_TO_RU if direction == "to" else AIRPORT_CODE_FROM_RU):
        return True
    municipality = normalized_airport_city(str(airport.get("municipality") or ""))
    name = normalized_airport_city(str(airport.get("name") or ""))
    city_map = (
        CITY_ROUTE_RU
        if direction == "route"
        else CITY_TO_RU
        if direction == "to"
        else CITY_FROM_RU
    )
    return any(label in city_map for label in (municipality, name)) or bool(
        airport_detail_speech(airport)
    )


def airport_speech(airport: dict[str, Any] | None, *, direction: str) -> str:
    """Return a TTS-friendly city name for origin/destination."""
    if not isinstance(airport, dict):
        return ""
    code = str(airport.get("iata_code") or airport.get("icao_code") or "").strip().upper()
    code_speech = (
        AIRPORT_CODE_TO_RU if direction == "to" else AIRPORT_CODE_FROM_RU
    ).get(code)
    if code_speech:
        return code_speech
    municipality = normalized_airport_city(str(airport.get("municipality") or ""))
    name = normalized_airport_city(str(airport.get("name") or ""))
    city_map = CITY_TO_RU if direction == "to" else CITY_FROM_RU
    airport_detail = airport_detail_speech(airport)
    for label in (municipality, name):
        if label in city_map:
            city = city_map[label]
            if airport_detail and airport_detail != city:
                return f"{city}, {airport_detail}"
            return city
    if airport_detail:
        return airport_detail
    return municipality or name or code


def airport_route_speech(airport: dict[str, Any] | None) -> str:
    """Return a neutral TTS-friendly airport label for route pairs."""
    if not isinstance(airport, dict):
        return ""
    code = str(airport.get("iata_code") or airport.get("icao_code") or "").strip().upper()
    if code in AIRPORT_CODE_ROUTE_RU:
        return AIRPORT_CODE_ROUTE_RU[code]
    municipality = normalized_airport_city(str(airport.get("municipality") or ""))
    name = normalized_airport_city(str(airport.get("name") or ""))
    city_map = CITY_ROUTE_RU
    airport_detail = airport_detail_speech(airport)
    for label in (municipality, name):
        if label in city_map:
            city = city_map[label]
            if airport_detail and airport_detail != city:
                return f"{city}, {airport_detail}"
            return city
    if airport_detail:
        return airport_detail
    return municipality or name or code


def has_aircraft_model_speech_mapping(model: str, aircraft_type: str = "") -> bool:
    """Return true when model/type speech is not only generic Latin fallback."""
    raw = model.strip()
    if not raw:
        return True
    return spoken_model(raw, aircraft_type) != tts_cyrillic_text(raw)


def route_endpoint_speech(enrichment: dict[str, Any], direction: str) -> str:
    """Return a neutral route endpoint label."""
    name = str(enrichment.get(f"{direction}_name") or "").strip()
    iata = str(enrichment.get(f"{direction}_iata") or "").strip()
    airport = {
        "iata_code": iata,
        "municipality": name,
        "name": name,
    }
    return airport_route_speech(airport) or str(
        enrichment.get(f"{direction}_speech") or name
    ).strip()


def route_pair_speech(enrichment: dict[str, Any]) -> str:
    """Return a neutral route pair such as 'Ларнака - Кутаиси'."""
    origin = route_endpoint_speech(enrichment, "origin")
    destination = route_endpoint_speech(enrichment, "destination")
    return f"{origin} - {destination}" if origin and destination else ""


def novelty_reason(enrichment: dict[str, Any], phase: str) -> str:
    """Return why a candidate should be announced as unusual."""
    reasons: list[str] = []
    airline_name = str(enrichment.get("airline_name") or "").strip()
    if airline_name and airline_speech(airline_name) == airline_name:
        reasons.append(f"новая авиакомпания {airline_name}")
    model = str(enrichment.get("aircraft_model") or enrichment.get("aircraft_type") or "").strip()
    model_speech = str(enrichment.get("aircraft_model_speech") or "").strip()
    if model and (not model_speech or model_speech == model):
        reasons.append(f"новый тип {model}")
    return "; ".join(reasons)


def has_route_details(enrichment: dict[str, Any]) -> bool:
    """Return true when public data confirms route-like flight context."""
    route_fields = (
        "origin_iata",
        "origin_name",
        "origin_speech",
        "destination_iata",
        "destination_name",
        "destination_speech",
        "route_summary",
        "route_source",
        "scheduled_departure_local",
    )
    return any(str(enrichment.get(field) or "").strip() for field in route_fields)


def has_routine_speech_context(enrichment: dict[str, Any]) -> bool:
    """Return true when a routine aircraft announcement has useful context."""
    if has_route_details(enrichment):
        return True
    context_fields = (
        "airline_name",
        "registered_owner",
    )
    return any(str(enrichment.get(field) or "").strip() for field in context_fields)


def suppress_unhelpful_flight_label(
    flight: str,
    *,
    airline: str,
    enrichment: dict[str, Any],
) -> bool:
    """Return true when the flight label is likely just receiver noise or a tail."""
    if not airline:
        return False
    token = flight.strip().replace(" ", "").replace("-", "").upper()
    if not token:
        return False
    if _is_hex_token(token):
        return True
    if re.fullmatch(r"[A-Z]{4,}", token):
        return True
    prefix_match = re.fullmatch(r"([A-Z]{4,})[0-9A-Z]+", token)
    return bool(
        prefix_match
        and prefix_match.group(1) not in CALLSIGN_PREFIX_SPEECH_RU
        and is_military_aircraft(enrichment)
    )


def include_flight_number_in_speech(
    *,
    phase: str,
    airline: str,
    enrichment: dict[str, Any],
    flight: str = "",
) -> bool:
    """Return true when the flight number adds useful spoken identity."""
    if not airline:
        return True
    if suppress_unhelpful_flight_label(
        flight,
        airline=airline,
        enrichment=enrichment,
    ):
        return False
    if phase in {
        "positioned_approach",
        "positioned_landing",
        "positioned_takeoff",
        "positioned_runway_staging",
        "positioned_low_nearby",
        "no_position_nearby",
    } and has_route_details(enrichment):
        return False
    return True


def build_announcement(
    aircraft: dict[str, Any],
    phase: str,
    confidence: float,
    enrichment: dict[str, Any],
) -> str:
    """Build the short spoken announcement."""
    if phase == "no_position_nearby" and (
        not has_route_details(enrichment) or confidence < 0.68
    ):
        return ""
    if phase in {
        "positioned_approach",
        "positioned_landing",
        "positioned_takeoff",
        "positioned_runway_staging",
        "positioned_low_nearby",
    } and not has_routine_speech_context(enrichment):
        return ""

    label = flight_label(aircraft)
    fallback_label = "" if _is_hex_token(label) or label == "unknown" else label
    airline_name = str(
        enrichment.get("airline_name") or enrichment.get("registered_owner") or ""
    ).strip()
    airline = airline_speech(airline_name)
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
    route_pair = route_pair_speech(enrichment)
    flight_number = str(enrichment.get("spoken_flight") or label).strip()
    if _is_hex_token(flight_number):
        flight_number = ""
    interest_type = str(enrichment.get("interest_type") or "").strip()
    has_position = (
        parse_float(aircraft.get("lat")) is not None
        and parse_float(aircraft.get("lon")) is not None
    )

    if phase == "military_visible":
        base = "Военный самолёт в зоне видимости"
    elif phase == "emergency_squawk":
        base = "Нештатная ситуация у самолёта"
    elif phase == "special_interest":
        if interest_type == "helicopter_no_callsign":
            base = (
                "Вертолёт в зоне видимости без позывного"
                if has_position
                else "Вертолёт без координат и без позывного"
            )
        else:
            base = "Интересный самолёт в зоне видимости"
    elif phase == "kutaisi_route":
        if str(enrichment.get("destination_iata") or "").upper() == "KUT":
            base = "Информация для наблюдения: рейс на Кутаиси"
        elif str(enrichment.get("origin_iata") or "").upper() == "KUT":
            base = "Информация для наблюдения: рейс из Кутаиси"
        else:
            base = "Информация для наблюдения: рейс через Кутаиси"
    elif phase == "no_position_nearby":
        origin_iata = str(enrichment.get("origin_iata") or "").strip().upper()
        destination_iata = str(enrichment.get("destination_iata") or "").strip().upper()
        if origin_iata == "BUS":
            base = "Приёмник видит вылет без координат"
        elif destination_iata == "BUS":
            base = "Приёмник видит прилёт без координат"
        else:
            base = "Приёмник видит самолёт без координат"
    elif phase == "positioned_approach":
        base = "Заходит на посадку"
    elif phase == "positioned_landing":
        base = "Заходит на посадку"
    elif phase == "positioned_takeoff":
        base = "Вылетает"
    elif phase == "positioned_runway_staging":
        base = "Самолёт у взлётной полосы"
    elif phase == "positioned_low_nearby":
        base = "Самолёт рядом"
    else:
        base = "Самолёт"

    if phase == "military_visible":
        operator = military_operator_speech(enrichment)
        if suppress_unhelpful_flight_label(
            label,
            airline=operator,
            enrichment=enrichment,
        ):
            flight_number = ""
        subject = " ".join(part for part in [operator, flight_number] if part)
    else:
        subject_parts = [airline]
        if include_flight_number_in_speech(
            phase=phase,
            airline=airline,
            enrichment=enrichment,
            flight=label,
        ):
            subject_parts.append(flight_number)
        subject = " ".join(part for part in subject_parts if part)
    if phase in {
        "positioned_approach",
        "positioned_landing",
        "positioned_takeoff",
        "positioned_runway_staging",
        "positioned_low_nearby",
    }:
        object_word = service_object_word(enrichment)
        identity = subject or fallback_label
        if phase == "positioned_low_nearby":
            sentence = (
                f"{base}: {object_word} {identity}."
                if identity
                else f"{base}: {object_word}."
            )
        else:
            sentence = (
                f"{base} {object_word} {identity}."
                if identity
                else f"{base} {object_word}."
            )
    else:
        identity = subject or fallback_label
        sentence = f"{base}: {identity}." if identity else f"{base}."
    reason = novelty_reason(enrichment, phase)
    if reason:
        sentence = f"Особое объявление. {sentence}"

    extra: list[str] = []
    if phase == "emergency_squawk":
        meaning = INTERESTING_SQUAWKS.get(
            squawk_code(aircraft),
            ("нештатная ситуация", ""),
        )[0]
        extra.append(meaning)
        if route_pair:
            extra.append(route_pair)
    elif phase == "special_interest":
        interest_label = str(enrichment.get("interest_label") or "").strip()
        if interest_label and interest_type != "helicopter_no_callsign":
            extra.append(interest_label)
        if route_pair:
            extra.append(route_pair)
    elif phase == "military_visible":
        interest_label = str(enrichment.get("interest_label") or "").strip()
        if interest_label:
            extra.append(interest_label)
        route = str(enrichment.get("route_summary") or "").strip()
        if route:
            extra.append(route)
    elif phase == "kutaisi_route":
        if route_pair:
            extra.append(route_pair)
    elif phase == "no_position_nearby":
        if route_pair:
            extra.append(route_pair)
    elif phase in {"positioned_approach", "positioned_landing"}:
        if origin:
            extra.append(f"Из {origin}")
        elif destination:
            extra.append(f"В {destination}, откуда летит, пока не определено")
    elif phase in {"positioned_takeoff", "positioned_runway_staging"}:
        if destination:
            extra.append(f"В {destination}")
        elif origin:
            extra.append(f"Из {origin}, куда летит, пока не определено")
    elif route_pair:
        extra.append(route_pair)
    if model:
        extra.append(model)
    if built_year:
        extra.append(built_year)
    if extra:
        sentence = f"{sentence} {', '.join(extra)}."
    return tts_cyrillic_text(sentence)


def movement_family(phase: str) -> str:
    """Return the broad local movement family for follow-up boundaries."""
    if phase in {"positioned_approach", "positioned_landing"}:
        return "arrival"
    if phase in {"positioned_takeoff", "positioned_runway_staging"}:
        return "departure"
    return phase


def build_followup_announcement(
    previous: AircraftCandidate,
    current: AircraftCandidate,
) -> str:
    """Build a short update when more details arrive after the first sighting."""
    if candidate_airframe_key(previous) != candidate_airframe_key(current):
        return ""
    if movement_family(previous.phase) != movement_family(current.phase):
        return ""

    details: list[str] = []
    if (
        candidate_has_real_flight(current)
        and (current.flight != previous.flight or current.airline_name != previous.airline_name)
    ):
        airline = airline_speech(current.airline_name)
        flight = current.spoken_flight or current.flight
        if _is_hex_token(flight):
            flight = ""
        identity_parts = [airline]
        if include_flight_number_in_speech(
            phase=current.phase,
            airline=airline,
            enrichment=current.as_dict(),
            flight=current.flight,
        ):
            identity_parts.append(flight)
        identity = " ".join(part for part in identity_parts if part)
        if identity:
            details.append(f"это {identity}")

    if current.phase in {"positioned_approach", "positioned_landing"}:
        route = current.origin_speech or current.origin_name
        if route and route != (previous.origin_speech or previous.origin_name):
            details.append(f"из {route}")
    elif current.phase == "positioned_takeoff":
        route = current.destination_speech or current.destination_name
        if route and route != (previous.destination_speech or previous.destination_name):
            details.append(f"в {route}")
    else:
        current_route = route_pair_speech(current.as_dict())
        previous_route = route_pair_speech(previous.as_dict())
        if current_route and current_route != previous_route:
            details.append(current_route)

    model = current.aircraft_model_speech or current.aircraft_model or current.aircraft_type
    previous_model = (
        previous.aircraft_model_speech or previous.aircraft_model or previous.aircraft_type
    )
    if model and model != previous_model:
        details.append(model)

    if current.built_year_speech and current.built_year_speech != previous.built_year_speech:
        details.append(current.built_year_speech)

    if len(details) == 1 and details[0].startswith("это "):
        return ""
    if not details:
        return ""
    return tts_cyrillic_text(f"Дополнение: {', '.join(details)}.")


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

    seen = parse_float_or(aircraft.get("seen"), 999.0)
    seen_pos = parse_float_or(aircraft.get("seen_pos"), 999.0)
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
    view_attrs = window_view_attrs(
        aircraft,
        home_latitude=home_latitude,
        home_longitude=home_longitude,
    )
    window_preopen_needed = bool(view_attrs.get("window_preopen_needed"))
    runway_staging = bool(view_attrs.get("window_runway_staging"))

    if runway_staging:
        phase = "positioned_runway_staging"
        confidence = 0.6
        reason_parts.append("active on runway staging area")
    elif (
        distance_km <= max_distance_km
        and altitude <= 2800
        and vertical_rate is not None
        and vertical_rate <= -160
    ):
        phase = "positioned_landing"
        confidence = 0.62
        reason_parts.append(f"descending {vertical_rate:.0f} fpm")
    elif (
        (distance_km <= max_distance_km or window_preopen_needed)
        and altitude <= 3200
        and vertical_rate is not None
        and vertical_rate >= 160
    ):
        phase = "positioned_takeoff"
        confidence = 0.62
        reason_parts.append(f"climbing {vertical_rate:.0f} fpm")
    elif (
        distance_km <= max_distance_km
        and altitude <= 900
        and ground_speed is not None
        and 35 <= ground_speed <= 190
    ):
        phase = "positioned_low_nearby"
        confidence = 0.52
        reason_parts.append(f"low nearby at {ground_speed:.0f} kt")
    elif (
        distance_km <= max_approach_distance_km
        and window_preopen_needed
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
        **view_attrs,
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

    seen = parse_float_or(aircraft.get("seen"), 999.0)
    if seen > max_seen_seconds:
        return None

    rssi = parse_float(aircraft.get("rssi"))
    messages = parse_float_or(aircraft.get("messages"), 0.0)
    altitude = altitude_ft(aircraft)
    flight = str(aircraft.get("flight") or "").strip()
    if altitude is not None and altitude > 5000:
        return None

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
    seen = parse_float_or(aircraft.get("seen"), 999.0)
    seen_pos = parse_float(aircraft.get("seen_pos"))
    if seen > 20.0 and (seen_pos is None or seen_pos > 60.0):
        return None

    phase = ""
    confidence = 0.0
    reason = ""
    origin_iata = str(enrichment.get("origin_iata") or "").upper()
    destination_iata = str(enrichment.get("destination_iata") or "").upper()
    squawk = squawk_code(aircraft)
    if squawk in INTERESTING_SQUAWKS:
        phase = "emergency_squawk"
        confidence = 0.93
        reason = INTERESTING_SQUAWKS[squawk][1]
    else:
        special = classify_special_interest(aircraft, enrichment)
        if special is not None:
            interest_type, interest_label, interest_detail, confidence = special
            enrichment["interest_type"] = interest_type
            enrichment["interest_label"] = interest_label
            enrichment["interest_detail"] = interest_detail
            phase = (
                "military_visible"
                if interest_type == "military_tanker"
                else "special_interest"
            )
            reason = interest_detail

    if not phase and is_military_aircraft(enrichment):
        phase = "military_visible"
        confidence = 0.86
        operator = military_operator_speech(enrichment) or "unknown operator"
        reason = f"military metadata: {operator}"
    elif not phase and "KUT" in {origin_iata, destination_iata}:
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
    announcement_suppressed = False
    announcement_suppression_reason = ""
    if not announcement:
        announcement_suppressed = True
        announcement_suppression_reason = (
            "no-position aircraft is receiver-only and not visually actionable"
            if phase == "no_position_nearby"
            else "routine aircraft has no airline, route, or aircraft context worth speech"
            if phase
            in {
                "positioned_approach",
                "positioned_landing",
                "positioned_takeoff",
                "positioned_runway_staging",
                "positioned_low_nearby",
            }
            else "announcement renderer returned empty"
        )
    window_visible = bool(classifier.get("window_visible"))
    window_preopen_needed = bool(classifier.get("window_preopen_needed"))
    if phase in {"military_visible", "special_interest", "kutaisi_route"}:
        window_visible = bool(classifier.get("window_visible", True))
        window_preopen_needed = bool(classifier.get("window_preopen_needed", window_visible))

    return AircraftCandidate(
        state=make_key(aircraft, phase),
        phase=phase,
        confidence=confidence,
        confidence_reason=str(classifier["reason"]),
        event_key=make_key(aircraft, phase),
        hex=str(aircraft.get("hex") or ""),
        flight=flight_label(aircraft),
        squawk=squawk_code(aircraft),
        announcement=announcement,
        announcement_suppressed=announcement_suppressed,
        announcement_suppression_reason=announcement_suppression_reason,
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
        window_visible=window_visible,
        window_preopen_needed=window_preopen_needed,
        window_view_reason=str(
            classifier.get("window_view_reason") or classifier.get("reason") or ""
        ),
        window_runway_staging=bool(classifier.get("window_runway_staging")),
        window_view_projected_lat=parse_float(classifier.get("window_view_projected_lat")),
        window_view_projected_lon=parse_float(classifier.get("window_view_projected_lon")),
        window_view_lead_seconds=parse_float(classifier.get("window_view_lead_seconds")),
        window_view_radius_km=parse_float(classifier.get("window_view_radius_km")),
        window_distance_km=parse_float(classifier.get("window_distance_km")),
        window_bearing_degrees=parse_float(classifier.get("window_bearing_degrees")),
        window_direction=str(classifier.get("window_direction") or ""),
        window_elevation_degrees=parse_float(classifier.get("window_elevation_degrees")),
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
    match = re.search(
        r"(?:>|^)\s*(?:<b>\s*)?Year built:?\s*(?:</b>\s*)?</td>\s*<td>\s*(\d{4})\b",
        html,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1))
    match = re.search(
        r"<title>\s*Aircraft Data [^,<]+,\s*(\d{4})\b",
        html,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None
