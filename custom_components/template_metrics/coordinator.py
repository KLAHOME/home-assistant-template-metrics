"""DataUpdateCoordinator for Grafana Metrics."""

import json
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import TemplateError
from opentelemetry.sdk.metrics import Meter

from .const import (
    DOMAIN,
    METER,
    UPDATE_INTERVAL,
    INSTANCE_LABEL,
    METRIC_LABEL_INSTANCE,
    TEMPLATE_ATTRIBUTES,
)

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

    def _normalize_attribute_value(self, value: Any) -> Any:
        """Normalize template output for use as an attribute."""
        if isinstance(value, str):
            stripped_value = value.strip()
            if not stripped_value:
                return ""
            if stripped_value[0] in ("[", "{"):
                try:
                    return json.loads(stripped_value)
                except json.JSONDecodeError:
                    return value
            return value
        return value

    def _render_metric_attributes(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """Render configured default attributes for a metric."""
        metric_attributes = dict(self._attributes)
        custom_attribute_templates = metric.get(TEMPLATE_ATTRIBUTES, {})
        if custom_attribute_templates:
            for attribute_name, attribute_template in custom_attribute_templates.items():
                rendered_attribute = Template(attribute_template, self.hass).async_render()
                if rendered_attribute is None:
                    _LOGGER.error(
                        "Template for attribute %s of %s returned None",
                        attribute_name,
                        metric["name"],
                    )
                    raise UpdateFailed(
                        f"Template attribute {attribute_name} returned None for {metric['name']}"
                    )
                metric_attributes[attribute_name] = self._normalize_attribute_value(rendered_attribute)
        return metric_attributes

    def _extract_series_entries(
        self, rendered_value: Any, metric_name: str
    ) -> list[dict[str, Any]] | None:
        """Interpret the template output as optional multi-series data."""
        candidate = rendered_value
        if isinstance(candidate, str):
            stripped_value = candidate.strip()
            if not stripped_value:
                return None
            if stripped_value[0] in ("[", "{"):
                try:
                    candidate = json.loads(stripped_value)
                except json.JSONDecodeError as err:
                    _LOGGER.error(
                        "Template for %s returned invalid JSON payload: %s",
                        metric_name,
                        stripped_value,
                    )
                    raise UpdateFailed(
                        f"Template {metric_name} returned invalid JSON payload"
                    ) from err
        if isinstance(candidate, dict):
            candidate = [candidate]
        if isinstance(candidate, list):
            entries: list[dict[str, Any]] = []
            for index, entry in enumerate(candidate):
                if not isinstance(entry, dict):
                    raise UpdateFailed(
                        f"Template {metric_name} returned invalid entry at index {index}"
                    )
                if "value" not in entry:
                    raise UpdateFailed(
                        f"Template {metric_name} entry {index} missing 'value'"
                    )
                attributes = entry.get("attributes", {})
                if attributes is None:
                    attributes = {}
                if not isinstance(attributes, dict):
                    raise UpdateFailed(
                        f"Template {metric_name} entry {index} attributes must be a mapping"
                    )
                normalized_attributes = {
                    key: self._normalize_attribute_value(val)
                    for key, val in attributes.items()
                }
                entries.append({"value": entry["value"], "attributes": normalized_attributes})
            return entries
        return None

    def _coerce_to_float(
        self,
        raw_value: Any,
        metric_name: str,
        *,
        series_index: int | None = None,
    ) -> float:
        """Ensure template output can be exported as a numeric metric."""
        try:
            return float(raw_value)
        except (TypeError, ValueError) as err:
            context = f" entry {series_index}" if series_index is not None else ""
            _LOGGER.error(
                "Invalid numeric value for %s%s: %s",
                metric_name,
                context,
                raw_value,
            )
            raise UpdateFailed(
                f"Invalid numeric value for {metric_name}{context}: {raw_value}"
            ) from err

    async def _async_update_data(self) -> Dict[str, Any]:
        """Push metrics to endpoint."""
        if not self.enabled:
            _LOGGER.debug("Push disabled, skipping metrics push")
            return {"success": True, "data": {}, "enabled": False}

        try:
            metrics_data: Dict[str, Any] = {}
            for metric in self._config["metrics"]:
                try:
                    template = Template(metric["template"], self.hass)
                    rendered_value = template.async_render()
                    if rendered_value is None:
                        _LOGGER.error(f"Template for {metric['name']} returned None")
                        raise UpdateFailed(f"Template {metric['name']} returned None")

                    gauge = self.meter.create_gauge(
                        metric["name"], description=f"HA {metric['name']}"
                    )
                    base_attributes = self._render_metric_attributes(metric)

                    series_entries = self._extract_series_entries(
                        rendered_value, metric["name"]
                    )
                    if series_entries is None:
                        float_value = self._coerce_to_float(
                            rendered_value, metric["name"]
                        )
                        set_kwargs: Dict[str, Any] = {}
                        if base_attributes:
                            set_kwargs["attributes"] = base_attributes
                        gauge.set(float_value, **set_kwargs)
                        metrics_data[metric["name"]] = float_value
                        _LOGGER.debug(
                            "Updated metric %s: %s", metric["name"], float_value
                        )
                        continue

                    metrics_data[metric["name"]] = []
                    for index, series_entry in enumerate(series_entries):
                        float_value = self._coerce_to_float(
                            series_entry["value"],
                            metric["name"],
                            series_index=index,
                        )
                        entry_attributes = dict(base_attributes)
                        entry_attributes.update(series_entry["attributes"])
                        set_kwargs: Dict[str, Any] = {}
                        if entry_attributes:
                            set_kwargs["attributes"] = entry_attributes
                        gauge.set(float_value, **set_kwargs)
                        metrics_data[metric["name"]].append(
                            {"value": float_value, "attributes": entry_attributes}
                        )
                        _LOGGER.debug(
                            "Updated metric %s series %s: %s",
                            metric["name"],
                            entry_attributes,
                            float_value,
                        )
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
