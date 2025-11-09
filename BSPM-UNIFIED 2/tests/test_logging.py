"""
Test Suite: Structured Logging
Version: 3.2
Platform: Intel Mac (macOS Ventura) + Docker

Tests for structured JSON logging configuration.
"""

import pytest
import json
import logging
from pathlib import Path
from backend.logging_config import (
    StructuredFormatter, setup_logging, LoggerAdapter
)
from unittest.mock import Mock, patch


class TestStructuredFormatter:
    """Test StructuredFormatter class."""

    def test_format_basic_record(self):
        """Format basic log record to JSON."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data['level'] == 'INFO'
        assert data['logger'] == 'test.logger'
        assert data['message'] == 'Test message'
        assert 'timestamp' in data

    def test_format_with_correlation_id(self):
        """Include correlation_id in output."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.correlation_id = 'req_12345'

        output = formatter.format(record)
        data = json.loads(output)

        assert data['correlation_id'] == 'req_12345'

    def test_format_with_session_id(self):
        """Include session_id in output."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.session_id = 'sess_abc'

        output = formatter.format(record)
        data = json.loads(output)

        assert data['session_id'] == 'sess_abc'

    def test_format_with_exception(self):
        """Include exception info in output."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name='test.logger',
                level=logging.ERROR,
                pathname='test.py',
                lineno=42,
                msg='Error occurred',
                args=(),
                exc_info=exc_info
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert 'exception' in data
            assert data['exception']['type'] == 'ValueError'
            assert data['exception']['message'] == 'Test error'
            assert 'traceback' in data['exception']

    def test_format_with_extra_fields(self):
        """Include extra fields in output."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.user_id = 'user_123'
        record.request_id = 'req_456'

        output = formatter.format(record)
        data = json.loads(output)

        assert 'extra' in data
        assert data['extra']['user_id'] == 'user_123'
        assert data['extra']['request_id'] == 'req_456'

    def test_timestamp_format(self):
        """Timestamp is in ISO 8601 format."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        # Should end with 'Z' for UTC
        assert data['timestamp'].endswith('Z')
        # Should parse as valid datetime
        from datetime import datetime
        datetime.fromisoformat(data['timestamp'].rstrip('Z'))


class TestSetupLogging:
    """Test setup_logging function."""

    def test_creates_log_directory(self, temp_dir):
        """Creates log directory if it doesn't exist."""
        log_dir = temp_dir / "logs"

        assert not log_dir.exists()

        setup_logging(log_dir=str(log_dir), log_level="INFO")

        assert log_dir.exists()

    def test_creates_log_files(self, temp_dir):
        """Creates expected log files."""
        log_dir = temp_dir / "logs"

        setup_logging(log_dir=str(log_dir), log_level="INFO")

        assert (log_dir / "app.log").exists()
        assert (log_dir / "error.log").exists()
        assert (log_dir / "app.jsonl").exists()

    def test_sets_log_level(self, temp_dir):
        """Sets correct log level."""
        log_dir = temp_dir / "logs"

        logger = setup_logging(log_dir=str(log_dir), log_level="DEBUG")

        assert logger.level == logging.DEBUG

    def test_logs_to_console(self, temp_dir, caplog):
        """Logs to console handler."""
        log_dir = temp_dir / "logs"

        logger = setup_logging(log_dir=str(log_dir), log_level="INFO")
        logger.info("Test console message")

        assert "Test console message" in caplog.text

    def test_logs_to_file(self, temp_dir):
        """Logs to file handlers."""
        log_dir = temp_dir / "logs"

        logger = setup_logging(log_dir=str(log_dir), log_level="INFO")
        logger.info("Test file message")

        # Check app.log
        app_log_content = (log_dir / "app.log").read_text()
        log_entry = json.loads(app_log_content.strip())

        assert log_entry['message'] == "Test file message"

    def test_error_logs_separate_file(self, temp_dir):
        """Error logs go to separate file."""
        log_dir = temp_dir / "logs"

        logger = setup_logging(log_dir=str(log_dir), log_level="INFO")
        logger.info("Info message")
        logger.error("Error message")

        # error.log should only have error
        error_log_content = (log_dir / "error.log").read_text()
        error_entry = json.loads(error_log_content.strip())

        assert error_entry['level'] == 'ERROR'
        assert error_entry['message'] == "Error message"

    def test_jsonl_format(self, temp_dir):
        """JSONL file has one JSON object per line."""
        log_dir = temp_dir / "logs"

        logger = setup_logging(log_dir=str(log_dir), log_level="INFO")
        logger.info("Message 1")
        logger.info("Message 2")

        jsonl_content = (log_dir / "app.jsonl").read_text()
        lines = jsonl_content.strip().split('\n')

        assert len(lines) >= 2  # At least our 2 messages (may have setup log)

        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert 'timestamp' in data
            assert 'message' in data

    @patch('logging.handlers.RotatingFileHandler')
    def test_rotation_configuration(self, mock_handler_class, temp_dir):
        """File handlers configured with rotation."""
        log_dir = temp_dir / "logs"

        setup_logging(
            log_dir=str(log_dir),
            log_level="INFO",
            max_bytes=10 * 1024 * 1024,
            backup_count=5
        )

        # Should have created rotating handlers
        assert mock_handler_class.call_count >= 3  # app.log, error.log, app.jsonl


