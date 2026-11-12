"""Test fixtures for Home Assistant Metrics."""

import os
import sys

import pytest
from opentelemetry.sdk.metrics.export import MetricExportResult

from custom_components.template_metrics.const import DOMAIN, OPT_IN_METRIC

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
            "instance_label": "test-instance",
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
    exporter_cls = mocker.patch(
        "custom_components.template_metrics.PrometheusRemoteWriteMetricsExporter"
    )
    exporter_cls.return_value.export.return_value = MetricExportResult.SUCCESS
    mocker.patch("custom_components.template_metrics.PeriodicExportingMetricReader")

    # The opt-in gauge is separate so metric tests only see their own values
    opt_in_gauge = mocker.MagicMock()
    mock_meter.return_value.create_gauge.side_effect = lambda name, **_: (
        opt_in_gauge if name == OPT_IN_METRIC else mock_gauge
    )
    mock_gauge.opt_in_gauge = opt_in_gauge
    # The exporter behind the gate, to check what actually leaves the instance
    mock_gauge.exporter = exporter_cls.return_value
    return mock_gauge
