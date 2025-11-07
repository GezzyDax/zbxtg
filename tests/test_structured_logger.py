"""Tests for structured logging helpers."""

import logging
from pathlib import Path
from typing import Any, Dict, cast

import pytest

from structured_logger import StructuredLogger, setup_structured_logging


def test_setup_structured_logging_creates_handlers(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    log_dir = tmp_path / "logs"
    log_file = log_dir / "app.log"

    setup_structured_logging(level="DEBUG", json_output=False, log_file=str(log_file))

    # Log a message after setup
    test_logger = logging.getLogger("structured.test")
    test_logger.debug("structured message")

    # Verify file was created and contains the message
    assert log_file.exists()
    log_content = log_file.read_text()
    assert "structured message" in log_content


def test_structured_logger_context(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    logger = StructuredLogger("zbxtg.test")
    logger.set_context(user="alice")
    logger.info("action happened", action="restart")

    first_context = cast(Dict[str, Any], getattr(caplog.records[0], "context", {}))
    assert first_context["user"] == "alice"
    assert first_context["action"] == "restart"

    logger.clear_context()
    logger.info("clean context")
    second_context = cast(Dict[str, Any], getattr(caplog.records[1], "context", {}))
    assert second_context == {}
