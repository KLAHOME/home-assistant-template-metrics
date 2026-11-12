"""Switch for enabling/disabling pushing metrics."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TemplateMetricsCoordinator
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
    coordinator: TemplateMetricsCoordinator = hass.data[DOMAIN][COORDINATOR]

    entities = [
        TemplateMetricsSwitch(coordinator),
    ]
    async_add_entities(entities)


class TemplateMetricsSwitch(CoordinatorEntity, SwitchEntity, RestoreEntity):
    """Switch to enable/disable sending metrics.

    A saved off state survives restarts; without a saved state it starts on.
    """

    _attr_has_entity_name = True
    _attr_name = "Template Metrics Switch"
    _attr_unique_id = f"{DOMAIN}_switch"

    def __init__(self, coordinator: TemplateMetricsCoordinator):
        """Initialize."""
        super().__init__(coordinator)

    async def async_added_to_hass(self) -> None:
        """Restore a saved off state before anything is exported."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state == STATE_OFF:
            self.coordinator.set_enabled(False, send_opt_out=False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self.coordinator.set_enabled(True)
        # CoordinatorEntity will call listeners; ensure we write our state
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self.coordinator.set_enabled(False)
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return if metrics sending is enabled."""
        return self.coordinator.enabled

    @property
    def available(self) -> bool:
        """Switch should remain available; off reflects disabled or failures."""
        return True
