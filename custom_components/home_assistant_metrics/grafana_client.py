"""Grafana Cloud client for Home Assistant Metrics."""
import base64
import json
import logging
import time
from typing import Any, Dict, List, Optional

import requests

_LOGGER = logging.getLogger(__name__)


class GrafanaCloudClient:
    """Client for pushing metrics to Grafana Cloud."""

    def __init__(self, grafana_url: str, username: str, password: str):
        """Initialize the Grafana Cloud client."""
        self.grafana_url = grafana_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)

    async def test_connection(self, hass) -> bool:
        """Test the connection to Grafana Cloud."""
        try:
            url = f"{self.grafana_url}/api/health"
            response = await hass.async_add_executor_job(
                self.session.get, url, {"timeout": 10}
            )
            return response.status_code == 200
        except Exception as exception:
            _LOGGER.error(f"Error testing Grafana connection: {exception}")
            return False

    async def push_metrics(self, hass, metrics_data: List[Dict[str, Any]]) -> bool:
        """Push metrics to Grafana Cloud."""
        try:
            if not metrics_data:
                return True

            # Convert to Prometheus remote write format (simplified JSON version)
            payload = self._convert_to_remote_write_format(metrics_data)
            
            # Use Prometheus remote write endpoint
            url = f"{self.grafana_url}/api/prom/push"
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "HomeAssistantMetrics/1.0",
            }

            response = await hass.async_add_executor_job(
                self.session.post,
                url,
                {
                    "json": payload,
                    "headers": headers,
                    "timeout": 30,
                }
            )

            if response.status_code in [200, 204]:
                _LOGGER.debug(f"Successfully pushed {len(metrics_data)} metrics to Grafana Cloud")
                return True
            else:
                _LOGGER.error(f"Failed to push metrics: {response.status_code} - {response.text}")
                return False

        except Exception as exception:
            _LOGGER.error(f"Error pushing metrics to Grafana Cloud: {exception}")
            return False

    def _convert_to_remote_write_format(self, metrics_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert metrics to Prometheus remote write format."""
        timeseries = []
        
        for metric in metrics_data:
            labels = []
            for label_name, label_value in metric.get("labels", {}).items():
                labels.append({
                    "name": label_name,
                    "value": str(label_value)
                })
            
            samples = []
            for sample in metric.get("samples", []):
                samples.append({
                    "value": float(sample["value"]),
                    "timestamp": int(sample["timestamp"])
                })
            
            if labels and samples:
                timeseries.append({
                    "labels": labels,
                    "samples": samples
                })
        
        return {"timeseries": timeseries}


class MetricsConverter:
    """Helper class for converting Home Assistant states to metrics."""

    @staticmethod
    def convert_states_to_metrics(instance_alias: str, states: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Home Assistant states to metrics format."""
        metrics = []
        current_time = int(time.time() * 1000)  # Milliseconds for Prometheus
        
        for state in states:
            entity_id = state.get("entity_id", "")
            state_value = state.get("state", "")
            attributes = state.get("attributes", {})
            
            # Skip unavailable states
            if state_value in ["unavailable", "unknown", "None", None]:
                continue
            
            # Create base labels
            base_labels = {
                "instance": instance_alias,
                "entity_id": entity_id,
                "domain": entity_id.split(".")[0] if "." in entity_id else "unknown",
                "friendly_name": attributes.get("friendly_name", entity_id),
            }
            
            # Convert main state
            numeric_value = MetricsConverter._get_numeric_value(state_value)
            if numeric_value is not None:
                metrics.append({
                    "labels": {**base_labels, "metric_type": "state"},
                    "samples": [{
                        "value": numeric_value,
                        "timestamp": current_time,
                    }]
                })
            
            # Convert numeric attributes
            for attr_name, attr_value in attributes.items():
                # Skip non-metric attributes
                if attr_name in [
                    "friendly_name", "icon", "entity_picture", "supported_features",
                    "device_class", "state_class", "unit_of_measurement"
                ]:
                    continue
                
                attr_numeric_value = MetricsConverter._get_numeric_value(attr_value)
                if attr_numeric_value is not None:
                    attr_labels = {**base_labels, "metric_type": "attribute", "attribute": attr_name}
                    metrics.append({
                        "labels": attr_labels,
                        "samples": [{
                            "value": attr_numeric_value,
                            "timestamp": current_time,
                        }]
                    })
        
        return metrics

    @staticmethod
    def _get_numeric_value(value: Any) -> Optional[float]:
        """Extract numeric value from state or attribute."""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Handle boolean strings
            value_lower = value.lower()
            if value_lower == "on":
                return 1.0
            elif value_lower == "off":
                return 0.0
            elif value_lower == "true":
                return 1.0
            elif value_lower == "false":
                return 0.0
            elif value_lower == "open":
                return 1.0
            elif value_lower == "closed":
                return 0.0
            elif value_lower == "home":
                return 1.0
            elif value_lower == "not_home":
                return 0.0
            
            # Try to parse as number
            try:
                return float(value)
            except ValueError:
                pass
        
        return None