"""Sensor platform for Aircraft Window."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AircraftWindowConfigEntry
from .coordinator import AircraftWindowCoordinator


async def async_setup_entry(
    hass,
    entry: AircraftWindowConfigEntry,
    async_add_entities,
) -> None:
    """Set up Aircraft Window sensors."""
    coordinator = entry.runtime_data
    async_add_entities([AircraftWindowCandidateSensor(coordinator)])


class AircraftWindowCandidateSensor(CoordinatorEntity[AircraftWindowCoordinator], SensorEntity):
    """Current aircraft candidate sensor."""

    _attr_has_entity_name = True
    _attr_name = "Candidate"
    _attr_icon = "mdi:airplane-clock"

    def __init__(self, coordinator: AircraftWindowCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_candidate"
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

