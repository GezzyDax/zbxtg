"""Prometheus metrics for monitoring application performance."""

import logging

from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

logger = logging.getLogger(__name__)

# Application info
app_info = Info("zbxtg_app", "Application information")

# Zabbix metrics
zabbix_requests_total = Counter(
    "zbxtg_zabbix_requests_total",
    "Total number of Zabbix API requests",
    ["method", "status"],
)

zabbix_request_duration_seconds = Histogram(
    "zbxtg_zabbix_request_duration_seconds",
    "Zabbix API request duration in seconds",
    ["method"],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

zabbix_problems_found = Counter(
    "zbxtg_zabbix_problems_found_total",
    "Total number of problems found in Zabbix",
    ["severity"],
)

# Telegram metrics
telegram_messages_sent_total = Counter(
    "zbxtg_telegram_messages_sent_total",
    "Total number of Telegram messages sent",
    ["status"],
)

telegram_messages_edited_total = Counter(
    "zbxtg_telegram_messages_edited_total",
    "Total number of Telegram messages edited",
    ["status"],
)

telegram_messages_deleted_total = Counter(
    "zbxtg_telegram_messages_deleted_total",
    "Total number of Telegram messages deleted",
    ["status"],
)

# Alert metrics
alerts_sent_total = Counter(
    "zbxtg_alerts_sent_total",
    "Total number of alerts sent",
    ["severity"],
)

alerts_failed_total = Counter(
    "zbxtg_alerts_failed_total",
    "Total number of failed alert sends",
    ["reason"],
)

alerts_updated_total = Counter(
    "zbxtg_alerts_updated_total",
    "Total number of alerts updated",
    ["status_change"],
)

active_alerts = Gauge(
    "zbxtg_active_alerts",
    "Current number of active alerts being tracked",
)

failed_alerts_queue = Gauge(
    "zbxtg_failed_alerts_queue",
    "Current number of alerts in failed queue waiting for retry",
)

# Monitor metrics
monitor_checks_total = Counter(
    "zbxtg_monitor_checks_total",
    "Total number of monitoring check cycles",
)

monitor_errors_total = Counter(
    "zbxtg_monitor_errors_total",
    "Total number of monitoring errors",
    ["error_type"],
)

monitor_last_check_timestamp = Gauge(
    "zbxtg_monitor_last_check_timestamp",
    "Unix timestamp of last successful monitoring check",
)

# System metrics
app_uptime_seconds = Gauge(
    "zbxtg_app_uptime_seconds",
    "Application uptime in seconds",
)


class MetricsServer:
    """Prometheus metrics HTTP server."""

    def __init__(self, port: int = 9090, enabled: bool = True):
        self.port = port
        self.enabled = enabled
        self.started = False

    def start(self):
        """Starts the Prometheus metrics HTTP server."""
        if not self.enabled:
            logger.info("Metrics server disabled")
            return

        if self.started:
            logger.warning("Metrics server already started")
            return

        try:
            start_http_server(self.port)
            self.started = True
            logger.info(f"Metrics server started on port {self.port}")

            # Set application info
            app_info.info(
                {
                    "version": "2.0.0",
                    "app_name": "zbxtg",
                }
            )
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

    def is_running(self) -> bool:
        """Check if metrics server is running."""
        return self.started


# Global metrics server instance
_metrics_server = None


def get_metrics_server(port: int = 9090, enabled: bool = True) -> MetricsServer:
    """Get or create the global metrics server instance."""
    global _metrics_server
    if _metrics_server is None:
        _metrics_server = MetricsServer(port, enabled)
    return _metrics_server
