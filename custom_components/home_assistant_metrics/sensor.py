"""Home Assistant Metrics sensor platform."""
import asyncio
import json
import logging
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

import requests
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    CONF_GRAFANA_URL,
    CONF_GRAFANA_USER,
    CONF_GRAFANA_PASSWORD,
    CONF_HA_INSTANCES,
    CONF_HA_URL,
    CONF_HA_TOKEN,
    CONF_HA_ALIAS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .grafana_client import GrafanaCloudClient, MetricsConverter

_LOGGER = logging.getLogger(__name__)


class HAMetricsCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Home Assistant metrics data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.config_entry = config_entry
        self.ha_instances = config_entry.data[CONF_HA_INSTANCES]
        
        # Initialize Grafana client
        self.grafana_client = GrafanaCloudClient(
            config_entry.data[CONF_GRAFANA_URL],
            config_entry.data[CONF_GRAFANA_USER],
            config_entry.data[CONF_GRAFANA_PASSWORD],
        )
        
        # Get update interval from config or options
        update_interval_seconds = config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )
        update_interval = timedelta(seconds=update_interval_seconds)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        try:
            metrics_data = {}
            all_metrics = []
            
            # Collect metrics from all configured Home Assistant instances
            for instance in self.ha_instances:
                instance_alias = instance[CONF_HA_ALIAS]
                instance_url = instance[CONF_HA_URL]
                instance_token = instance[CONF_HA_TOKEN]
                
                _LOGGER.debug(f"Collecting metrics from {instance_alias}")
                
                # Get all states from the Home Assistant instance
                states = await self._fetch_ha_states(instance_url, instance_token)
                
                if states:
                    metrics_data[instance_alias] = {
                        "entity_count": len(states),
                        "last_update": time.time(),
                    }
                    
                    # Convert states to metrics
                    instance_metrics = MetricsConverter.convert_states_to_metrics(
                        instance_alias, states
                    )
                    all_metrics.extend(instance_metrics)
                    
                    _LOGGER.debug(f"Converted {len(instance_metrics)} metrics from {instance_alias}")
                else:
                    _LOGGER.warning(f"No states received from {instance_alias}")
            
            # Push all metrics to Grafana Cloud
            if all_metrics:
                success = await self.grafana_client.push_metrics(self.hass, all_metrics)
                if success:
                    _LOGGER.debug(f"Successfully pushed {len(all_metrics)} metrics to Grafana Cloud")
                else:
                    _LOGGER.error("Failed to push metrics to Grafana Cloud")
            
            return metrics_data
            
        except Exception as exception:
            _LOGGER.error(f"Error updating metrics data: {exception}")
            raise UpdateFailed(exception) from exception

    async def _fetch_ha_states(self, ha_url: str, ha_token: str) -> List[Dict[str, Any]]:
        """Fetch all states from a Home Assistant instance."""
        try:
            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            }
            
            url = f"{ha_url.rstrip('/')}/api/states"
            
            response = await self.hass.async_add_executor_job(
                requests.get, url, {"headers": headers, "timeout": 30}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                _LOGGER.error(f"Failed to fetch states: {response.status_code}")
                return []
                
        except Exception as exception:
            _LOGGER.error(f"Error fetching HA states: {exception}")
            return []


class HAMetricsSensor(CoordinatorEntity, SensorEntity):
    """Home Assistant Metrics sensor."""

    def __init__(self, coordinator: HAMetricsCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Home Assistant Metrics"
        self._attr_unique_id = f"{DOMAIN}_main"
        self._attr_icon = "mdi:chart-line"

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return "No data"
        
        total_entities = sum(data.get("entity_count", 0) for data in self.coordinator.data.values())
        return f"{total_entities} entities monitored"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        attributes = {
            "instances": list(self.coordinator.data.keys()),
            "instance_count": len(self.coordinator.data),
        }
        
        # Add per-instance information
        total_entities = 0
        for instance, data in self.coordinator.data.items():
            entity_count = data.get("entity_count", 0)
            last_update = data.get("last_update")
            
            attributes[f"{instance}_entities"] = entity_count
            if last_update:
                attributes[f"{instance}_last_update"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(last_update)
                )
            total_entities += entity_count
        
        attributes["total_entities"] = total_entities
        return attributes


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Home Assistant Metrics sensor."""
    coordinator = HAMetricsCoordinator(hass, config_entry)
    
    # Fetch initial data so we have data when entities are added
    await coordinator.async_config_entry_first_refresh()
    
    async_add_entities([HAMetricsSensor(coordinator)])