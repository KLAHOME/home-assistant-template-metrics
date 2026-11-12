"""Tests for the exporter gate."""

from unittest.mock import MagicMock

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    InMemoryMetricReader,
    MetricExporter,
    MetricExportResult,
)

from custom_components.template_metrics.const import OPT_IN_METRIC
from custom_components.template_metrics.gate import GatedMetricsExporter


def _metrics_data(opt_in: int):
    """Collect real SDK metrics data with the opt-in gauge and one other metric."""
    reader = InMemoryMetricReader()
    meter = MeterProvider(metric_readers=[reader]).get_meter("test")
    meter.create_gauge(OPT_IN_METRIC).set(opt_in, attributes={"instance": "x"})
    meter.create_gauge("ha_temperature").set(21.5, attributes={"instance": "x"})
    return reader.get_metrics_data()


def _names(metrics_data) -> set[str]:
    return {
        m.name
        for rm in metrics_data.resource_metrics
        for sm in rm.scope_metrics
        for m in sm.metrics
    }


def _inner() -> MagicMock:
    inner = MagicMock(spec=MetricExporter)
    inner._preferred_temporality = {}
    inner._preferred_aggregation = {}
    inner.export.return_value = MetricExportResult.SUCCESS
    return inner


def test_enabled_forwards_everything():
    inner = _inner()
    gate = GatedMetricsExporter(inner)
    data = _metrics_data(1)
    assert gate.export(data) is MetricExportResult.SUCCESS
    inner.export.assert_called_once()
    assert inner.export.call_args.args[0] is data


def test_disabled_without_opt_out_drops_everything():
    inner = _inner()
    gate = GatedMetricsExporter(inner)
    gate.disable(send_opt_out=False)
    assert gate.export(_metrics_data(1)) is MetricExportResult.SUCCESS
    inner.export.assert_not_called()


def test_opt_out_is_sent_exactly_once():
    inner = _inner()
    gate = GatedMetricsExporter(inner)
    gate.disable(send_opt_out=True)

    gate.export(_metrics_data(0))
    inner.export.assert_called_once()
    assert _names(inner.export.call_args.args[0]) == {OPT_IN_METRIC}

    gate.export(_metrics_data(0))
    gate.export(_metrics_data(0))
    inner.export.assert_called_once()


def test_enable_after_opt_out_forwards_again():
    inner = _inner()
    gate = GatedMetricsExporter(inner)
    gate.disable(send_opt_out=True)
    gate.enable()
    gate.export(_metrics_data(1))
    assert _names(inner.export.call_args.args[0]) == {OPT_IN_METRIC, "ha_temperature"}
    assert gate.enabled
