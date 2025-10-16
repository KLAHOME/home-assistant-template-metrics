"""Home Assistant Template Metrics Integration."""

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
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from opentelemetry import metrics
from .prometheus_remote_write import (
    PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from .const import (
    COORDINATOR,
    DOMAIN,
    USER,
    TOKEN,
    REMOTE_WRITE_URL,
    UPDATE_INTERVAL,
    METRICS,
    TEMPLATE_NAME,
    TEMPLATE,
    METER,
    PROVIDER,
)
from .coordinator import TemplateMetricsCoordinator

_LOGGER = logging.getLogger(__name__)

TEMPLATE_SCHEMA = vol.Schema(
    {
        vol.Required(TEMPLATE_NAME): cv.string,
        vol.Required(TEMPLATE): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(USER): cv.string,
                vol.Required(TOKEN): cv.string,
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
    """Set up the integration."""
    if DOMAIN not in config:
        return True

    config_data = config[DOMAIN]
    hass.data.setdefault(DOMAIN, {})

    if (
        not config_data[USER]
        or not config_data[TOKEN]
        or not config_data[REMOTE_WRITE_URL]
        or not len(config_data[METRICS])
    ):
        _LOGGER.error(
            "User, Token, Remote Write URL and at least one metric must be provided"
        )
        raise ConfigEntryNotReady

    # Setup OpenTelemetry for Metrics Export
    # resource = {}  # Optional: Füge resource attributes hinzu, z.B. service.name="ha-grafana"
    provider = MeterProvider(
        metric_readers=[
            PeriodicExportingMetricReader(
                PrometheusRemoteWriteMetricsExporter(
                    endpoint=config_data[REMOTE_WRITE_URL],
                    headers={
                        "Authorization": f"Basic {base64.b64encode(f'{config_data[USER]}:{config_data[TOKEN]}'.encode()).decode()}"
                    },
                ),
                export_interval_millis=1000 * config_data.get(UPDATE_INTERVAL, 60),
            )
        ]
    )
    metrics.set_meter_provider(provider)
    hass.data[DOMAIN][METER] = metrics.get_meter("ha_metrics")
    hass.data[DOMAIN][PROVIDER] = provider

    # Ensure OpenTelemetry background threads are shut down when HA stops
    async def _shutdown_otel(_event):
        try:
            # The SDK exposes a shutdown on the provider to flush and stop readers
            provider.shutdown()
        except Exception as err:
            _LOGGER.debug("Error during OpenTelemetry shutdown: %s", err)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown_otel)

    coordinator = TemplateMetricsCoordinator(
        hass,
        config=config_data,
    )
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][COORDINATOR] = coordinator

    await async_load_platform(hass, Platform.BINARY_SENSOR, DOMAIN, {}, config)
    await async_load_platform(hass, Platform.SWITCH, DOMAIN, {}, config)

    return True
