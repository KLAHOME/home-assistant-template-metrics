"""Home Assistant Template Metrics Integration."""

from __future__ import annotations

import base64
import logging
from typing import Any

import voluptuous as vol
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import (
    HomeAssistant,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from .const import (
    COORDINATOR,
    DEFAULT_JOB_LABEL,
    DOMAIN,
    INSTANCE_LABEL,
    JOB_LABEL,
    METER,
    METRICS,
    PROVIDER,
    REMOTE_WRITE_URL,
    TEMPLATE,
    TEMPLATE_ATTRIBUTES,
    TEMPLATE_NAME,
    TOKEN,
    UPDATE_INTERVAL,
    USER,
)
from .coordinator import TemplateMetricsCoordinator
from .prometheus_remote_write import (
    PrometheusRemoteWriteMetricsExporter,
)

_LOGGER = logging.getLogger(__name__)

TEMPLATE_SCHEMA = vol.Schema(
    {
        vol.Required(TEMPLATE_NAME): cv.string,
        vol.Required(TEMPLATE): cv.string,
        vol.Optional(TEMPLATE_ATTRIBUTES, default={}): {cv.string: cv.string},
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
                vol.Optional(INSTANCE_LABEL): cv.string,
                vol.Optional(JOB_LABEL, default=DEFAULT_JOB_LABEL): cv.string,
                vol.Required(METRICS): vol.All(
                    cv.ensure_list,
                    [TEMPLATE_SCHEMA],
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
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
        or (INSTANCE_LABEL in config_data and not config_data[INSTANCE_LABEL])
    ):
        _LOGGER.error(
            "User, Token, Remote Write URL and at least one metric must be provided"
        )
        raise ConfigEntryNotReady

    resource_attributes = {"service.name": "homeassistant"}

    provider = MeterProvider(
        resource=Resource(attributes=resource_attributes),
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
        ],
    )
    metrics.set_meter_provider(provider)
    hass.data[DOMAIN][METER] = metrics.get_meter("ha_metrics")
    hass.data[DOMAIN][PROVIDER] = provider

    # Ensure OpenTelemetry background threads are shut down when HA stops
    async def _shutdown_otel(_event):
        try:
            # The SDK exposes a shutdown on the provider to flush and stop readers
            provider.shutdown()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Error during OpenTelemetry shutdown: %s", err)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown_otel)

    coordinator = TemplateMetricsCoordinator(
        hass,
        config=config_data,
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][COORDINATOR] = coordinator

    await async_load_platform(hass, Platform.BINARY_SENSOR, DOMAIN, {}, config)
    await async_load_platform(hass, Platform.SWITCH, DOMAIN, {}, config)

    return True
