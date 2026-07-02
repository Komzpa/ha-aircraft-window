# Dehardcoding Audit

This audit tracks repository areas that still assume one apartment, one local
airport, one airport-board provider, and Russian speech. The target is to make
Aircraft Window reusable by other Home Assistant users without removing the
current Batumi defaults.

## Already Configurable

- Receiver URL: `dump1090_url`.
- Observer coordinates: Home Assistant home coordinates by default, with
  `home_latitude` and `home_longitude` options.
- Candidate distance/altitude/timing thresholds:
  `max_positioned_distance_km`, `max_approach_distance_km`,
  `max_approach_altitude_ft`, `max_no_position_seen_seconds`,
  `scan_interval_seconds`, and enrichment prefetch settings.
- Enrichment enable/disable and mapping-review collection.

These are good foundations, but they do not yet describe the local viewing
geometry or airport context.

Configuration surface today:

- `config_flow.py` exposes receiver, observer coordinates, candidate
  thresholds, polling, enrichment, mapping-review options, local airport
  identity/timezone, window azimuth/radius/projection profile, optional raw
  window polygon JSON, terminal area, runway staging area, watched route airport
  codes, speech locale, and provider base URL/cache options.
- `strings.json` and translations mirror that schema.
- Options still do not expose a friendly polygon editor, a multi-provider
  airport-board registry, or non-Russian speech packs.

## Hardcoded Local Context

### Airport Identity And Board

Current assumptions and status:

- `settings.py` now defines the default `local_airport` profile and provider
  settings. `coordinator.py` keeps compatibility aliases such as
  `LOCAL_AIRPORT_IATA`, `BATUMI_AIRPORT_BOARD_BASE_URL`,
  `BATUMI_AIRPORT_BOARD_LEGS`, and `TBILISI_TIMEZONE`, but runtime reads go
  through `runtime_settings`.
- Basic local airport IATA/name/timezone are configurable through Home
  Assistant config/options. Non-Batumi profiles without a custom name fall back
  to their configured IATA code instead of inheriting the Batumi display name.
  IANA `local_timezone_name` supports DST-aware airport-local schedules, with
  `local_timezone_offset_hours` retained as a fixed-offset fallback.
- `airport_board_provider` is a constrained option backed by the provider
  registry in `board_providers.py`. It can be disabled for generic installs.
  The Batumi board is only used when that provider is `batumi_airport_board`;
  non-Batumi profiles treat the stored Batumi provider default as unset.
- A `json_airport_board` provider can fetch a user-supplied canonical board JSON
  endpoint, so non-Batumi installs can integrate their own adapter/proxy without
  patching Python.
- Schedule sensor/binary-sensor docstrings and README now say configured-airport
  departure while keeping the existing entity IDs, and schedule attributes expose
  the configured local airport IATA/name plus provider source.
- Batumi board callsign-prefix mapping and row matching now live in
  `custom_components/aircraft_window/board_providers.py`.
- Built-in callsign and known-route fallbacks live in
  `custom_components/aircraft_window/route_fallbacks.py`; the current default
  data still includes Vanilla Sky `BUS <-> Natakhtari`, but those built-in
  callsign-prefix and route-by-callsign fallbacks are only inherited by the
  default Batumi profile. Other local-airport profiles use explicit route
  fallback overrides only.
- Tests still group much of this under `BatumiAirportBoardTest`; canonical JSON
  provider coverage is present, but a richer provider registry/test split is
  still pending.

Target shape:

- Add a configured `local_airport` object:
  `iata`, `name`, `timezone`, optional `airport_board_provider`, optional
  `terminal_area`, and optional `runway_staging_areas`.
- Move provider-specific Batumi board logic behind a provider interface:
  disabled by default for new generic installs, `batumi_airport_board` and
  canonical `json_airport_board` as built-in providers.
- Rename user-facing schedule entities/docs to "configured airport" while
  keeping stable entity IDs for backward compatibility.
- Keep a Batumi default profile for existing entries so current behavior does
  not silently disappear during migration.

### Viewing Geometry

Current assumptions and status:

- `settings.py` now defines the default `WindowViewProfile`, runway staging
  areas, and terminal area. `logic.py` keeps compatibility aliases for the old
  constants, but visibility, projection, staging, and terminal suppression reads
  can take a `RuntimeSettings` object.
- Basic azimuth, half-angle, projection lead/step, radius, raw polygon JSON,
  terminal area, and runway staging values are configurable through Home
  Assistant config/options. The Batumi polygon is kept only for the default
  Batumi profile when the polygon option is empty; other local-airport profiles
  fall back to the azimuth/radius model unless a polygon is configured.
- Batumi terminal-area and runway-staging defaults are also inherited only by
  the default Batumi profile. Other local-airport profiles get no terminal or
  staging geometry unless `terminal_area_enabled` or `runway_staging_enabled`
  is set. Legacy non-Batumi entries with custom stored area coordinates are
  treated as enabled during migration.

Target shape:

- Add a `view_profile` options object:
  `azimuth_degrees`, `half_angle_degrees`, optional `view_polygon_lon_lat`,
  lead time, projection step, day/low-light/night radius.
- Add `airport_profiles[]` with `iata`, `lat`, `lon`,
  `terminal_radius_km`, `terminal_max_altitude_ft`, and optional staging areas.
- Keep current Batumi values as default profile data, not as logic constants.
- Avoid making every user hand-enter a polygon: support the current
  azimuth/half-angle model, with raw polygon JSON as an advanced setting and a
  friendlier editor still pending.

### Special-Interest Policy

Current assumptions and status:

- Kutaisi is now the default `WatchAirport` in `settings.py`, not a literal
  branch in `interest_candidate`. It is only inherited by the default Batumi
  profile; other local-airport profiles start with no watched airports unless
  `watch_airports` is explicitly configured with a non-default value.
