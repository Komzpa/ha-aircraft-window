"""Binary sensors for Aircraft Window."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AircraftWindowConfigEntry
from .coordinator import AircraftWindowCoordinator


async def async_setup_entry(
    hass,
    entry: AircraftWindowConfigEntry,
    async_add_entities,
) -> None:
    """Set up Aircraft Window binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            AircraftWindowActiveBinarySensor(coordinator),
            AircraftWindowUnusualBinarySensor(coordinator),
        ]
    )


class AircraftWindowBaseBinarySensor(
    CoordinatorEntity[AircraftWindowCoordinator],
    BinarySensorEntity,
):
    """Base class for Aircraft Window binary sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AircraftWindowCoordinator, suffix: str) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{suffix}"
        self._attr_device_info = {
            "identifiers": {(coordinator.entry.domain, coordinator.entry.entry_id)},
            "name": "Aircraft Window",
            "manufacturer": "Komzpa",
        }


class AircraftWindowActiveBinarySensor(AircraftWindowBaseBinarySensor):
    """Whether a candidate aircraft is currently active."""

    _attr_name = "Candidate active"
    _attr_icon = "mdi:airplane-alert"

    def __init__(self, coordinator: AircraftWindowCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "candidate_active")

    @property
    def is_on(self) -> bool:
        """Return true when a candidate is active."""
        return self.coordinator.data.active


class AircraftWindowUnusualBinarySensor(AircraftWindowBaseBinarySensor):
    """Whether the current aircraft is unusual or unmapped."""

    _attr_name = "Unusual aircraft"
    _attr_icon = "mdi:airplane-marker"

    def __init__(self, coordinator: AircraftWindowCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "unusual_aircraft")

    @property
    def is_on(self) -> bool:
        """Return true when the current candidate is unusual."""
        return bool(self.coordinator.data.unusual_aircraft)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the novelty reason."""
        return {"novelty_reason": self.coordinator.data.novelty_reason}
