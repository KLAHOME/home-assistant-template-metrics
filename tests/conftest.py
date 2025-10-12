"""Test fixtures for Home Assistant Metrics."""

import os
import sys
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.setup import async_setup_component

from custom_components.hametrics.const import DOMAIN


if "HA_CLONE" in os.environ:
    # Rewire the testing package to the cloned test modules
    sys.modules["pytest_homeassistant_custom_component"] = __import__("tests")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
):  # pylint: disable=unused-argument
    """Enable custom integrations."""
    yield


@pytest.fixture
def mock_config():
    """Fixture for a sample configuration."""
    return {
        DOMAIN: {
            "instance_id": "test_instance",
            "api_key": "test_api_key",
            "remote_write_url": "https://prometheus.example.com/api/prom/push",
            "update_interval": 60,
            "metrics": [
                {
                    "name": "ha_temperature_adjusted",
                    "template": "{{ states('sensor.temp') | float * 1.1 + 2 }}",
                },
                {
                    "name": "ha_uptime_hours",
                    "template": "{{ (now() - as_timestamp(states.homeassistant.start_time)) / 3600 | round(2) }}",
                },
            ],
        }
    }


@pytest.fixture
def mock_config_entry(mock_config):
    """Fixture for a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=mock_config[DOMAIN],
        unique_id="hametrics_test",
    )


@pytest.fixture(autouse=True)
def mock_opentelemetry(mocker):
    """Mock OpenTelemetry components to avoid real metric exports."""
    mocker.patch("opentelemetry.metrics.set_meter_provider")
    mock_meter = mocker.patch("opentelemetry.metrics.get_meter")
    mock_gauge = mocker.MagicMock()
    mocker.patch(
        "opentelemetry.exporter.prometheus_remote_write.PrometheusRemoteWriteMetricsExporter"
    )
    mock_meter.return_value.create_gauge.return_value = mock_gauge
    return mock_gauge


@pytest.fixture
async def setup_hass(hass, mock_config):
    """Set up Home Assistant with the Grafana Metrics integration."""
    await async_setup_component(
        hass, "homeassistant", {}
    )  # Setzt homeassistant.start_time
    hass.states.async_set("sensor.temp", "20.0")  # Mock-Sensor für Templates
    hass.states.async_set("homeassistant.start_time", "2025-10-10T00:00:00+00:00")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()
    return hass
