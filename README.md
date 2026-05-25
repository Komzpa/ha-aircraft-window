# Aircraft Window

Aircraft Window is a Home Assistant custom integration for people who live close
enough to an airport to see departures and arrivals from the window.

It polls a local `dump1090`/`readsb`/PiAware `aircraft.json` feed, selects the
best current landing or takeoff candidate near home, enriches it with public
route and aircraft data, and emits a Home Assistant event that can drive Assist
announcements, covers, cameras, or whatever else belongs in your house.

## What it exposes

- `sensor.aircraft_window_candidate`: current candidate state and attributes.
- `sensor.aircraft_window_schedule_preopen`: scheduled Batumi departure preopen
  state from the airport board.
- `sensor.aircraft_window_enrichment_prefetch`: background enrichment cache status.
- `binary_sensor.aircraft_visible_outside_window`: on when the candidate is
  currently in the configured window view geometry.
- `binary_sensor.aircraft_window_curtain_preopen_needed`: on when the current
  candidate is visible, projected into view soon, or active near the runway
  staging area.
- `binary_sensor.aircraft_scheduled_departure_curtain_preopen_needed`: on while
  a scheduled Batumi departure is inside the preopen window.
- `binary_sensor.aircraft_window_candidate_active`: on while a candidate is live.
- `binary_sensor.aircraft_window_unusual_aircraft`: on for an unmapped airline,
  unmapped aircraft type, or no-position aircraft without useful reference data.
- `aircraft_window_candidate` event: fired once per new candidate, with the same
  attributes as the sensor, including `announcement`.

The announcement text includes the phase, airline, flight number, route direction,
aircraft model, and built year when public enrichment data is available. It also
exposes a conservative `service_type` classification (`passenger`, `cargo`,
`military`, `business_jet`, `general_aviation`, or `unknown`) with confidence
and reason attributes. Announcements say "passenger flight" only when route
details match a known passenger airline, "cargo aircraft" only when
cargo/freighter metadata is explicit, "business jet" only when public type/model
metadata identifies a business-jet family, and otherwise keep the neutral
aircraft wording.
If the receiver first sees only the transponder hex and the callsign appears a
few seconds later, Aircraft Window announces the first sighting immediately and
then sends a short "Уточнение..." follow-up with only the newly learned details.
For arrivals, it also has an early `positioned_approach` phase: by default,
descending aircraft below 10,000 ft are tracked out to 60 km, matching the common
landing-light-on operating band before the close runway-window phases take over.
It also watches special-interest traffic already visible to the local receiver:
routes to or from Kutaisi (`KUT`) and likely military aircraft identified from
public owner, operator, or airframe metadata can produce `kutaisi_route` and
`military_visible` events even when they are not landing at the home airport.
Aircraft transmitting emergency transponder codes `7500`, `7600`, or `7700`
produce an `emergency_squawk` event with cautious wording for unlawful
interference, radio failure, or a general emergency. Speech names the situation
without reading raw squawk or transponder details aloud; locally watched routine
squawk codes and other receiver-only technical flags are not voice triggers by
themselves.

## Installation

### HACS custom repository

1. Open HACS.
2. Add `https://github.com/Komzpa/ha-aircraft-window` as a custom repository.
3. Choose category `Integration`.
4. Install **Aircraft Window**.
5. Restart Home Assistant.
6. Add the integration from **Settings -> Devices & services**.

Aircraft Window uses Home Assistant's configured home coordinates automatically.
Manual latitude/longitude overrides are available later in the integration
options if your viewing point is not the HA home location.

### Manual

Copy `custom_components/aircraft_window` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Receiver URL

Use the URL that returns your receiver's JSON list of aircraft. Common examples:

```text
http://piaware.local/skyaware/data/aircraft.json
http://receiver.local:8080/data/aircraft.json
```

The integration never needs FlightAware cloud credentials. It reads the local
receiver feed.

## No-position aircraft

Near conflict zones or over water, aircraft may sometimes appear without usable
coordinates. Aircraft Window does not fake coordinates. It treats a fresh,
strong, low-altitude local receiver hit as a lower-confidence `no_position_nearby`
candidate. That receiver-only evidence is exposed in attributes for debugging,
but it stays silent unless route-like context makes the interruption useful; the
announcement should not read out "strong local reception" chatter.

When the current receiver row has no coordinates, Aircraft Window also checks
the local SkyAware/dump1090 history snapshots for the same hex. If a recent
position is found there, the candidate is reclassified with
`position_source: skyaware_history` instead of staying no-position. This catches
short timing gaps where PiAware/MLAT or ADS-B position data arrived just before
the current row lost `lat`/`lon`.

## Automations

The included blueprint can announce every new `aircraft_window_candidate` event
through an Assist satellite. Copy or import
`blueprints/automation/aircraft_window_announce.yaml`, then use it like this:

```yaml
use_blueprint:
  path: Komzpa/aircraft_window_announce.yaml
  input:
    assist_satellite: assist_satellite.living_room
    mute_boolean: input_boolean.aircraft_announcements_muted
    minimum_confidence: 0.45
```

For curtains, keep your house policy in Home Assistant automations. A typical
pattern is:

```yaml
trigger:
  - platform: event
    event_type: aircraft_window_candidate
condition:
  - condition: state
    entity_id: input_boolean.aircraft_announcements_muted
    state: "off"
  - condition: state
    entity_id: input_boolean.sleep_mode
    state: "off"
  - condition: template
    value_template: "{{ trigger.event.data.phase != 'no_position_nearby' }}"
action:
  - service: cover.open_cover
    target:
      entity_id: cover.living_room_curtains
```

Use your own sleep, darkness, sun-glare, and privacy helpers as conditions. This
integration deliberately only detects the aircraft and emits the event; it does
not try to own your cover policy.

## Enrichment

When enabled, Aircraft Window uses short cached requests to public data sources:

- `api.adsbdb.com` for route, airline, model, and registration.
- `hexdb.io` as a fallback aircraft lookup.
- `airport-data.com` for built year by registration.

If those sources are slow or unavailable, the local aircraft candidate still
works; the announcement just contains less detail.

The hot candidate scan uses only cached enrichment data, so slow route or
aircraft lookups do not block the 2-second local receiver path. A background
coordinator warms the same cache under a separate budget and also refreshes the
Batumi airport board for scheduled curtain preopen state. Deadline misses are
not stored as real network errors.

The same enrichment is used for special-interest matching and service
classification. Military detection is best-effort and conservative: it uses
public operator prefixes, registered owner text, and known transport/surveillance
type codes instead of trying to infer mission intent. ADS-B emitter categories
are treated as size/type hints, not proof that a flight is passenger or cargo.

## Development

Run the lightweight checks:

```bash
python -m compileall custom_components tests
python -m ruff check .
python -m unittest discover
```