class TestLoggerAdapter:
    """Test LoggerAdapter class."""

    def test_includes_context_in_logs(self, caplog):
        """Adapter includes context in all logs."""
        base_logger = logging.getLogger('test.adapter')
        adapter = LoggerAdapter(base_logger, {
            'correlation_id': 'req_123',
            'session_id': 'sess_456'
        })

        caplog.set_level(logging.INFO)
        adapter.info("Test message")

        # Check that extra fields were passed
        record = caplog.records[0]
        assert hasattr(record, 'correlation_id')
        assert record.correlation_id == 'req_123'
        assert hasattr(record, 'session_id')
        assert record.session_id == 'sess_456'

    def test_merges_extra_fields(self, caplog):
        """Adapter merges extra fields from both adapter and log call."""
        base_logger = logging.getLogger('test.adapter')
        adapter = LoggerAdapter(base_logger, {
            'correlation_id': 'req_123'
        })

        caplog.set_level(logging.INFO)
        adapter.info("Test message", extra={'request_type': 'POST'})

        record = caplog.records[0]
        assert hasattr(record, 'correlation_id')
        assert hasattr(record, 'request_type')


class TestLoggingIntegration:
    """Test logging integration scenarios."""

    def test_structured_logging_with_exception(self, temp_dir):
        """Log exceptions with structured format."""
        log_dir = temp_dir / "logs"
        logger = setup_logging(log_dir=str(log_dir), log_level="ERROR")

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred")

        # Check log file
        log_content = (log_dir / "error.log").read_text()
        log_entry = json.loads(log_content.strip())

        assert log_entry['level'] == 'ERROR'
        assert 'exception' in log_entry
        assert log_entry['exception']['type'] == 'ValueError'

    def test_correlation_id_tracking(self, temp_dir):
        """Track correlation ID through request lifecycle."""
        log_dir = temp_dir / "logs"
        base_logger = setup_logging(log_dir=str(log_dir), log_level="INFO")

        # Create adapter with correlation ID
        adapter = LoggerAdapter(base_logger, {
            'correlation_id': 'req_abc123'
        })

        adapter.info("Request started")
        adapter.info("Processing request")
        adapter.info("Request completed")

        # Check logs have correlation ID
        log_content = (log_dir / "app.log").read_text()
        lines = log_content.strip().split('\n')

        for line in lines:
            entry = json.loads(line)
            if 'Request' in entry['message']:
                assert entry.get('correlation_id') == 'req_abc123'

    def test_multi_logger_isolation(self, temp_dir):
        """Multiple loggers maintain isolation."""
        log_dir = temp_dir / "logs"
        setup_logging(log_dir=str(log_dir), log_level="INFO")

        logger1 = logging.getLogger('module1')
        logger2 = logging.getLogger('module2')

        logger1.info("Module 1 message")
        logger2.info("Module 2 message")

        # Both should be in log file
        log_content = (log_dir / "app.log").read_text()
        lines = log_content.strip().split('\n')

        loggers_found = set()
        for line in lines:
            entry = json.loads(line)
            loggers_found.add(entry['logger'])

        assert 'module1' in loggers_found
        assert 'module2' in loggers_found


# Run with: pytest tests/test_logging.py -v
# Run with coverage: pytest tests/test_logging.py --cov=backend.logging_config
