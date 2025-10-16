"""DataUpdateCoordinator for Grafana Metrics."""

import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import TemplateError
from opentelemetry.sdk.metrics import Meter

from .const import DOMAIN, METER, UPDATE_INTERVAL, INSTANCE_LABEL, METRIC_LABEL_INSTANCE

_LOGGER = logging.getLogger(__name__)


class TemplateMetricsCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to push metrics data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: Any,
    ) -> None:
        """Initialize."""
        self._config = config
        self.meter: Meter = hass.data[DOMAIN][METER]
        self.enabled = True
        self.last_update_success = True
        self._attributes: dict[str, Any] = {}

        instance_label = config.get(INSTANCE_LABEL)
        if instance_label:
            self._attributes[METRIC_LABEL_INSTANCE] = instance_label

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
        _LOGGER.debug(f"Metrics set to {'' if enabled else 'not'} enabled")
        # Notify listeners immediately so entities re-evaluate their state
        self.async_set_updated_data(
            {
                "success": True,
                "data": {},
                "enabled": self.enabled,
            }
        )

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        # Try to login to push endpoint to verify credentials.

    async def _async_update_data(self) -> Dict[str, Any]:
        """Push metrics to endpoint."""
        if not self.enabled:
            _LOGGER.debug("Push disabled, skipping metrics push")
            return {"success": True, "data": {}, "enabled": False}

        try:
            metrics_data = {}
            for metric in self._config["metrics"]:
                try:
                    template = Template(metric["template"], self.hass)
                    value = template.async_render()
                    if value is None:
                        _LOGGER.error(f"Template for {metric['name']} returned None")
                        raise UpdateFailed(f"Template {metric['name']} returned None")

                    try:
                        float_value = float(value)
                    except ValueError:
                        _LOGGER.error(
                            f"Invalid numeric value for {metric['name']}: {value}"
                        )
                        raise UpdateFailed(
                            f"Invalid numeric value for {metric['name']}: {value}"
                        )

                    gauge = self.meter.create_gauge(
                        metric["name"], description=f"HA {metric['name']}"
                    )
                    set_kwargs: Dict[str, Any] = {}
                    if self._attributes:
                        set_kwargs["attributes"] = self._attributes
                    gauge.set(float_value, **set_kwargs)
                    metrics_data[metric["name"]] = float_value
                    _LOGGER.debug(f"Updated metric {metric['name']}: {float_value}")
                except TemplateError as err:
                    _LOGGER.error(f"Template {metric} is invalid: {err}")
                    raise UpdateFailed(f"Template {metric} is invalid: {err}")

            self.last_update_success = True
            return {"success": True, "data": metrics_data, "enabled": True}
        except Exception as err:
            self.last_update_success = False
            _LOGGER.error(f"Error updating metrics: {err}")
            raise UpdateFailed(f"Failed to update metrics: {err}")

    async def async_request_refresh(self) -> None:
        """Request a refresh and always notify listeners to re-evaluate.

        Ensures entities depending on coordinator state (like the binary sensor)
        update their state even when a refresh fails due to an exception.
        """
        try:
            await super().async_request_refresh()
        finally:
            # Always notify listeners so CoordinatorEntity entities re-evaluate
            self.async_update_listeners()
