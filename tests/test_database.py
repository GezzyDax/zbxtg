"""Tests for the alert database module."""

import time
from pathlib import Path

import pytest

from database import AlertDatabase


@pytest.mark.asyncio
async def test_alert_database_crud_operations(tmp_path: Path) -> None:
    """Ensure the alert database supports full CRUD workflow."""
    db_path = tmp_path / "alerts.db"
    database = AlertDatabase(str(db_path))
    await database.initialize()

    event_id = "evt-1"
    await database.save_alert(
        event_id,
        message_id=101,
        status="problem",
        severity=4,
        hostname="web-1",
        problem_name="High load",
        metadata={"service": "web"},
    )

    alert = await database.get_alert(event_id)
    assert alert is not None
    assert alert["status"] == "problem"
    assert alert["hostname"] == "web-1"

    await database.update_alert_status(event_id, status="resolved", resolved_at=time.time())
    alert = await database.get_alert(event_id)
    assert alert is not None
    assert alert["status"] == "resolved"
    assert alert["resolved_at"] is not None

    # Insert another active alert to exercise listing helpers.
    await database.save_alert("evt-2", message_id=202, status="problem", severity=2)

    active_alerts = await database.get_active_alerts()
    assert len(active_alerts) == 1
    assert active_alerts[0]["event_id"] == "evt-2"

    resolved_alerts = await database.get_alerts_by_status("resolved")
    assert any(alert_row["event_id"] == event_id for alert_row in resolved_alerts)

    # Force the first alert to look stale and verify cleanup.
    cutoff = time.time() - (40 * 24 * 3600)
    async with database.get_connection() as conn:
        await conn.execute(
            "UPDATE alerts SET created_at = ? WHERE event_id = ?",
            (cutoff, event_id),
        )

    deleted = await database.delete_old_alerts(days=30)
    assert deleted == 1


@pytest.mark.asyncio
async def test_alert_database_statistics(tmp_path: Path) -> None:
    """Validate statistics helpers."""
    db_path = tmp_path / "stats.db"
    database = AlertDatabase(str(db_path))
    await database.initialize()

    await database.save_statistic("alerts_sent", 3)
    await database.save_statistic("alerts_sent", 2)
    stats = await database.get_statistics("alerts_sent", days=1)
    assert stats
    assert stats[0]["total"] == 5

    await database.log_event("alert_sent", event_id="evt-100", details="Test alert")
    events = await database.get_recent_events(limit=5)
    assert len(events) == 1
    assert events[0]["event_type"] == "alert_sent"

    # Seed data for summary metrics.
    await database.save_alert("evt-active", message_id=1, status="problem", severity=4)
    await database.save_alert("evt-resolved", message_id=2, status="resolved", severity=2)

    summary = await database.get_stats_summary()
    assert summary["total_alerts"] == 2
    assert summary["active_alerts"] == 1
    assert summary["resolved_alerts"] == 1
    assert summary["severity_distribution"][4] == 1
