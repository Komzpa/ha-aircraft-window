"""Binary sensors for Aircraft Window."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AircraftWindowConfigEntry
from .const import (
    ENTITY_ID_CURTAIN_PREOPEN,
    ENTITY_ID_SCHEDULED_PREOPEN,
    ENTITY_ID_VISIBLE,
)
from .coordinator import AircraftWindowCoordinator, EnrichmentPrefetchCoordinator

BASE_URGENT_CURTAIN_PHASES = {
    "positioned_approach",
    "positioned_landing",
    "positioned_takeoff",
    "positioned_low_nearby",
    "military_visible",
    "special_interest",
}


def _is_urgent_curtain_phase(coordinator: AircraftWindowCoordinator, phase: str) -> bool:
    """Return true when a phase should open curtains for visible aircraft."""
    if phase in BASE_URGENT_CURTAIN_PHASES:
        return True
    return coordinator.runtime_settings.watch_policy.airport_phase(phase) is not None


async def async_setup_entry(
    hass,
    entry: AircraftWindowConfigEntry,
    async_add_entities,
) -> None:
    """Set up Aircraft Window binary sensors."""
    runtime = entry.runtime_data
    async_add_entities(
        [
            AircraftWindowVisibleOutsideBinarySensor(runtime.candidate),
            AircraftWindowCurtainPreopenBinarySensor(runtime.candidate),
            AircraftWindowScheduledDeparturePreopenBinarySensor(
                runtime.enrichment_prefetch
            ),
            AircraftWindowActiveBinarySensor(runtime.candidate),
            AircraftWindowUnusualBinarySensor(runtime.candidate),
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


class AircraftWindowVisibleOutsideBinarySensor(AircraftWindowBaseBinarySensor):
    """Whether the candidate aircraft is worth looking for outside."""

    _attr_name = "Visible outside window"
    _attr_icon = "mdi:window-open-variant"

    def __init__(self, coordinator: AircraftWindowCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "visible_outside_window")
        self._attr_unique_id = "aircraft_visible_outside_window"
        self._attr_entity_id = ENTITY_ID_VISIBLE

    @property
    def is_on(self) -> bool:
        """Return true when the aircraft should be visible from the window."""
        return bool(self.coordinator.data.window_visible)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the visible-window reason."""
        return {"window_view_reason": self.coordinator.data.window_view_reason}


class AircraftWindowCurtainPreopenBinarySensor(AircraftWindowBaseBinarySensor):
    """Whether curtains should preopen for the current aircraft candidate."""

    _attr_name = "Curtain preopen needed"
    _attr_icon = "mdi:curtains"

    def __init__(self, coordinator: AircraftWindowCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "curtain_preopen_needed")
        self._attr_unique_id = "aircraft_window_curtain_preopen_needed"
        self._attr_entity_id = ENTITY_ID_CURTAIN_PREOPEN

    @property
    def is_on(self) -> bool:
        """Return true when the current candidate should preopen curtains."""
        candidate = self.coordinator.data
        altitude = candidate.altitude_ft
        altitude_ok = altitude is None or altitude <= 10000
        return bool(
            (candidate.window_visible or candidate.window_runway_staging)
            and _is_urgent_curtain_phase(self.coordinator, candidate.phase)
            and altitude_ok
        )

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return the preopen reason."""
        candidate = self.coordinator.data
        return {
            "phase": candidate.phase,
            "altitude_ft": candidate.altitude_ft,
            "window_view_reason": candidate.window_view_reason,
        }


class AircraftWindowScheduledDeparturePreopenBinarySensor(
    CoordinatorEntity[EnrichmentPrefetchCoordinator],
    BinarySensorEntity,
):
    """Whether a scheduled configured-airport departure needs curtain preopen."""

    _attr_has_entity_name = True
    _attr_name = "Scheduled departure curtain preopen needed"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: EnrichmentPrefetchCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = "aircraft_scheduled_departure_curtain_preopen_needed"
        self._attr_entity_id = ENTITY_ID_SCHEDULED_PREOPEN
        self._attr_device_info = {
            "identifiers": {(coordinator.entry.domain, coordinator.entry.entry_id)},
            "name": "Aircraft Window",
            "manufacturer": "Komzpa",
        }

    @property
    def _schedule_data(self) -> dict[str, object]:
        """Return the nested schedule preopen payload."""
        data = self.coordinator.data or {}
        nested = data.get("schedule_preopen")
        return nested if isinstance(nested, dict) else {}

    @property
    def is_on(self) -> bool:
        """Return true when a scheduled departure is inside the preopen window."""
        return self._schedule_data.get("state") == "on"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return schedule attributes."""
        return dict(self._schedule_data)


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
