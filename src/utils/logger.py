"""
Logging Configuration Module for AdminFlow.

This module provides comprehensive logging capabilities for the AdminFlow
Active Directory automation system. It establishes both file-based and
console logging with structured output format.

Features:
- Configurable log levels
- Automatic log directory creation
- Timestamped output
- Custom logger class for AD operations
- Security event logging

Usage:
    # Basic setup - configures root logger
    setup_logging("logs/ad_automation.log")

    # Use logger
    logger = logging.getLogger(__name__)
    logger.info("Operation completed")

    # Use custom ADLogger for structured logging
    ad_logger = ADLogger("ad_operations")
    ad_logger.log_operation("User Creation", "SUCCESS", "Created user jsmith")

Log Output Format:
    2024-01-15 10:30:45 - module_name - INFO - Message content

Files:
    Log files are stored in the logs/ directory with rotation
    managed by the operating system or external tools.
"""

import logging
from datetime import datetime
from pathlib import Path


def setup_logging(
    log_file: str = "logs/ad_automation.log", level: int = logging.INFO
) -> logging.Logger:
    """
    Configure the logging system with file and console handlers.

    This function sets up a comprehensive logging configuration with:
    - File handler: Writes all logs to specified file
    - Console handler: Outputs logs to stdout for real-time monitoring

    Args:
        log_file: Path to log file (default: logs/ad_automation.log)
                 The directory will be created if it doesn't exist
        level: Logging level (default: logging.INFO)
               Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

    Returns:
        logging.Logger: The configured logger for this module

    Example:
        # Configure logging with custom settings
        setup_logging("logs/my_app.log", logging.DEBUG)

        # Later in code
        logger = logging.getLogger(__name__)
        logger.debug("Debug message")
        logger.info("Info message")
    """

    # Ensure log directory exists
    # Creates parent directories as needed (parents=True)
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure the root logger with basic settings
    # This establishes the default behavior for all loggers
    logging.basicConfig(
        level=level,
        # Format: timestamp - logger name - level - message
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        # Use both file and console handlers
        handlers=[
            # File handler - logs everything to file
            logging.FileHandler(log_file),
            # Stream handler - outputs to console
            logging.StreamHandler(),
        ],
    )

    # Return logger for this module
    return logging.getLogger(__name__)


class ADLogger:
    """
    Custom logger for Active Directory operations with structured logging.

    This class provides specialized logging methods tailored for AD
    operations, making it easier to track and audit AD changes.

    Features:
    - Structured operation logging with status
    - User action logging (create, modify, delete)
    - Security event logging with alerts
    - Timestamped messages in consistent format

    Attributes:
        name: Logger name (typically module name)
        log_dir: Directory for log files

    Example:
        >>> ad_logger = ADLogger("user_management")
        >>> ad_logger.log_user_action("jsmith", "CREATE", "User created in OU=IT")
        >>> ad_logger.log_security_event("PRIVILEGED_ACCESS", "Admin login detected")
    """

    def __init__(self, name: str, log_dir: str = "logs"):
        """
        Initialize ADLogger with name and optional log directory.

        Args:
            name: Identifier for this logger (e.g., "user_management")
            log_dir: Directory for log files (default: "logs")
        """
        # Get standard Python logger
        self.logger = logging.getLogger(name)

        # Store log directory and ensure it exists
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_operation(self, operation: str, status: str, details: str = ""):
        """
        Log an AD operation with structured format.

        Creates a standardized log entry with timestamp, operation name,
        status, and optional details. This is useful for tracking the
        outcome of AD management operations.

        Args:
            operation: Name of the operation (e.g., "User Creation", "Group Update")
            status: Operation result status
                   Use: "SUCCESS", "WARNING", "ERROR", "FAILED"
            details: Additional context about the operation

        Example:
            >>> logger = ADLogger("migration")
            >>> logger.log_operation(
            ...     operation="Batch User Move",
            ...     status="SUCCESS",
            ...     details="Moved 50 users to OU=Archived"
            ... )
        """
        # Generate timestamp in ISO format
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build log message with structured format
        message = f"[{timestamp}] {operation} - {status}"
        if details:
            message += f" | {details}"

        # Log at appropriate level based on status
        if status == "SUCCESS":
            self.logger.info(message)
        elif status == "WARNING":
            self.logger.warning(message)
        else:
            # ERROR or FAILED
            self.logger.error(message)

    def log_user_action(self, username: str, action: str, result: str):
        """
        Log user-specific actions with consistent formatting.

        This is a convenience method for logging actions that affect
        specific user accounts, making it easy to track who did what.

        Args:
            username: The user account that was modified
            action: The action performed (e.g., "CREATED", "DISABLED", "MOVED")
            result: Outcome details

        Example:
            >>> logger = ADLogger("user_mgmt")
            >>> logger.log_user_action("jsmith", "DISABLED", "Account disabled due to inactivity")
        """
        self.log_operation(f"User: {username}", result, action)

    def log_security_event(self, event_type: str, details: str):
        """
        Log security-relevant events with elevated importance.

        Security events are logged at WARNING level to ensure they're
        captured in monitoring systems and reviewed regularly.

        Security events to log:
        - Privileged account access
        - Failed login attempts
        - Password changes
        - Group membership modifications
        - Account lockouts

        Args:
            event_type: Type of security event
                       Examples: "PRIVILEGED_ACCESS", "FAILED_LOGIN", "LOCKOUT"
            details: Detailed information about the event

        Example:
            >>> logger = ADLogger("security")
            >>> logger.log_security_event(
            ...     "FAILED_LOGIN",
            ...     "5 failed attempts for user admin from IP 192.168.1.100"
            ... )
        """
        # Prefix message to make security events easily identifiable
        self.logger.warning(f"SECURITY: {event_type} - {details}")
