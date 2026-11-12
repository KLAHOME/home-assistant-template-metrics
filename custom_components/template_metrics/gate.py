"""Exporter gate: nothing leaves Home Assistant while pushing is disabled.

The OpenTelemetry SDK keeps the last value of a synchronous gauge and the
periodic reader exports it again on every interval (cumulative temporality),
also when the coordinator stopped rendering templates. The gate therefore sits
between the reader and the remote write exporter and drops every export while
disabled. Right after disabling it lets exactly one export through that only
contains the opt-in metric, so the receiver sees ``opt_in=0`` once and then
nothing.
"""

from __future__ import annotations

import logging
import threading

from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
)

from .const import OPT_IN_METRIC

_LOGGER = logging.getLogger(__name__)


class GatedMetricsExporter(MetricExporter):
    """Forwards exports to the wrapped exporter only while enabled."""

    def __init__(self, exporter: MetricExporter, enabled: bool = True) -> None:
        super().__init__(
            preferred_temporality=getattr(exporter, "_preferred_temporality", None),
            preferred_aggregation=getattr(exporter, "_preferred_aggregation", None),
        )
        self._exporter = exporter
        self._lock = threading.Lock()
        self._enabled = enabled
        self._opt_out = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        with self._lock:
            self._enabled = True
            self._opt_out = False

    def disable(self, send_opt_out: bool) -> None:
        """Stop forwarding; with send_opt_out the next export carries only the opt-in metric."""
        with self._lock:
            self._enabled = False
            self._opt_out = send_opt_out

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        opt_out = False
        with self._lock:
            if self._enabled:
                data = metrics_data
            elif self._opt_out:
                self._opt_out = False
                opt_out = True
                data = _only_opt_in(metrics_data)
            else:
                data = None
        if data is None:
            _LOGGER.debug("Push disabled, export dropped")
            return MetricExportResult.SUCCESS
        try:
            result = self._exporter.export(
                data, timeout_millis=timeout_millis, **kwargs
            )
        except Exception:
            result = MetricExportResult.FAILURE
            if opt_out:
                self._rearm_opt_out()
            raise
        if opt_out and result is not MetricExportResult.SUCCESS:
            self._rearm_opt_out()
        return result

    def _rearm_opt_out(self) -> None:
        """Retry the opt-out on the next export unless re-enabled meanwhile."""
        with self._lock:
            if not self._enabled:
                self._opt_out = True

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return self._exporter.force_flush(timeout_millis=timeout_millis)

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._exporter.shutdown(timeout_millis=timeout_millis, **kwargs)


def _only_opt_in(metrics_data: MetricsData) -> MetricsData | None:
    """The export reduced to the opt-in metric, None without it."""
    resource_metrics = []
    for rm in metrics_data.resource_metrics:
        scope_metrics = []
        for sm in rm.scope_metrics:
            kept = [m for m in sm.metrics if m.name == OPT_IN_METRIC]
            if kept:
                scope_metrics.append(
                    ScopeMetrics(scope=sm.scope, metrics=kept, schema_url=sm.schema_url)
                )
        if scope_metrics:
            resource_metrics.append(
                ResourceMetrics(
                    resource=rm.resource,
                    scope_metrics=scope_metrics,
                    schema_url=rm.schema_url,
                )
            )
    return MetricsData(resource_metrics=resource_metrics) if resource_metrics else None
