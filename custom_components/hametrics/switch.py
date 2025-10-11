"""Switch entity to enable/disable hametrics pushing."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    handler = hass.data.get(DOMAIN, {}).get("handler")
    if not handler:
        return

    async_add_entities([HAMetricsEnableSwitch(handler)], update_before_add=True)


class HAMetricsEnableSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Enable metric push"
    # Ensure entity is enabled and identifiable consistently in tests
    _attr_entity_registry_enabled_default = True

    def __init__(self, handler) -> None:
        self._handler = handler
        self._attr_unique_id = f"{DOMAIN}_enable_switch"
        self._attr_is_on = handler.enabled
        # Force a deterministic entity_id used by tests
        self.entity_id = "switch.enable_metric_push"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "hametrics")}, name="Home Assistant Metrics"
        )

    async def async_turn_on(self, **kwargs) -> None:
        self._handler.set_enabled(True)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._handler.set_enabled(False)
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_update(self) -> None:
        self._attr_is_on = self._handler.enabled

    async def async_added_to_hass(self) -> None:
        @callback
        def _changed():
            self._attr_is_on = self._handler.enabled
            self.async_write_ha_state()

        self._cb = _changed
        self._handler.add_listener(self._cb)

        # entity_id already set in __init__

    async def async_will_remove_from_hass(self) -> None:
        if hasattr(self, "_cb"):
            self._handler.remove_listener(self._cb)
