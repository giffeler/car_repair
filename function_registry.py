"""
function_registry.py

Manages registration, metadata exposure, and execution of OpenAI-callable functions
for the Car Repair MCP demonstrator with improved dependency injection and error handling.
"""

import time
from typing import Any, Awaitable, Callable, Dict, List, Protocol, Type

from pydantic import BaseModel, ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from exceptions import CarRepairError, ErrorCode, FunctionExecutionError
from logging_config import (
    get_logger,
    log_function_call,
    log_function_result,
    set_request_context,
)


class FunctionHandler(Protocol):
    """Protocol defining the interface for function handlers with dependency injection."""

    async def __call__(
        self, params: BaseModel, session: AsyncSession, user: Dict[str, Any]
    ) -> Any:
        """
        Execute the function with validated parameters and injected dependencies.

        Args:
            params: Validated Pydantic parameter model
            session: Async database session
            user: Authenticated user context

        Returns:
            Function execution result
        """
        ...


class FunctionDefinition(BaseModel):
    """
    Defines a callable function with type-safe parameter validation and dependency injection.
    """

    name: str
    description: str
    parameters_model: Type[BaseModel]
    handler: Callable[..., Awaitable[Any]]

    def openai_tool(self) -> Dict[str, Any]:
        """Generate OpenAI tool definition from function metadata."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_model.model_json_schema(),
            },
        }

    async def execute(
        self,
        params: Dict[str, Any],
        session: AsyncSession,
        user: Dict[str, Any],
    ) -> Any:
        """
        Execute the function with proper dependency injection and error handling.

        Args:
            params: Raw parameter dictionary from function call
            session: Async database session
            user: Authenticated user context

        Returns:
            Function execution result

        Raises:
            FunctionExecutionError: If function execution fails
            ValidationError: If parameter validation fails
        """
        logger = get_logger("function_registry")
        start_time = time.time()

        try:
            # Set function context for logging
            set_request_context(function_name_val=self.name)

            # Validate parameters
            try:
                validated_params = self.parameters_model(**params)
            except ValidationError as e:
                raise FunctionExecutionError(
                    function_name=self.name,
                    message=f"Parameter validation failed: {str(e)}",
                    error_code=ErrorCode.FUNCTION_PARAMETER_INVALID,
                    context={
                        "validation_errors": e.errors(),
                        "parameters": params,
                    },
                    cause=e,
                )

            # Log function call
            log_function_call(logger, self.name, params, user)

            # Execute handler with dependency injection
            result = await self.handler(validated_params, session, user)

            # Log successful execution
            execution_time_ms = (time.time() - start_time) * 1000
            result_type = (
                type(result).__name__ if result is not None else "None"
            )
            log_function_result(
                logger, self.name, True, execution_time_ms, result_type
            )

            return result

        except CarRepairError:
            # Re-raise structured errors without wrapping
            execution_time_ms = (time.time() - start_time) * 1000
            log_function_result(
                logger,
                self.name,
                False,
                execution_time_ms,
                error_code=getattr(CarRepairError, "error_code", "UNKNOWN"),
            )
            raise
        except Exception as e:
            # Wrap unexpected errors in structured format
            execution_time_ms = (time.time() - start_time) * 1000
            error = FunctionExecutionError(
                function_name=self.name,
                message=f"Unexpected error during function execution: {str(e)}",
                error_code=ErrorCode.FUNCTION_EXECUTION_FAILED,
                context={"parameters": params},
                cause=e,
            )
            log_function_result(
                logger,
                self.name,
                False,
                execution_time_ms,
                error_code=error.error_code.value,
            )
            raise error

    model_config = {"arbitrary_types_allowed": True}


class FunctionRegistry:
    """
    Registry for managing OpenAI-callable functions with type-safe execution and error handling.
    """

    def __init__(self) -> None:
        self.functions: Dict[str, FunctionDefinition] = {}
        self.logger = get_logger("function_registry")

    def register(self, func_def: FunctionDefinition) -> None:
        """
        Register a new function definition with validation.

        Args:
            func_def: Function definition to register

        Raises:
            FunctionExecutionError: If function name is already registered
        """
        if func_def.name in self.functions:
            error = FunctionExecutionError(
                function_name=func_def.name,
                message=f"Function '{func_def.name}' is already registered",
                error_code=ErrorCode.FUNCTION_REGISTRY_ERROR,
                context={"existing_functions": list(self.functions.keys())},
            )
            self.logger.error(
                "Function registration failed",
                function_name=func_def.name,
                error_code=error.error_code.value,
                reason="duplicate_name",
            )
            raise error

        self.functions[func_def.name] = func_def
        self.logger.info(
            "Function registered successfully",
            function_name=func_def.name,
            total_functions=len(self.functions),
        )

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get OpenAI tool definitions for all registered functions."""
        return [f.openai_tool() for f in self.functions.values()]

    async def execute_function(
        self,
        name: str,
        params: Dict[str, Any],
        session: AsyncSession,
        user: Dict[str, Any],
    ) -> Any:
        """
        Execute a registered function with comprehensive error handling.

        Args:
            name: Function name to execute
            params: Function parameters
            session: Async database session
            user: Authenticated user context

        Returns:
            Function execution result

        Raises:
            FunctionExecutionError: If function is not registered or execution fails
        """
        if name not in self.functions:
            error = FunctionExecutionError(
                function_name=name,
                message=f"Function '{name}' is not registered",
                error_code=ErrorCode.FUNCTION_NOT_FOUND,
                context={
                    "requested_function": name,
                    "available_functions": list(self.functions.keys()),
                },
            )
            self.logger.error(
                "Function execution failed",
                function_name=name,
                error_code=error.error_code.value,
                reason="function_not_found",
            )
            raise error

        func_def = self.functions[name]
        return await func_def.execute(params, session, user)

    def list_functions(self) -> List[Dict[str, Any]]:
        """Get metadata for all registered functions."""
        return [
            {
                "name": name,
                "description": func_def.description,
                "parameters": func_def.parameters_model.model_json_schema(),
            }
            for name, func_def in self.functions.items()
        ]

    def get_function_count(self) -> int:
        """Get total number of registered functions."""
        return len(self.functions)

    def is_function_registered(self, name: str) -> bool:
        """Check if a function is registered."""
        return name in self.functions


# Global instance
function_registry = FunctionRegistry()
