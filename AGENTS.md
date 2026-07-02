# Aircraft Window Agent Notes

- When an announcement contains a semantic contradiction, such as "looks like a drone" next to `Airbus A319`, treat it as a classifier bug until proven otherwise. Audit metadata token matching for substring false positives before adding a one-off exception.
- Semantic classifier token tables must match whole metadata tokens or explicitly bounded phrases. Do not let short tokens such as `rpa`, `uas`, `army`, `ups`, or `sf` match inside airline, owner, route, or model names.
- If a new airline, operator, route endpoint, airport, model, or callsign family appears in a live aircraft-window case, prefer runtime speech or route fallback override options for local pronunciations/routes. Promote repeatable built-ins to `custom_components/aircraft_window/speech_ru.py` or `custom_components/aircraft_window/route_fallbacks.py`, and add focused tests as applicable.
- Aircraft-window text should stay human-readable. Pronunciation and Silero stress marks belong in the shared OpenClaw TTS stress lexicon; when adding hard names such as a new operator, update that lexicon and smoke the normalized phrase too.
