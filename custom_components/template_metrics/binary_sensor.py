"""Binary sensor for connection status."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
    """Set up the sensor platform."""

    if discovery_info is None:
        return

    coordinator: TemplateMetricsCoordinator = hass.data[DOMAIN][COORDINATOR]

    entities = [
        TemplateMetricsBinarySensor(coordinator),
    ]
    async_add_entities(entities)


class TemplateMetricsBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for connection status."""

    _attr_has_entity_name = True
    _attr_name = "Template Metrics Connection"
    _attr_unique_id = f"{DOMAIN}_connection"

    def __init__(self, coordinator: TemplateMetricsCoordinator):
        """Initialize."""
        super().__init__(coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return true if connection is successful."""
        return self.coordinator.enabled and self.coordinator.last_update_success

    @property
    def available(self) -> bool:
        """Binary sensor should remain available and indicate status via is_on.

        We intentionally do not inherit the CoordinatorEntity availability logic
        which would mark the entity as unavailable when the last update failed.
        Instead, a failed update maps to state off.
        """
        return True
