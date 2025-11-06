"""Tests for Prometheus metrics helpers."""

from typing import Dict

from metrics import (
    MetricsServer,
    active_alerts,
    app_info,
    get_metrics_server,
    monitor_checks_total,
)


def test_metrics_server_start(monkeypatch) -> None:
    captured: Dict[str, int] = {}

    def fake_start(port: int) -> None:
        captured["port"] = port

    monkeypatch.setattr("metrics.start_http_server", fake_start)

    server = MetricsServer(port=9876, enabled=True)
    server.start()

    assert server.is_running() is True
    assert captured["port"] == 9876

    # Starting twice should be a no-op.
    server.start()
    assert captured["port"] == 9876


def test_metrics_singleton_and_counters() -> None:
    server_one = get_metrics_server(port=9100)
    server_two = get_metrics_server(port=9200)
    assert server_one is server_two

    monitor_checks_total.inc()
    monitor_checks_total.inc()
    assert monitor_checks_total._value.get() == 2  # type: ignore[attr-defined]

    active_alerts.set(5)
    assert active_alerts._value.get() == 5  # type: ignore[attr-defined]

    app_info.info({"version": "test", "app_name": "zbxtg-test"})
