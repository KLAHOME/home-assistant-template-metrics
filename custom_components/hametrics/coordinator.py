"""DataUpdateCoordinator for Grafana Metrics."""

import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, METER, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class HAMetricsCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to push metrics data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: Any,
    ) -> None:
        """Initialize."""
        self._config = config
        self.meter = hass.data[DOMAIN][METER]
        self.enabled = True

        update_interval = timedelta(seconds=config.get(UPDATE_INTERVAL, 60))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            always_update=False,
        )

    def set_enabled(self, enabled: bool) -> None:
        """Set the enabled state."""
        self.enabled = enabled
        _LOGGER.debug(f"Telemetry set to {'enabled' if enabled else 'disabled'}")
        self.async_set_updated_data(
            {"success": True, "data": {}, "enabled": self.enabled}
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Push metrics to Grafana Cloud if telemetry is enabled."""
        if not self.enabled:
            _LOGGER.debug("Telemetry disabled, skipping metrics push")
            return {"success": True, "data": {}, "enabled": False}

        try:
            # Templates auswerten
            metrics_data = {}
            for metric in self._config.metrics:
                template = Template(metric["template"], self.hass)
                value = template.async_render()
                if value is None:
                    _LOGGER.warning(f"Template for {metric['name']} returned None")
                    continue

                try:
                    float_value = float(value)
                except ValueError:
                    _LOGGER.warning(
                        f"Invalid numeric value for {metric['name']}: {value}"
                    )
                    continue

                # Metrik mit OpenTelemetry erstellen
                gauge = self.meter.create_gauge(
                    metric["name"], description=f"HA {metric['name']}"
                )
                gauge.set(float_value)
                metrics_data[metric["name"]] = float_value
                _LOGGER.debug(f"Pushed metric {metric['name']}: {float_value}")

            return {"success": True, "data": metrics_data, "enabled": True}

        except Exception as err:
            _LOGGER.error(f"Error pushing metrics: {err}")
            raise UpdateFailed(f"Failed to push metrics: {err}")
