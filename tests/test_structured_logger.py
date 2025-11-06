"""Tests for structured logging helpers."""

import logging
from pathlib import Path

import pytest

from structured_logger import StructuredLogger, setup_structured_logging


def test_setup_structured_logging_creates_handlers(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    log_dir = tmp_path / "logs"
    log_file = log_dir / "app.log"

    setup_structured_logging(level="DEBUG", json_output=False, log_file=str(log_file))

    logging.getLogger("structured.test").debug("structured message")
    assert "structured message" in caplog.text
    assert log_file.exists()


def test_structured_logger_context(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    logger = StructuredLogger("zbxtg.test")
    logger.set_context(user="alice")
    logger.info("action happened", action="restart")

    assert caplog.records[0].context["user"] == "alice"
    assert caplog.records[0].context["action"] == "restart"

    logger.clear_context()
    logger.info("clean context")
    assert caplog.records[1].context == {}
