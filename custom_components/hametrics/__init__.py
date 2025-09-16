"""Grafana Cloud Metrics integration."""

import asyncio
import logging
from typing import Any, Dict, List

import aiohttp
import async_timeout
import voluptuous as vol
import snappy

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .remote_pb2 import WriteRequest
from .const import (
    DOMAIN,
    CONF_GRAFANA_URL,
    CONF_GRAFANA_USER,
    CONF_GRAFANA_TOKEN,
    CONF_PUSH_INTERVAL,
    CONF_INSTANCE_NAME,
    CONF_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_GRAFANA_URL): cv.string,
                vol.Required(CONF_GRAFANA_USER): cv.string,
                vol.Required(CONF_GRAFANA_TOKEN): cv.string,
                vol.Optional(CONF_ENTITIES, default=[]): vol.All(cv.ensure_list),
                vol.Optional(CONF_PUSH_INTERVAL, default=60): cv.positive_int,
                vol.Optional(CONF_INSTANCE_NAME): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


class HAMetrics:
    """HA Metrics handler."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize the HA Metrics handler."""
        self.hass = hass
        self.config = config
        self.session = None
        self._push_task = None
        self._metrics_buffer = []
        self._last_push = None

        # Grafana Cloud Prometheus Push Gateway URL
        self.push_url = f"{config[CONF_GRAFANA_URL]}/api/prom/push"

        # Authentication
        self.auth = aiohttp.BasicAuth(
            config[CONF_GRAFANA_USER], config[CONF_GRAFANA_TOKEN]
        )

        # Instance identifier
        self.instance_name = config.get(
            CONF_INSTANCE_NAME, hass.config.location_name.lower().replace(" ", "_")
        )

        self.entities = config.get(CONF_ENTITIES, [])
        self.push_interval = config.get(CONF_PUSH_INTERVAL, 60)

    async def async_setup(self):
        """Set up the Grafana metrics handler."""
        self.session = aiohttp.ClientSession()

        # Track state changes for specified entities
        if self.entities:
            async_track_state_change_event(
                self.hass, self.entities, self._state_change_listener
            )
        else:
            # Track all entities if none specified
            async_track_state_change_event(self.hass, None, self._state_change_listener)

        # Start periodic push task
        self._push_task = self.hass.async_create_task(self._periodic_push())

        _LOGGER.info("Grafana Cloud Metrics integration started")

    async def async_unload(self):
        """Unload the integration."""
        if self._push_task:
            self._push_task.cancel()

        if self.session:
            await self.session.close()

    @callback
    def _state_change_listener(self, event):
        try:
            metrics = self._create_metric(
                event.data["entity_id"], event.data["new_state"]
            )
            self._metrics_buffer.extend(metrics)
        except Exception as exc:
            _LOGGER.error("Error processing state change: %s", exc)

    def _create_metric(self, entity_id: str, state) -> List[Dict[str, Any]]:
        """Create metrics from entity state."""
        metrics = []

        if state is None:
            return []

        try:
            # Base labels for all metrics from this entity
            base_labels = {
                "instance": self.instance_name,
                "entity_id": entity_id,
                "domain": entity_id.split(".")[0],
                "friendly_name": state.attributes.get("friendly_name", entity_id),
            }

            timestamp = int(dt_util.utcnow().timestamp() * 1000)

            # Main state metric
            main_metric = self._create_state_metric(
                entity_id, state, base_labels.copy(), timestamp
            )
            if main_metric:
                metrics.append(main_metric)

            # Process attributes
            attribute_metrics = self._create_attribute_metrics(
                entity_id, state, base_labels.copy(), timestamp
            )
            metrics.extend(attribute_metrics)

            return metrics

        except Exception as e:
            _LOGGER.error(f"Error creating metrics for {entity_id}: {e}")
            return []

    def _create_state_metric(
        self, entity_id: str, state, labels: Dict[str, str], timestamp: int
    ) -> Dict[str, Any]:
        """Create the main state metric."""
        try:
            # Try to convert state to numeric value
            if state.state in ["on", "off"]:
                value = 1 if state.state == "on" else 0
            elif state.state in ["unavailable", "unknown"]:
                return None  # Skip unavailable states
            else:
                try:
                    value = float(state.state)
                except (ValueError, TypeError):
                    # For non-numeric states, create a state metric
                    labels["state"] = state.state
                    value = 1

            return {
                "name": f"homeassistant_{entity_id.split('.')[0]}_state",
                "value": value,
                "timestamp": timestamp,
                "labels": labels,
            }
        except Exception:
            return None

    def _create_attribute_metrics(
        self, entity_id: str, state, base_labels: Dict[str, str], timestamp: int
    ) -> List[Dict[str, Any]]:
        """Create metrics from entity attributes."""
        metrics = []
        domain = entity_id.split(".")[0]

        for attr_key, attr_value in state.attributes.items():
            # Skip certain system attributes
            if attr_key in [
                "friendly_name",
                "icon",
                "device_class",
                "unit_of_measurement",
            ]:
                continue

            try:
                # Handle simple attributes
                if isinstance(attr_value, (str, int, float, bool)):
                    labels = base_labels.copy()
                    clean_key = self._clean_key(attr_key)

                    if isinstance(attr_value, bool):
                        value = 1 if attr_value else 0
                    elif isinstance(attr_value, (int, float)):
                        value = float(attr_value)
                    else:
                        # String values become labels
                        labels["value"] = str(attr_value)
                        value = 1

                    metrics.append(
                        {
                            "name": f"homeassistant_{domain}_attr_{clean_key}",
                            "value": value,
                            "timestamp": timestamp,
                            "labels": labels,
                        }
                    )

                # Handle list attributes (like quantities)
                elif isinstance(attr_value, list):
                    list_metrics = self._process_list_attribute(
                        entity_id, attr_key, attr_value, base_labels.copy(), timestamp
                    )
                    metrics.extend(list_metrics)

                # Handle dict attributes
                elif isinstance(attr_value, dict):
                    dict_metrics = self._process_dict_attribute(
                        entity_id, attr_key, attr_value, base_labels.copy(), timestamp
                    )
                    metrics.extend(dict_metrics)

            except Exception as e:
                _LOGGER.debug(
                    f"Could not process attribute {attr_key} for {entity_id}: {e}"
                )
                continue

        return metrics

    def _process_list_attribute(
        self,
        entity_id: str,
        attr_key: str,
        attr_list: list,
        base_labels: Dict[str, str],
        timestamp: int,
    ) -> List[Dict[str, Any]]:
        """Process list attributes like quantities."""
        metrics = []
        domain = entity_id.split(".")[0]
        clean_attr_key = self._clean_key(attr_key)

        for i, item in enumerate(attr_list):
            if isinstance(item, dict):
                # Handle list of objects (like battery quantities)
                for sub_key, sub_value in item.items():
                    if isinstance(sub_value, (int, float)):
                        labels = base_labels.copy()
                        labels["list_index"] = str(i)

                        # Add other keys from the dict as labels
                        for k, v in item.items():
                            if k != sub_key and isinstance(v, (str, int, float, bool)):
                                labels[self._clean_key(k)] = str(v)

                        metrics.append(
                            {
                                "name": f"homeassistant_{domain}_{clean_attr_key}_{self._clean_key(sub_key)}",
                                "value": float(sub_value),
                                "timestamp": timestamp,
                                "labels": labels,
                            }
                        )

            elif isinstance(item, (int, float)):
                # Handle list of numbers
                labels = base_labels.copy()
                labels["list_index"] = str(i)

                metrics.append(
                    {
                        "name": f"homeassistant_{domain}_{clean_attr_key}_value",
                        "value": float(item),
                        "timestamp": timestamp,
                        "labels": labels,
                    }
                )

        return metrics

    def _process_dict_attribute(
        self,
        entity_id: str,
        attr_key: str,
        attr_dict: dict,
        base_labels: Dict[str, str],
        timestamp: int,
    ) -> List[Dict[str, Any]]:
        """Process dictionary attributes."""
        metrics = []
        domain = entity_id.split(".")[0]
        clean_attr_key = self._clean_key(attr_key)

        for sub_key, sub_value in attr_dict.items():
            if isinstance(sub_value, (int, float)):
                labels = base_labels.copy()
                labels["dict_key"] = str(sub_key)

                metrics.append(
                    {
                        "name": f"homeassistant_{domain}_{clean_attr_key}_{self._clean_key(sub_key)}",
                        "value": float(sub_value),
                        "timestamp": timestamp,
                        "labels": labels,
                    }
                )

        return metrics

    def _clean_key(self, key: str) -> str:
        """Clean a key for use in metric names."""
        return key.replace(" ", "_").replace("-", "_").replace(".", "_").lower()

    def _format_prometheus_metrics(self, metrics: List[Dict[str, Any]]) -> bytes:
        """Format metrics in Prometheus Remote Write protobuf format."""
        write_request = WriteRequest()

        # Group metrics by metric name and labels
        metric_groups = {}

        for metric in metrics:
            # Create a key from metric name and sorted labels
            labels_items = sorted(metric["labels"].items())
            key = (metric["name"], tuple(labels_items))

            if key not in metric_groups:
                metric_groups[key] = []

            metric_groups[key].append(
                {"value": metric["value"], "timestamp": metric["timestamp"]}
            )

        # Create TimeSeries for each metric group
        for (metric_name, labels_items), samples in metric_groups.items():
            time_series = write_request.add_timeseries()

            # Add __name__ label
            time_series.add_label("__name__", metric_name)

            # Add other labels
            for label_name, label_value in labels_items:
                time_series.add_label(label_name, str(label_value))

            # Add samples
            for sample_data in samples:
                time_series.add_sample(
                    float(sample_data["value"]), int(sample_data["timestamp"])
                )

        # Serialize to protobuf
        return write_request.SerializeToString()

    async def _push_metrics(self, metrics: List[Dict[str, Any]]):
        """Push metrics to Grafana Cloud using protobuf format."""
        if not metrics:
            return

        try:
            # Convert to protobuf format
            protobuf_data = self._format_prometheus_metrics(metrics)

            # Compress using Snappy
            compressed_data = snappy.compress(protobuf_data)

            headers = {
                "Content-Type": "application/x-protobuf",
                "Content-Encoding": "snappy",
                "X-Prometheus-Remote-Write-Version": "0.1.0",
                "User-Agent": "HomeAssistant-Grafana-Metrics/1.0",
            }

            async with async_timeout.timeout(30):
                async with self.session.post(
                    self.push_url, data=compressed_data, headers=headers, auth=self.auth
                ) as response:
                    if response.status == 200:
                        _LOGGER.debug(
                            f"Successfully pushed {len(metrics)} metrics to Grafana"
                        )
                        self._last_push = dt_util.utcnow()
                    else:
                        error_text = await response.text()
                        _LOGGER.error(
                            f"Failed to push metrics: {response.status} - {error_text}"
                        )

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout pushing metrics to Grafana Cloud")
        except Exception as e:
            _LOGGER.error(f"Error pushing metrics to Grafana Cloud: {e}")

    async def _periodic_push(self):
        """Periodic task to push metrics."""
        while True:
            try:
                await asyncio.sleep(self.push_interval)

                if self._metrics_buffer:
                    # Copy buffer and clear it
                    metrics_to_send = self._metrics_buffer.copy()
                    self._metrics_buffer.clear()

                    await self._push_metrics(metrics_to_send)

            except asyncio.CancelledError:
                _LOGGER.error("Periodic push cancelled")
                raise  # <-- Make sure to re-raise!
            except Exception as exc:
                _LOGGER.error("Error in periodic push: %s", exc)


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Grafana Metrics integration."""
    if DOMAIN not in config:
        return True

    grafana_config = config[DOMAIN]

    # Initialize the metrics handler
    metrics_handler = HAMetrics(hass, grafana_config)

    # Store in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["handler"] = metrics_handler

    # Set up the handler
    await metrics_handler.async_setup()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration."""
    if DOMAIN in hass.data and "handler" in hass.data[DOMAIN]:
        handler = hass.data[DOMAIN]["handler"]
        await handler.async_unload()

    hass.data[DOMAIN].clear()
    return True
