"""
logging_config.py

Structured logging configuration using Python's standard library for the Car Repair MCP demonstrator.
Provides request correlation, contextual logging, and JSON output without external dependencies.
"""

import json
import logging
import os
import uuid
from collections.abc import MutableMapping
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Context variables for request correlation
request_id: ContextVar[str] = ContextVar("request_id", default="")
user_id: ContextVar[str] = ContextVar("user_id", default="")
function_name: ContextVar[str] = ContextVar("function_name", default="")


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs with context information."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON with contextual information.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Build base log entry with flexible typing for nested structures
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "car-repair-mcp",
            "version": "1.1.0",
        }

        # Add context variables
        if request_id.get():
            log_entry["request_id"] = request_id.get()

        if user_id.get():
            log_entry["user_id"] = user_id.get()

        if function_name.get():
            log_entry["function_name"] = function_name.get()

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        # Add exception information
        if record.exc_info:
            log_entry["exception"] = {
                "type": (
                    record.exc_info[0].__name__ if record.exc_info[0] else None
                ),
                "message": (
                    str(record.exc_info[1]) if record.exc_info[1] else None
                ),
                "module": (
                    record.exc_info[0].__module__
                    if record.exc_info[0]
                    else None
                ),
            }

        # Add structured error information if available
        if hasattr(record, "error_code"):
            log_entry["error_code"] = record.error_code

        if hasattr(record, "error_context"):
            log_entry["error_context"] = record.error_context

        return json.dumps(log_entry, default=str)


class ContextLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Logger adapter that automatically includes contextual information in log records."""

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, Dict[str, Any]]:
        """
        Process log message and kwargs to include contextual information.

        Args:
            msg: Log message
            kwargs: Keyword arguments

        Returns:
            Processed message and kwargs
        """
        # Extract extra fields from kwargs
        extra_fields = kwargs.pop("extra_fields", {})

        # Add any additional kwargs as extra fields
        for key, value in list(kwargs.items()):
            if key not in ("exc_info", "stack_info", "stacklevel", "extra"):
                extra_fields[key] = kwargs.pop(key)

        # Add extra fields to the record
        if extra_fields:
            kwargs.setdefault("extra", {})["extra_fields"] = extra_fields

        return msg, dict(kwargs)


def configure_logging() -> ContextLoggerAdapter:
    """
    Configure structured logging for the application using standard library.

    Returns:
        Configured context-aware logger adapter
    """
    # Determine log level and format from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))

    # Set formatter based on debug mode
    if debug_mode:
        # Simple formatter for development
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # Structured JSON formatter for production
        formatter = StructuredFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Create application logger
    app_logger = logging.getLogger("car_repair_mcp")

    return ContextLoggerAdapter(app_logger, {})


def get_logger(name: str) -> ContextLoggerAdapter:
    """
    Get a configured logger instance with context support.

    Args:
        name: Logger name (typically module name)

    Returns:
        Configured context-aware logger adapter
    """
    logger = logging.getLogger(name)
    return ContextLoggerAdapter(logger, {})


def set_request_context(
    req_id: Optional[str] = None,
    user_id_val: Optional[str] = None,
    function_name_val: Optional[str] = None,
) -> str:
    """
    Set request context for correlation logging.

    Args:
        req_id: Request ID (generates UUID if not provided)
        user_id_val: User ID for the request
        function_name_val: Function name being executed

    Returns:
        Request ID that was set
    """
    if req_id is None:
        req_id = str(uuid.uuid4())

    request_id.set(req_id)

    if user_id_val:
        user_id.set(user_id_val)

    if function_name_val:
        function_name.set(function_name_val)

    return req_id


def clear_request_context() -> None:
    """Clear request context variables."""
    request_id.set("")
    user_id.set("")
    function_name.set("")


def log_function_call(
    logger: ContextLoggerAdapter,
    function_name_val: str,
    parameters: Dict[str, Any],
    user_context: Dict[str, Any],
) -> None:
    """
    Log function call with structured information.

    Args:
        logger: Context-aware logger instance
        function_name_val: Name of function being called
        parameters: Function parameters
        user_context: User context information
    """
    logger.info(
        "Function call initiated",
        extra={
            "function_name": function_name_val,
            "parameters": parameters,
            "user_token": (
                user_context.get("token", "unknown")[:10] + "..."
                if user_context.get("token")
                else None
            ),
            "parameter_count": len(parameters),
        },
    )


def log_function_result(
    logger: ContextLoggerAdapter,
    function_name_val: str,
    success: bool,
    execution_time_ms: float,
    result_type: Optional[str] = None,
    error_code: Optional[str] = None,
) -> None:
    """
    Log function execution result with metrics.

    Args:
        logger: Context-aware logger instance
        function_name_val: Name of function that was executed
        success: Whether function execution succeeded
        execution_time_ms: Execution time in milliseconds
        result_type: Type of result returned (if successful)
        error_code: Error code (if failed)
    """
    log_data = {
        "function_name": function_name_val,
        "execution_time_ms": execution_time_ms,
        "status": "success" if success else "failed",
    }
    if result_type:
        log_data["result_type"] = result_type
    if error_code:
        log_data["error_code"] = error_code

    if success:
        logger.info("Function call completed successfully", extra=log_data)
    else:
        logger.error("Function call failed", extra=log_data)


def log_database_operation(
    logger: ContextLoggerAdapter,
    operation: str,
    entity_type: str,
    entity_id: Optional[Any] = None,
    success: bool = True,
    execution_time_ms: Optional[float] = None,
) -> None:
    """
    Log database operations with structured information.

    Args:
        logger: Context-aware logger instance
        operation: Database operation (select, insert, update, delete)
        entity_type: Type of entity being operated on
        entity_id: ID of specific entity (if applicable)
        success: Whether operation succeeded
        execution_time_ms: Operation execution time
    """
    log_data = {
        "database_operation": operation,
        "entity_type": entity_type,
        "success": success,
    }

    if entity_id is not None:
        log_data["entity_id"] = str(entity_id)

    if execution_time_ms is not None:
        log_data["execution_time_ms"] = execution_time_ms

    if success:
        logger.info("Database operation completed", extra=log_data)
    else:
        logger.error("Database operation failed", extra=log_data)


# Global logger instance
logger = configure_logging()
