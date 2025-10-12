"""Home Assistant Metrics Integration."""

from __future__ import annotations

import logging
from typing import Any, Dict
import base64

import voluptuous as vol
from homeassistant.const import (
    Platform,
)
from homeassistant.core import (
    HomeAssistant,
)
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from opentelemetry import metrics
from opentelemetry.exporter.prometheus_remote_write import (
    PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from .const import (
    COORDINATOR,
    DOMAIN,
    INSTANCE_ID,
    API_KEY,
    REMOTE_WRITE_URL,
    UPDATE_INTERVAL,
    METRICS,
    TEMPLATE_NAME,
    TEMPLATE,
    METER,
)
from .coordinator import HAMetricsCoordinator

_LOGGER = logging.getLogger(__name__)

TEMPLATE_SCHEMA = vol.Schema(
    {
        vol.Required(TEMPLATE_NAME): cv.string,
        vol.Required(TEMPLATE): cv.template,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(INSTANCE_ID): cv.string,
                vol.Required(API_KEY): cv.string,
                vol.Required(REMOTE_WRITE_URL): cv.url,
                vol.Optional(UPDATE_INTERVAL, default=60): cv.positive_int,
                vol.Required(METRICS): vol.All(
                    cv.ensure_list,
                    [TEMPLATE_SCHEMA],
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Grafana Metrics Sender integration."""
    if DOMAIN not in config:
        return True

    config_data = config[DOMAIN]
    hass.data.setdefault(DOMAIN, {})

    # Setup OpenTelemetry for Metrics Export
    # resource = {}  # Optional: Füge resource attributes hinzu, z.B. service.name="ha-grafana"
    provider = MeterProvider(
        metric_readers=[
            PeriodicExportingMetricReader(
                PrometheusRemoteWriteMetricsExporter(
                    endpoint=config_data[REMOTE_WRITE_URL],
                    headers={
                        "Authorization": f"Basic {base64.b64encode(f'{config_data[INSTANCE_ID]}:{config_data[API_KEY]}'.encode()).decode()}"
                    },
                ),
                export_interval_millis=1000 * config_data.get(UPDATE_INTERVAL, 60),
            )
        ]
    )
    metrics.set_meter_provider(provider)
    hass.data[DOMAIN][METER] = metrics.get_meter("ha_metrics")

    # Coordinator für periodische Updates
    coordinator = HAMetricsCoordinator(
        hass,
        config=config_data,
    )
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][COORDINATOR] = coordinator

    # await hass.async_create_task(
    #    hass.config_entries.async_forward_entry_setups(coordinator, PLATFORMS)
    # )
    await async_load_platform(hass, Platform.BINARY_SENSOR, DOMAIN, {}, config)
    await async_load_platform(hass, Platform.SWITCH, DOMAIN, {}, config)

    return True
