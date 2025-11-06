"""Tests for alert filtering logic."""

from typing import Dict

from filters import AlertFilters


def make_problem(
    severity: str = "3", resolved: bool = False, host_group: str = "Web"
) -> Dict[str, object]:
    """Helper to build a problem payload."""
    problem = {
        "problem": {
            "eventid": "12345",
            "severity": severity,
            "r_eventid": "1" if resolved else "0",
        },
        "hosts": [
            {
                "host": "web-1",
                "groups": [{"name": host_group}],
            }
        ],
        "trigger": {},
    }
    return problem


def test_filters_by_severity_and_status() -> None:
    filters = AlertFilters(min_severity=3)

    assert filters.should_send_alert(make_problem(severity="4")) is True
    assert filters.should_send_alert(make_problem(severity="2")) is False
    assert filters.should_send_alert(make_problem(resolved=True)) is False


def test_filters_quiet_hours(monkeypatch) -> None:
    filters = AlertFilters(
        min_severity=2,
        quiet_hours_enabled=True,
        quiet_hours_start="00:00",
        quiet_hours_end="23:59",
        quiet_hours_min_severity=5,
    )

    monkeypatch.setattr(filters, "is_in_quiet_hours", lambda: True)
    assert filters.should_send_alert(make_problem(severity="4")) is False
    assert filters.should_send_alert(make_problem(severity="5")) is True


def test_filters_host_groups_and_exclusions() -> None:
    filters = AlertFilters(host_groups=["DB"], excluded_hosts=["web-1"])

    allowed_problem = make_problem(host_group="DB")
    allowed_problem["problem"]["severity"] = "5"

    assert filters.should_send_alert(allowed_problem) is False

    matching_host_problem = make_problem(host_group="DB")
    matching_host_problem["problem"]["severity"] = "5"
    matching_host_problem["hosts"][0]["host"] = "db-1"
    assert filters.should_send_alert(matching_host_problem) is True


def test_filter_summary_contains_settings() -> None:
    filters = AlertFilters(
        min_severity=3,
        host_groups=["Web", "DB"],
        excluded_hosts=["maintenance"],
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
        quiet_hours_min_severity=4,
    )

    summary = filters.get_filter_summary()
    for expected in [
        "Минимальная серьезность: 3",
        "Группы хостов: Web, DB",
        "Исключенные хосты: maintenance",
        "Тихие часы: 22:00 - 07:00 (мин. серьезность: 4)",
    ]:
        assert expected in summary
