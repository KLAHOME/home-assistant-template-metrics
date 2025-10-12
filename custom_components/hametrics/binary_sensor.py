"""Binary sensor for connection status."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the sensor platform."""

    if discovery_info is None:
        return

    coordinator: HAMetricsCoordinator = hass.data[DOMAIN][COORDINATOR]

    entities = [
        HAMetricsBinarySensor(coordinator),
    ]
    async_add_entities(entities)


class HAMetricsBinarySensor(BinarySensorEntity):
    """Binary sensor for Grafana connection status."""

    _attr_has_entity_name = True
    _attr_name = "Connection Status"
    _attr_unique_id = f"{DOMAIN}_connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: HAMetricsCoordinator):
        """Initialize."""
        self._coordinator = coordinator

    @property
    def is_on(self) -> bool | None:
        """Return true if connection is successful."""
        return self._coordinator.last_update_success

    async def async_update(self) -> None:
        """Update the entity."""
        await self._coordinator.async_request_refresh()
