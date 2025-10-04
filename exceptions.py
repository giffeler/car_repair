"""
exceptions.py

Custom exception hierarchy for the Car Repair MCP demonstrator.
Provides structured error handling with error codes and contextual information.
"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Standardized error codes for the car repair system."""

    # Function execution errors
    FUNCTION_NOT_FOUND = "FUNC_001"
    FUNCTION_EXECUTION_FAILED = "FUNC_002"
    FUNCTION_PARAMETER_INVALID = "FUNC_003"
    FUNCTION_REGISTRY_ERROR = "FUNC_004"

    # Database errors
    DATABASE_CONNECTION_FAILED = "DB_001"
    DATABASE_OPERATION_FAILED = "DB_002"
    DATABASE_TRANSACTION_FAILED = "DB_003"
    ENTITY_NOT_FOUND = "DB_004"
    ENTITY_VALIDATION_FAILED = "DB_005"

    # Authentication and authorization
    AUTHENTICATION_FAILED = "AUTH_001"
    AUTHORIZATION_FAILED = "AUTH_002"
    INVALID_TOKEN = "AUTH_003"

    # External service errors
    OPENAI_API_ERROR = "EXT_001"
    OPENAI_RATE_LIMITED = "EXT_002"
    OPENAI_INVALID_REQUEST = "EXT_003"

    # Business logic errors
    CUSTOMER_NOT_FOUND = "BIZ_001"
    APPOINTMENT_NOT_FOUND = "BIZ_002"
    INVALID_APPOINTMENT_STATUS = "BIZ_003"
    SERVICE_ANALYSIS_FAILED = "BIZ_004"

    # System errors
    CONFIGURATION_ERROR = "SYS_001"
    INTERNAL_SERVER_ERROR = "SYS_002"
    REQUEST_TIMEOUT = "SYS_003"


class CarRepairError(Exception):
    """
    Base exception class for the car repair system.

    Provides structured error handling with error codes, contextual information,
    and proper logging integration.
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """
        Initialize a structured error.

        Args:
            message: Human-readable error description
            error_code: Standardized error code for categorization
            context: Additional context information for debugging
            cause: Original exception that caused this error (if any)
        """
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause

        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "context": self.context,
            "type": self.__class__.__name__,
        }

    def __str__(self) -> str:
        """String representation with error code."""
        return f"[{self.error_code.value}] {self.message}"


class FunctionExecutionError(CarRepairError):
    """Raised when function call execution fails."""

    def __init__(
        self,
        function_name: str,
        message: str,
        error_code: ErrorCode = ErrorCode.FUNCTION_EXECUTION_FAILED,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = context or {}
        context["function_name"] = function_name
        super().__init__(message, error_code, context, cause)


class DatabaseOperationError(CarRepairError):
    """Raised when database operations fail."""

    def __init__(
        self,
        operation: str,
        message: str,
        error_code: ErrorCode = ErrorCode.DATABASE_OPERATION_FAILED,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = context or {}
        context["operation"] = operation
        super().__init__(message, error_code, context, cause)


class EntityNotFoundError(CarRepairError):
    """Raised when a requested entity is not found."""

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        message = f"{entity_type} with ID {entity_id} not found"
        context = context or {}
        context.update(
            {"entity_type": entity_type, "entity_id": str(entity_id)}
        )
        super().__init__(message, ErrorCode.ENTITY_NOT_FOUND, context)


class AuthenticationError(CarRepairError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: ErrorCode = ErrorCode.AUTHENTICATION_FAILED,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code, context)


class ExternalServiceError(CarRepairError):
    """Raised when external service calls fail."""

    def __init__(
        self,
        service_name: str,
        message: str,
        error_code: ErrorCode = ErrorCode.OPENAI_API_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        context = context or {}
        context["service_name"] = service_name
        super().__init__(message, error_code, context, cause)


class ValidationError(CarRepairError):
    """Raised when data validation fails."""

    def __init__(
        self,
        field: str,
        value: Any,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        context = context or {}
        context.update({"field": field, "invalid_value": str(value)})
        super().__init__(message, ErrorCode.ENTITY_VALIDATION_FAILED, context)


def handle_database_error(
    operation: str, cause: Exception
) -> DatabaseOperationError:
    """
    Convert database exceptions to structured errors.

    Args:
        operation: Database operation that failed
        cause: Original exception

    Returns:
        Structured database error
    """
    error_message = f"Database operation '{operation}' failed: {str(cause)}"

    # Map specific database errors to appropriate error codes
    error_code = ErrorCode.DATABASE_OPERATION_FAILED
    if "connection" in str(cause).lower():
        error_code = ErrorCode.DATABASE_CONNECTION_FAILED
    elif "transaction" in str(cause).lower():
        error_code = ErrorCode.DATABASE_TRANSACTION_FAILED

    return DatabaseOperationError(
        operation=operation,
        message=error_message,
        error_code=error_code,
        cause=cause,
    )


def handle_external_service_error(
    service_name: str, cause: Exception
) -> ExternalServiceError:
    """
    Convert external service exceptions to structured errors.

    Args:
        service_name: Name of the external service
        cause: Original exception

    Returns:
        Structured external service error
    """
    error_message = f"{service_name} service error: {str(cause)}"

    # Map specific service errors to appropriate error codes
    error_code = ErrorCode.OPENAI_API_ERROR
    cause_str = str(cause).lower()

    if "rate" in cause_str and "limit" in cause_str:
        error_code = ErrorCode.OPENAI_RATE_LIMITED
    elif "invalid" in cause_str or "bad request" in cause_str:
        error_code = ErrorCode.OPENAI_INVALID_REQUEST

    return ExternalServiceError(
        service_name=service_name,
        message=error_message,
        error_code=error_code,
        cause=cause,
    )