- Kinematic-only thresholds and terminal suppression are now in `WatchPolicy`.
- Watched route airport codes are configurable through Home Assistant
  config/options. Structured `watch_airports_json` entries can also provide
  custom phase names and reason labels. Kinematic thresholds and terminal
  suppression are also configurable through Home Assistant config/options.

Target shape:

- Continue improving `watch_airports[]` / `watch_routes[]` editing beyond the
  current structured JSON option. Default can include `KUT` for the current
  Batumi install, but a new local airport should not inherit it silently.
- Add a `special_interest_policy` object:
  kinematic thresholds, terminal suppression enabled/disabled, and optional
  per-airport overrides.
- Keep emergency squawks and explicit metadata classes as built-in safety
  behavior, not user-maintained text.
- Keep terminal/known-route suppression enabled by default. Other airports will
  also have routine approach turns and descents, so this should be policy, not
  a Batumi exception.

## Hardcoded Speech And Locale

Current assumptions and status:

- Built-in Russian speech tables live in
  `custom_components/aircraft_window/speech_ru.py`: city forms, airport forms,
  airline/operator forms, callsign prefixes, aircraft-model phrases, military
  phrases, digits, years, and Latin transliteration.
- `RussianSpeechPack` now groups the Russian lookup tables and selected helpers
  accept a speech pack override, including aircraft-model speech rules.
- `speech_locale` is an explicit runtime/config option. The only supported pack
  today is `ru`, so stale/unsupported stored values fall back to Russian instead
  of creating a hidden mixed-locale state.
- Home Assistant options expose JSON-object overrides for airline names,
  airline aliases, origin/destination/route airport codes, and callsign
  prefixes, airport city labels, plus aircraft model/type speech. Options also
  expose JSON-object fallbacks for airline names by callsign prefix and route
  metadata by callsign. Runtime announcements, enrichment, and mapping review
  use the merged speech and fallback packs.
- Mapping review can be resolved by options overrides first; repeatable values
  can still be promoted to built-in tables.

Target shape:

- Add more speech profiles beyond the initial `speech_locale = "ru"` option,
  with built-in packs loaded from data files rather than Python constants.
- Extend the first options surface into a friendlier editor than raw JSON
  fields.
- Keep text human-readable in integration output; TTS stress marks stay outside
  this integration.
- Keep bounded-token matching rules for callsign and airline prefixes. Previous
  fixes show that loose prefix matching can misidentify an aircraft operator.

Migration path:

1. Done for the first Python-data slice: move speech constants into structured
   in-repo modules without changing behavior. A later slice can move those
   tables from Python modules into data files.
2. Done: add lookup wrappers that merge built-in Russian pack plus user
   overrides.
3. Only then expose user-editable override options or storage.

## External Providers

Current assumptions:

- ADSBDB, HexDB, Airplanes.live, Airport-data.com, and Batumi airport board
  base URLs are configurable through options.
- Route, aircraft, built-year, and airport-board cache TTLs are configurable.
- External enrichment and airport-board request timeouts are configurable.

Target shape:

- Keep public provider defaults, but represent them as provider config:
  enabled flag, base URL, timeout, TTL.
- Board providers should be optional because most airports will not have the
  same JSON endpoint shape as Batumi. Canonical JSON endpoints are supported as
  an adapter boundary; native provider plugins/registry remain future work.
- Provider errors should degrade to "no enrichment/board match" rather than
  changing the aircraft classification core.

## Entity And Documentation Language

Current assumptions:

- Several entity descriptions and docs mention Batumi specifically.
- Device name "Aircraft Window" is generic enough, but schedule/preopen names
  imply the Batumi provider.

Target shape:

- Keep existing entity IDs for compatibility.
- Update names/docs to say "configured airport" where possible.
- Keep configured airport IATA/name/provider visible in schedule entity
  attributes.

## Recommended Refactor Order

1. Done: add typed runtime settings helpers for default `local_airport`,
   `view_profile`, `watch_policy`, and `provider_settings`.
2. Done: move window geometry, runway staging, terminal area, watched-airport,
   provider URL, timezone, and local airport IATA reads through those settings
   helpers while keeping current defaults.
3. Partly done: Batumi airport board usage is optional through
   `airport_board_provider`, provider-specific row matching/fetch helpers are
   split into `board_providers.py`, and a canonical `json_airport_board`
   endpoint can be configured. A richer multi-provider registry/config surface
   is still pending.
4. Done: expose configured `watch_airports`, local airport, and basic/raw-JSON
   view profile through config/options.
5. Partly done: add `RussianSpeechPack`, override merge points, move the
   built-in Russian tables out of `logic.py`, and expose first-pass JSON
   speech/model/route fallback override options. A friendlier editor is still
   pending.
6. Done: move built-in callsign and known-route fallback tables out of
   `logic.py` into `route_fallbacks.py`.
7. Done for README and entity docstrings: rename Batumi-specific schedule
   wording to configured-airport wording while preserving existing entity IDs.

This order keeps live behavior stable while removing one category of hardcoding
at a time.

## First Implementation Slice

The lowest-risk first slice is a typed settings module with current defaults:

- `LocalAirportProfile`: `iata="BUS"`, `name="Batumi"`,
  `timezone="Asia/Tbilisi"`, terminal area, runway staging areas.
- `WindowViewProfile`: current azimuth, half-angle, polygon, lead/projection
  parameters, and radius thresholds.
- `WatchPolicy`: current `KUT` route interest and current kinematic thresholds.
- `ProviderSettings`: current enrichment providers and Batumi board enabled for
  migrated/default local profile.

Status: this slice is implemented in code. Do not expose all fields in the Home
Assistant options UI until migration behavior and validation are designed.
