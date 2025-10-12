"""Switch for enabling/disabling pushing metrics."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import HAMetricsCoordinator
from .const import COORDINATOR, DOMAIN


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the switch platform."""

    if discovery_info is None:
        return
    coordinator: HAMetricsCoordinator = hass.data[DOMAIN][COORDINATOR]

    entities = [
        HAMetricsSwitch(coordinator),
    ]
    async_add_entities(entities)


class HAMetricsSwitch(SwitchEntity):
    """Switch to enable/disable sending metrics."""

    _attr_has_entity_name = True
    _attr_name = ""
    _attr_unique_id = f"{DOMAIN}_switch"

    def __init__(self, coordinator: HAMetricsCoordinator):
        """Initialize."""
        self._coordinator = coordinator
        self._attr_is_on = True

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self._attr_is_on = True
        self._coordinator.set_telemetry_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self._attr_is_on = False
        self._coordinator.set_telemetry_enabled(False)
        self.async_write_ha_state()
