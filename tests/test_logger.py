import pytest
import logging
import os
from src.utils.logger import AlertLogger

def test_logger_initialization():
    logger = AlertLogger()
    
    # Check if logger is created with correct name
    assert logger.logger.name == "AlertCorrelation"
    
    # Check default log level
    assert logger.logger.level == logging.INFO
    
    # Check if console handler is added
    assert len(logger.logger.handlers) == 1
    assert isinstance(logger.logger.handlers[0], logging.StreamHandler)

def test_logger_with_file(tmp_path):
    # Create a temporary log file
    log_file = tmp_path / "test.log"
    
    # Initialize logger with file
    logger = AlertLogger(log_file=str(log_file))
    
    # Check if both console and file handlers are added
    assert len(logger.logger.handlers) == 2
    assert any(isinstance(h, logging.FileHandler) for h in logger.logger.handlers)
    
    # Test logging
    test_message = "Test log message"
    logger.info(test_message)
    
    # Verify log file was created and contains the message
    assert log_file.exists()
    with open(log_file, 'r') as f:
        log_content = f.read()
        assert test_message in log_content

def test_logger_different_levels():
    logger = AlertLogger(log_level="DEBUG")
    
    # Test all log levels
    test_messages = {
        "debug": "Debug message",
        "info": "Info message",
        "warning": "Warning message",
        "error": "Error message"
    }
    
    logger.debug(test_messages["debug"])
    logger.info(test_messages["info"])
    logger.warning(test_messages["warning"])
    logger.error(test_messages["error"])
    
    # Verify logger level is set correctly
    assert logger.logger.level == logging.DEBUG

def test_logger_format():
    logger = AlertLogger()
    
    # Get the formatter from the console handler
    formatter = logger.logger.handlers[0].formatter
    
    # Test the format
    record = logging.LogRecord(
        name="AlertCorrelation",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    formatted_message = formatter.format(record)
    
    # Check if format contains expected components
    assert "AlertCorrelation" in formatted_message
    assert "INFO" in formatted_message
    assert "Test message" in formatted_message 