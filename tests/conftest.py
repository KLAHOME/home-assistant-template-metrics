"""Test fixtures for Home Assistant Metrics."""

import os
import sys
import pytest

from custom_components.template_metrics.const import DOMAIN


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
            "user": "test",
            "token": "testtoken",
            "remote_write_url": "https://prometheus.example.com/api/prom/push",
            "update_interval": 60,
            "metrics": [
                {
                    "name": "ha_temperature_adjusted",
                    "template": "{{ states('sensor.temp') | float * 1.1 + 2 }}",
                },
            ],
        }
    }


@pytest.fixture()
def mock_opentelemetry(mocker):
    """Mock OpenTelemetry components to avoid real metric exports."""
    mocker.patch("opentelemetry.metrics.set_meter_provider")
    mock_meter = mocker.patch("opentelemetry.metrics.get_meter")
    mock_gauge = mocker.MagicMock()
    mocker.patch(
        "custom_components.template_metrics.PrometheusRemoteWriteMetricsExporter"
    )
    mock_meter.return_value.create_gauge.return_value = mock_gauge
    return mock_gauge
