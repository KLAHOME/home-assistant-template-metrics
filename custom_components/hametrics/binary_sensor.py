"""Binary sensor to reflect hametrics connectivity after initial push."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):
    handler = hass.data.get(DOMAIN, {}).get("handler")
    if not handler:
        return

    async_add_entities(
        [HAMetricsConnectedBinarySensor(handler)], update_before_add=True
    )


class HAMetricsConnectedBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Connected"
    _attr_entity_registry_enabled_default = True

    def __init__(self, handler) -> None:
        self._handler = handler
        self._attr_unique_id = f"{DOMAIN}_connected"
        self._attr_is_on = handler.connected
        # Deterministic entity_id for tests
        self.entity_id = "binary_sensor.connected"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, "hametrics")}, name="Home Assistant Metrics"
        )

    @property
    def is_on(self) -> bool:
        return self._handler.connected

    async def async_update(self) -> None:
        self._attr_is_on = self._handler.connected

    async def async_added_to_hass(self) -> None:
        @callback
        def _changed():
            self._attr_is_on = self._handler.connected
            self.async_write_ha_state()

        self._cb = _changed
        self._handler.add_listener(self._cb)

        # entity_id already set in __init__

    async def async_will_remove_from_hass(self) -> None:
        if hasattr(self, "_cb"):
            self._handler.remove_listener(self._cb)
