"""Aircraft Window integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import AircraftWindowRuntimeData

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type AircraftWindowConfigEntry = ConfigEntry[AircraftWindowRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AircraftWindowConfigEntry,
) -> bool:
    """Set up Aircraft Window from a config entry."""
    runtime = AircraftWindowRuntimeData(hass, entry)
    entry.runtime_data = runtime
    await runtime.candidate.async_config_entry_first_refresh()
    await runtime.enrichment_prefetch.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: AircraftWindowConfigEntry,
) -> bool:
    """Unload an Aircraft Window config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
