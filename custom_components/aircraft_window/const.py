"""Constants for the Aircraft Window integration."""

DOMAIN = "aircraft_window"

CONF_DUMP1090_URL = "dump1090_url"
CONF_HOME_LATITUDE = "home_latitude"
CONF_HOME_LONGITUDE = "home_longitude"
CONF_MAX_POSITIONED_DISTANCE_KM = "max_positioned_distance_km"
CONF_MAX_NO_POSITION_SEEN_SECONDS = "max_no_position_seen_seconds"
CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"
CONF_ENABLE_ENRICHMENT = "enable_enrichment"
CONF_ENRICHMENT_TIMEOUT_SECONDS = "enrichment_timeout_seconds"

DEFAULT_DUMP1090_URL = "http://piaware.local/skyaware/data/aircraft.json"
DEFAULT_MAX_POSITIONED_DISTANCE_KM = 8.0
DEFAULT_MAX_NO_POSITION_SEEN_SECONDS = 4.0
DEFAULT_SCAN_INTERVAL_SECONDS = 2
DEFAULT_ENRICHMENT_TIMEOUT_SECONDS = 1.5

EVENT_CANDIDATE = "aircraft_window_candidate"
