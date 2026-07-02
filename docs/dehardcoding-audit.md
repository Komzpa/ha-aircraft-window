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

- `config_flow.py` only exposes receiver, observer coordinates, candidate
  thresholds, polling, enrichment, and mapping-review options.
- `strings.json` and translations mirror that same narrow schema.
- No option currently identifies the airport, runway area, window direction,
  schedule provider, watched routes, or speech locale.

## Hardcoded Local Context

### Airport Identity And Board

Current assumptions and status:

- `settings.py` now defines the default `local_airport` profile and provider
  settings. `coordinator.py` keeps compatibility aliases such as
  `LOCAL_AIRPORT_IATA`, `BATUMI_AIRPORT_BOARD_BASE_URL`,
  `BATUMI_AIRPORT_BOARD_LEGS`, and `TBILISI_TIMEZONE`, but runtime reads go
  through `runtime_settings`.
- Schedule sensors and docs say "Batumi departure" rather than "configured
  airport departure".
- `CALLSIGN_PREFIX_TO_BOARD_AIRLINE` is tuned for the Batumi airport board.
- `KNOWN_ROUTE_BY_CALLSIGN` contains Vanilla Sky `BUS <-> Natakhtari`.
- Tests describe this as `BatumiAirportBoardTest`, which is accurate today but
  means the provider contract is not yet generic.

Target shape:

- Add a configured `local_airport` object:
  `iata`, `name`, `timezone`, optional `airport_board_provider`, optional
  `terminal_area`, and optional `runway_staging_areas`.
- Move provider-specific Batumi board logic behind a provider interface:
  disabled by default for new generic installs, `batumi_airport_board` as one
  built-in provider.
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
- Home Assistant options do not expose these values yet.

Target shape:

- Add a `view_profile` options object:
  `azimuth_degrees`, `half_angle_degrees`, optional `view_polygon_lon_lat`,
  lead time, projection step, day/low-light/night radius.
- Add `airport_profiles[]` with `iata`, `lat`, `lon`,
  `terminal_radius_km`, `terminal_max_altitude_ft`, and optional staging areas.
- Keep current Batumi values as default profile data, not as logic constants.
- Avoid making every user hand-enter a polygon at first: support the current
  azimuth/half-angle model, with polygon override as an advanced setting.

### Special-Interest Policy

Current assumptions and status:

- Kutaisi is now the default `WatchAirport` in `settings.py`, not a literal
  branch in `interest_candidate`.
- Kinematic-only thresholds and terminal suppression are now in `WatchPolicy`.
- Home Assistant options do not expose `WatchPolicy` yet.

Target shape:

- Add `watch_airports[]` / `watch_routes[]`, each with a reason label and phase
  name. Default can include `KUT` for the current install, but a new user should
  choose their own watched airports.
- Add a `special_interest_policy` object:
  kinematic thresholds, terminal suppression enabled/disabled, and optional
  per-airport overrides.
- Keep emergency squawks and explicit metadata classes as built-in safety
  behavior, not user-maintained text.
- Keep terminal/known-route suppression enabled by default. Other airports will
  also have routine approach turns and descents, so this should be policy, not
  a Batumi exception.

## Hardcoded Speech And Locale

Current assumptions:

- Russian speech tables live in `logic.py`:
  city forms, airport forms, airline/operator forms, callsign prefixes, model
  names, military phrases, digits, years, and Latin transliteration.
- Mapping review is designed to fill Python tables, not a user-owned lexicon.
- README points maintainers at code tables such as `AIRLINE_SPEECH_RU`.

Target shape:

- Introduce a speech profile:
  `speech_locale = "ru"` initially, with built-in Russian pack loaded from data
  files rather than scattered constants.
- Add optional user override packs in storage/options:
  airline names, airport names, callsign prefixes, route fallbacks, model names.
- Keep text human-readable in integration output; TTS stress marks stay outside
  this integration.
- Keep bounded-token matching rules for callsign and airline prefixes. Previous
  fixes show that loose prefix matching can misidentify an aircraft operator.

Migration path:

1. Move speech constants into structured in-repo data modules/files without
   changing behavior.
2. Add lookup wrappers that merge built-in Russian pack plus user overrides.
3. Only then expose user-editable override options or storage.

## External Providers

Current assumptions:

- ADSBDB, HexDB, Airplanes.live, airport-data.com, and Batumi airport board are
  fixed provider URLs.
- Cache TTLs are fixed per provider.

Target shape:

- Keep public provider defaults, but represent them as provider config:
  enabled flag, base URL, timeout, TTL.
- Board providers should be optional because most airports will not have the
  same JSON endpoint shape as Batumi.
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
- Surface configured airport IATA/name in schedule entity attributes.

## Recommended Refactor Order

1. Done: add typed runtime settings helpers for default `local_airport`,
   `view_profile`, `watch_policy`, and `provider_settings`.
2. Done: move window geometry, runway staging, terminal area, watched-airport,
   provider URL, timezone, and local airport IATA reads through those settings
   helpers while keeping current defaults.
3. Move Batumi airport board behind a provider abstraction and make it optional.
4. Expose configured `watch_airports`, local airport, and view profile through
   config/options after migration behavior is designed.
5. Move speech tables into a Russian speech pack and add override merge points.
6. Rename docs/strings from Batumi-specific wording to configured-airport
   wording while preserving existing entity IDs.

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
