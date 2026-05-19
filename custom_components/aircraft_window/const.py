"""Constants for the Aircraft Window integration."""

DOMAIN = "aircraft_window"

CONF_DUMP1090_URL = "dump1090_url"
CONF_HOME_LATITUDE = "home_latitude"
CONF_HOME_LONGITUDE = "home_longitude"
CONF_MAX_POSITIONED_DISTANCE_KM = "max_positioned_distance_km"
CONF_MAX_APPROACH_DISTANCE_KM = "max_approach_distance_km"
CONF_MAX_APPROACH_ALTITUDE_FT = "max_approach_altitude_ft"
CONF_MAX_NO_POSITION_SEEN_SECONDS = "max_no_position_seen_seconds"
CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"
CONF_BACKGROUND_INTERVAL_SECONDS = "background_interval_seconds"
CONF_ENABLE_ENRICHMENT = "enable_enrichment"
CONF_ENRICHMENT_TIMEOUT_SECONDS = "enrichment_timeout_seconds"
CONF_PREFETCH_LIMIT = "prefetch_limit"
CONF_PREFETCH_BUDGET_SECONDS = "prefetch_budget_seconds"

DEFAULT_DUMP1090_URL = "http://piaware.local/skyaware/data/aircraft.json"
DEFAULT_MAX_POSITIONED_DISTANCE_KM = 8.0
DEFAULT_MAX_APPROACH_DISTANCE_KM = 60.0
DEFAULT_MAX_APPROACH_ALTITUDE_FT = 10000.0
DEFAULT_MAX_NO_POSITION_SEEN_SECONDS = 4.0
DEFAULT_SCAN_INTERVAL_SECONDS = 2
DEFAULT_BACKGROUND_INTERVAL_SECONDS = 60
DEFAULT_ENRICHMENT_TIMEOUT_SECONDS = 1.5
DEFAULT_PREFETCH_LIMIT = 12
DEFAULT_PREFETCH_BUDGET_SECONDS = 12.0
SCHEDULED_PREOPEN_BEFORE_SECONDS = 300
SCHEDULED_PREOPEN_AFTER_SECONDS = 180

EVENT_CANDIDATE = "aircraft_window_candidate"

ENTITY_ID_CANDIDATE = "sensor.aircraft_window_candidate"
ENTITY_ID_ENRICHMENT_PREFETCH = "sensor.aircraft_window_enrichment_prefetch"
ENTITY_ID_SCHEDULE_PREOPEN = "sensor.aircraft_window_schedule_preopen"
ENTITY_ID_VISIBLE = "binary_sensor.aircraft_visible_outside_window"
ENTITY_ID_CURTAIN_PREOPEN = "binary_sensor.aircraft_window_curtain_preopen_needed"
ENTITY_ID_SCHEDULED_PREOPEN = "binary_sensor.aircraft_scheduled_departure_curtain_preopen_needed"
