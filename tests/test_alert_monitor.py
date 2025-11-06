"""Tests for alert_monitor module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alert_monitor import AlertMonitor


class TestAlertMonitor:
    """Tests for AlertMonitor class."""

    def test_alert_monitor_initialization(self, app_config):
        """Test AlertMonitor initialization."""
        mock_zabbix = MagicMock()
        mock_telegram = MagicMock()

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        assert monitor.config == app_config
        assert monitor.zabbix_client == mock_zabbix
        assert monitor.telegram_bot == mock_telegram
        assert monitor.sent_alerts == {}
        assert monitor.is_running is False

    @pytest.mark.asyncio
    async def test_process_problem(self, app_config, mock_problem, mock_problem_details):
        """Test processing a single problem."""
        mock_zabbix = MagicMock()
        mock_zabbix.get_problem_details = MagicMock(return_value=mock_problem_details)

        mock_telegram = AsyncMock()
        mock_telegram.send_alert = AsyncMock(return_value=123)

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        await monitor._process_problem(mock_problem)

        assert "12345" in monitor.sent_alerts
        assert monitor.sent_alerts["12345"]["message_id"] == 123
        assert monitor.sent_alerts["12345"]["status"] == "problem"
        assert monitor.stats["alerts_sent"] == 1

    @pytest.mark.asyncio
    async def test_process_problem_failure(self, app_config, mock_problem, mock_problem_details):
        """Test processing problem when sending fails."""
        mock_zabbix = MagicMock()
        mock_zabbix.get_problem_details = MagicMock(return_value=mock_problem_details)

        mock_telegram = AsyncMock()
        mock_telegram.send_alert = AsyncMock(return_value=None)

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        await monitor._process_problem(mock_problem)

        assert "12345" not in monitor.sent_alerts
        assert len(monitor.failed_alerts) == 1

    def test_should_send_alert_severity_filter(self, app_config, mock_problem_details):
        """Test alert filtering by severity."""
        mock_zabbix = MagicMock()
        mock_telegram = MagicMock()

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        # Severity 3 should pass (min_severity is 2)
        assert monitor._should_send_alert(mock_problem_details) is True

        # Severity 1 should be filtered
        mock_problem_details["problem"]["severity"] = "1"
        assert monitor._should_send_alert(mock_problem_details) is False

    def test_should_send_alert_resolved(self, app_config, mock_problem_details):
        """Test alert filtering for resolved problems."""
        mock_zabbix = MagicMock()
        mock_telegram = MagicMock()

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        # Active problem should pass
        assert monitor._should_send_alert(mock_problem_details) is True

        # Resolved problem should be filtered
        mock_problem_details["problem"]["r_eventid"] = "99999"
        assert monitor._should_send_alert(mock_problem_details) is False

    @pytest.mark.asyncio
    async def test_check_for_alerts(self, app_config, mock_problem):
        """Test checking for new alerts."""
        mock_zabbix = MagicMock()
        mock_zabbix.get_problems = MagicMock(return_value=[mock_problem])
        mock_zabbix.get_problem_details = MagicMock(
            return_value={"problem": mock_problem, "trigger": {}, "hosts": []}
        )

        mock_telegram = AsyncMock()
        mock_telegram.send_alert = AsyncMock(return_value=123)

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)
        monitor.last_check_time = 0  # Set to 0 to ensure problem is processed

        await monitor._check_for_alerts()

        assert monitor.stats["problems_found"] > 0

    @pytest.mark.asyncio
    async def test_check_for_status_updates(self, app_config, mock_problem):
        """Test checking for status updates."""
        # Create a resolved problem
        resolved_problem = mock_problem.copy()
        resolved_problem["r_eventid"] = "99999"

        mock_zabbix = MagicMock()
        mock_zabbix.get_problems = MagicMock(return_value=[resolved_problem])
        mock_zabbix.get_problem_details = MagicMock(
            return_value={"problem": resolved_problem, "trigger": {}, "hosts": []}
        )

        mock_telegram = AsyncMock()
        mock_telegram.update_alert = AsyncMock(return_value=True)

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        # Add existing alert
        monitor.sent_alerts["12345"] = {
            "message_id": 123,
            "timestamp": 1000,
            "status": "problem",
        }

        await monitor._check_for_status_updates()

        # Status should be updated to resolved
        assert monitor.sent_alerts["12345"]["status"] == "resolved"
        assert "resolved_at" in monitor.sent_alerts["12345"]

    @pytest.mark.asyncio
    async def test_cleanup_resolved_alerts(self, app_config):
        """Test cleanup of resolved alerts."""
        mock_zabbix = MagicMock()
        mock_telegram = AsyncMock()
        mock_telegram.delete_message = AsyncMock(return_value=True)

        app_config.delete_resolved_after = 1  # 1 second
        app_config.mark_resolved = False  # Enable deletion

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        # Add resolved alert from the past
        import time

        monitor.sent_alerts["12345"] = {
            "message_id": 123,
            "timestamp": time.time(),
            "status": "resolved",
            "resolved_at": time.time() - 10,  # Resolved 10 seconds ago
        }

        await monitor._cleanup_resolved_alerts()

        # Alert should be deleted
        assert "12345" not in monitor.sent_alerts
        mock_telegram.delete_message.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_cleanup_resolved_alerts_mark_only(self, app_config):
        """Test marking resolved alerts without deletion."""
        mock_zabbix = MagicMock()
        mock_telegram = AsyncMock()

        app_config.delete_resolved_after = 1
        app_config.mark_resolved = True  # Don't delete, just mark

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        import time

        monitor.sent_alerts["12345"] = {
            "message_id": 123,
            "timestamp": time.time(),
            "status": "resolved",
            "resolved_at": time.time() - 10,
        }

        await monitor._cleanup_resolved_alerts()

        # Alert should still exist (not deleted)
        assert "12345" in monitor.sent_alerts
        mock_telegram.delete_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_failed_alerts(self, app_config, mock_problem_details):
        """Test retrying failed alerts."""
        mock_zabbix = MagicMock()
        mock_telegram = AsyncMock()
        mock_telegram.send_alert = AsyncMock(return_value=456)

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        # Add failed alert
        monitor.failed_alerts.append(
            {
                "problem_details": mock_problem_details,
                "timestamp": 1000,
                "attempts": 1,
            }
        )

        await monitor._retry_failed_alerts()

        # Alert should be sent successfully
        assert len(monitor.failed_alerts) == 0
        assert "12345" in monitor.sent_alerts

    @pytest.mark.asyncio
    async def test_retry_failed_alerts_max_attempts(self, app_config, mock_problem_details):
        """Test failed alerts with max attempts exceeded."""
        mock_zabbix = MagicMock()
        mock_telegram = AsyncMock()
        mock_telegram.send_alert = AsyncMock(return_value=None)

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        # Add failed alert with max attempts
        monitor.failed_alerts.append(
            {
                "problem_details": mock_problem_details,
                "timestamp": 1000,
                "attempts": 5,
            }
        )

        await monitor._retry_failed_alerts()

        # Alert should be discarded
        assert len(monitor.failed_alerts) == 0
        assert "12345" not in monitor.sent_alerts

    @pytest.mark.asyncio
    async def test_get_status(self, app_config):
        """Test getting monitor status."""
        mock_zabbix = MagicMock()
        mock_zabbix._make_request = MagicMock(return_value="6.0.0")

        mock_telegram = AsyncMock()
        mock_telegram.check_connection = AsyncMock(return_value=True)

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)
        monitor.is_running = True

        from datetime import datetime

        monitor.stats["start_time"] = datetime.now()

        status = await monitor.get_status()

        assert status["running"] is True
        assert "uptime_seconds" in status
        assert "uptime_str" in status
        assert status["telegram_connected"] is True

    @pytest.mark.asyncio
    async def test_send_status_message(self, app_config):
        """Test sending status message."""
        mock_zabbix = MagicMock()
        mock_zabbix._make_request = MagicMock(return_value="6.0.0")

        mock_telegram = AsyncMock()
        mock_telegram.check_connection = AsyncMock(return_value=True)
        mock_telegram.send_message = AsyncMock()

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

        from datetime import datetime

        monitor.stats["start_time"] = datetime.now()

        await monitor.send_status_message()

        mock_telegram.send_message.assert_called_once()

    def test_stop_monitoring(self, app_config):
        """Test stopping monitor."""
        mock_zabbix = MagicMock()
        mock_telegram = MagicMock()

        monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)
        monitor.is_running = True

        monitor.stop_monitoring()

        assert monitor.is_running is False
