"""Sensor platform for Aircraft Window."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AircraftWindowConfigEntry
from .const import (
    ENTITY_ID_CANDIDATE,
    ENTITY_ID_ENRICHMENT_PREFETCH,
    ENTITY_ID_SCHEDULE_PREOPEN,
)
from .coordinator import AircraftWindowCoordinator, EnrichmentPrefetchCoordinator


async def async_setup_entry(
    hass,
    entry: AircraftWindowConfigEntry,
    async_add_entities,
) -> None:
    """Set up Aircraft Window sensors."""
    runtime = entry.runtime_data
    async_add_entities(
        [
            AircraftWindowCandidateSensor(runtime.candidate),
            AircraftWindowSchedulePreopenSensor(runtime.enrichment_prefetch),
            AircraftWindowPrefetchSensor(runtime.enrichment_prefetch),
        ]
    )


class AircraftWindowCandidateSensor(CoordinatorEntity[AircraftWindowCoordinator], SensorEntity):
    """Current aircraft candidate sensor."""

    _attr_has_entity_name = True
    _attr_name = "Candidate"
    _attr_icon = "mdi:airplane-clock"

    def __init__(self, coordinator: AircraftWindowCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = "aircraft_window_candidate"
        self._attr_entity_id = ENTITY_ID_CANDIDATE
        self._attr_device_info = {
            "identifiers": {(coordinator.entry.domain, coordinator.entry.entry_id)},
            "name": "Aircraft Window",
            "manufacturer": "Komzpa",
        }

    @property
    def native_value(self) -> str:
        """Return event key or idle."""
        return self.coordinator.data.state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aircraft attributes."""
        return self.coordinator.data.as_dict()


class AircraftWindowPrefetchSensor(
    CoordinatorEntity[EnrichmentPrefetchCoordinator],
    SensorEntity,
):
    """Background enrichment prefetch status."""

    _attr_has_entity_name = True
    _attr_name = "Enrichment prefetch"
    _attr_icon = "mdi:database-refresh"

    def __init__(self, coordinator: EnrichmentPrefetchCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = "aircraft_window_enrichment_prefetch"
        self._attr_entity_id = ENTITY_ID_ENRICHMENT_PREFETCH
        self._attr_device_info = {
            "identifiers": {(coordinator.entry.domain, coordinator.entry.entry_id)},
            "name": "Aircraft Window",
            "manufacturer": "Komzpa",
        }

    @property
    def _prefetch_data(self) -> dict[str, Any]:
        """Return the nested prefetch status payload."""
        data = self.coordinator.data or {}
        nested = data.get("enrichment_prefetch")
        return nested if isinstance(nested, dict) else data

    @property
    def native_value(self) -> str:
        """Return prefetch status."""
        return str(self._prefetch_data.get("state") or "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return prefetch attributes."""
        return dict(self._prefetch_data)


class AircraftWindowSchedulePreopenSensor(
    CoordinatorEntity[EnrichmentPrefetchCoordinator],
    SensorEntity,
):
    """Scheduled configured-airport departure curtain preopen sensor."""

    _attr_has_entity_name = True
    _attr_name = "Schedule preopen"
    _attr_icon = "mdi:airplane-clock"

    def __init__(self, coordinator: EnrichmentPrefetchCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = "aircraft_window_schedule_preopen"
        self._attr_entity_id = ENTITY_ID_SCHEDULE_PREOPEN
        self._attr_device_info = {
            "identifiers": {(coordinator.entry.domain, coordinator.entry.entry_id)},
            "name": "Aircraft Window",
            "manufacturer": "Komzpa",
        }

    @property
    def _schedule_data(self) -> dict[str, Any]:
        """Return the nested schedule preopen payload."""
        data = self.coordinator.data or {}
        nested = data.get("schedule_preopen")
        return nested if isinstance(nested, dict) else {}

    @property
    def native_value(self) -> str:
        """Return schedule preopen status."""
        return str(self._schedule_data.get("state") or "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return schedule attributes."""
        return dict(self._schedule_data)
