"""
process_function_calls.py

Executes OpenAI tool calls against registered handlers with comprehensive error recovery,
retry logic, and structured logging for the Car Repair MCP demonstrator.
Refactored to deprecate legacy function_call support.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from openai.types.chat.chat_completion import ChatCompletion
from sqlmodel.ext.asyncio.session import AsyncSession

from exceptions import (
    CarRepairError,
    DatabaseOperationError,
    ErrorCode,
    FunctionExecutionError,
)
from function_registry import FunctionRegistry
from logging_config import get_logger, set_request_context
from metrics import (
    FUNCTION_CALL_COUNT,  # Assuming metrics.py exists
    FUNCTION_RETRY_COUNT,
)


class FunctionCallResult:
    """Encapsulates function call execution results with comprehensive error context."""

    def __init__(
        self,
        tool_call_id: Optional[str],
        function_name: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        retry_count: int = 0,
    ):
        self.tool_call_id = tool_call_id
        self.function_name = function_name
        self.success = success
        self.result = result
        self.error = error
        self.error_code = error_code
        self.execution_time_ms = execution_time_ms
        self.retry_count = retry_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API response."""
        base_dict: Dict[str, Any] = {
            "name": self.function_name,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "retry_count": self.retry_count,
        }

        if self.tool_call_id:
            base_dict["tool_call_id"] = self.tool_call_id

        if self.success:
            base_dict["result"] = self.result
        else:
            base_dict["error"] = self.error
            if self.error_code:
                base_dict["error_code"] = self.error_code

        return base_dict


class FunctionCallProcessor:
    """Processes OpenAI function calls with advanced error recovery and retry logic."""

    def __init__(
        self,
        registry: FunctionRegistry,
        max_retries: int = 2,
        retry_delay_ms: int = 100,
        timeout_seconds: int = 30,
    ):
        self.registry = registry
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms
        self.timeout_seconds = timeout_seconds
        self.logger = get_logger("function_call_processor")

    async def execute_single_function(
        self,
        function_name: str,
        parameters: Dict[str, Any],
        session: AsyncSession,
        user: Dict[str, Any],
        tool_call_id: Optional[str] = None,
    ) -> FunctionCallResult:
        """Execute a single function call with retry logic and comprehensive error handling."""
        start_time = time.time()
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                set_request_context(function_name_val=function_name)

                if attempt > 0:
                    self.logger.info(
                        "Retrying function call",
                        extra={
                            "function_name": function_name,
                            "attempt": attempt + 1,
                            "max_attempts": self.max_retries + 1,
                            "tool_call_id": tool_call_id,
                        },
                    )
                    await asyncio.sleep(self.retry_delay_ms / 1000.0)

                # Execute function with timeout
                result = await asyncio.wait_for(
                    self.registry.execute_function(
                        function_name, parameters, session, user
                    ),
                    timeout=self.timeout_seconds,
                )

                execution_time_ms = (time.time() - start_time) * 1000

                self.logger.info(
                    "Function call completed successfully",
                    extra={
                        "function_name": function_name,
                        "execution_time_ms": execution_time_ms,
                        "retry_count": attempt,
                        "tool_call_id": tool_call_id,
                    },
                )

                FUNCTION_CALL_COUNT.labels(
                    function_name=function_name, success=True
                ).inc()
                FUNCTION_RETRY_COUNT.labels(
                    function_name=function_name
                ).observe(attempt)

                return FunctionCallResult(
                    tool_call_id=tool_call_id,
                    function_name=function_name,
                    success=True,
                    result=result,
                    execution_time_ms=execution_time_ms,
                    retry_count=attempt,
                )

            except asyncio.TimeoutError as e:
                last_error = e
                execution_time_ms = (time.time() - start_time) * 1000

                self.logger.warning(
                    "Function call timeout",
                    extra={
                        "function_name": function_name,
                        "timeout_seconds": self.timeout_seconds,
                        "execution_time_ms": execution_time_ms,
                        "attempt": attempt + 1,
                        "tool_call_id": tool_call_id,
                    },
                )

                if attempt >= self.max_retries:
                    break

            except DatabaseOperationError as e:
                last_error = e
                execution_time_ms = (time.time() - start_time) * 1000

                self.logger.error(
                    "Database error in function call",
                    extra={
                        "function_name": function_name,
                        "error_code": e.error_code.value,
                        "execution_time_ms": execution_time_ms,
                        "attempt": attempt + 1,
                        "tool_call_id": tool_call_id,
                    },
                    exc_info=True,
                )

                if attempt >= self.max_retries:
                    break

            except CarRepairError as e:
                execution_time_ms = (time.time() - start_time) * 1000

                self.logger.error(
                    "Business logic error in function call",
                    extra={
                        "function_name": function_name,
                        "error_code": e.error_code.value,
                        "execution_time_ms": execution_time_ms,
                        "tool_call_id": tool_call_id,
                        "error_context": e.context,
                    },
                )

                FUNCTION_CALL_COUNT.labels(
                    function_name=function_name, success=False
                ).inc()
                FUNCTION_RETRY_COUNT.labels(
                    function_name=function_name
                ).observe(attempt)

                return FunctionCallResult(
                    tool_call_id=tool_call_id,
                    function_name=function_name,
                    success=False,
                    error=str(e),
                    error_code=e.error_code.value,
                    execution_time_ms=execution_time_ms,
                    retry_count=attempt,
                )

            except Exception as e:
                last_error = e
                execution_time_ms = (time.time() - start_time) * 1000

                self.logger.error(
                    "Unexpected error in function call",
                    extra={
                        "function_name": function_name,
                        "execution_time_ms": execution_time_ms,
                        "attempt": attempt + 1,
                        "tool_call_id": tool_call_id,
                    },
                    exc_info=True,
                )

                if attempt >= self.max_retries:
                    break

        # All retries exhausted
        execution_time_ms = (time.time() - start_time) * 1000
        error_message = f"Function call failed after {self.max_retries + 1} attempts: {str(last_error)}"
        error_code = ErrorCode.FUNCTION_EXECUTION_FAILED.value

        if isinstance(last_error, asyncio.TimeoutError):
            error_code = ErrorCode.REQUEST_TIMEOUT.value
            error_message = (
                f"Function call timed out after {self.timeout_seconds} seconds"
            )

        FUNCTION_CALL_COUNT.labels(
            function_name=function_name, success=False
        ).inc()
        FUNCTION_RETRY_COUNT.labels(function_name=function_name).observe(
            self.max_retries
        )

        return FunctionCallResult(
            tool_call_id=tool_call_id,
            function_name=function_name,
            success=False,
            error=error_message,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            retry_count=self.max_retries,
        )


async def process_function_calls(
    response: ChatCompletion,
    registry: FunctionRegistry,
    session: AsyncSession,
    user: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Process all function calls from OpenAI response with advanced error recovery."""
    processor = FunctionCallProcessor(registry)
    results: List[Dict[str, Any]] = []

    processor.logger.info(
        "Processing function calls from OpenAI response",
        extra={"choice_count": len(response.choices)},
    )

    for choice_idx, choice in enumerate(response.choices):
        message = choice.message

        # Process modern tool_calls format (OpenAI API v1.1+)
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.type == "function":
                    result = await _process_tool_call(
                        processor, tool_call, session, user
                    )
                    results.append(result.to_dict())

    # Log processing summary
    successful_calls = sum(1 for r in results if r.get("success", False))
    total_calls = len(results)

    processor.logger.info(
        "Function call processing completed",
        extra={
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": total_calls - successful_calls,
            "success_rate": (
                f"{(successful_calls/total_calls*100):.1f}%"
                if total_calls > 0
                else "N/A"
            ),
        },
    )

    return results


async def _process_tool_call(
    processor: FunctionCallProcessor,
    tool_call: Any,
    session: AsyncSession,
    user: Dict[str, Any],
) -> FunctionCallResult:
    """Process an OpenAI tool call with structured error handling."""
    fn_name = tool_call.function.name
    fn_args = tool_call.function.arguments

    try:
        # Parse JSON arguments with validation
        if isinstance(fn_args, str):
            parsed_args = json.loads(fn_args)
        else:
            parsed_args = fn_args or {}

        # Validate argument structure
        if not isinstance(parsed_args, dict):
            raise FunctionExecutionError(
                function_name=fn_name,
                message="Function arguments must be a dictionary",
                error_code=ErrorCode.FUNCTION_PARAMETER_INVALID,
                context={"received_type": type(parsed_args).__name__},
            )

        return await processor.execute_single_function(
            fn_name, parsed_args, session, user, tool_call.id
        )

    except json.JSONDecodeError as e:
        processor.logger.error(
            "JSON parsing failed for tool call",
            extra={
                "function_name": fn_name,
                "tool_call_id": tool_call.id,
                "arguments": str(fn_args)[:200],
                "error": str(e),
            },
        )

        return FunctionCallResult(
            tool_call_id=tool_call.id,
            function_name=fn_name,
            success=False,
            error=f"Invalid JSON arguments: {str(e)}",
            error_code=ErrorCode.FUNCTION_PARAMETER_INVALID.value,
        )


def enhance_openai_response(
    original_response: ChatCompletion, function_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Enhance OpenAI response with comprehensive function call metadata and metrics."""
    response_dict = original_response.model_dump()

    # Add function results as metadata
    response_dict["function_call_results"] = function_results

    # Calculate comprehensive metrics
    if function_results:
        successful_calls = [
            r for r in function_results if r.get("success", False)
        ]
        failed_calls = [
            r for r in function_results if not r.get("success", True)
        ]

        # Calculate timing metrics
        execution_times = [
            r.get("execution_time_ms", 0)
            for r in function_results
            if r.get("execution_time_ms")
        ]
        total_execution_time = sum(execution_times)
        avg_execution_time = (
            total_execution_time / len(execution_times)
            if execution_times
            else 0
        )

        # Calculate retry metrics
        total_retries = sum(r.get("retry_count", 0) for r in function_results)

        # Group errors by code for analysis
        error_codes: Dict[str, int] = {}
        for result in failed_calls:
            error_code = result.get("error_code", "UNKNOWN")
            error_codes[error_code] = error_codes.get(error_code, 0) + 1

        response_dict["function_call_summary"] = {
            "total_calls": len(function_results),
            "successful": len(successful_calls),
            "failed": len(failed_calls),
            "success_rate": f"{(len(successful_calls)/len(function_results)*100):.1f}%",
            "functions_called": [r["name"] for r in function_results],
            "execution_metrics": {
                "total_execution_time_ms": total_execution_time,
                "average_execution_time_ms": round(avg_execution_time, 2),
                "max_execution_time_ms": (
                    max(execution_times) if execution_times else 0
                ),
                "total_retries": total_retries,
            },
            "error_summary": error_codes if error_codes else None,
        }

    return response_dict


def get_function_call_statistics(
    function_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate detailed statistics for function call analysis and monitoring."""
    if not function_results:
        return {"total_calls": 0, "analysis_available": False}

    # Basic counts
    total_calls = len(function_results)
    successful_calls = [r for r in function_results if r.get("success", False)]
    failed_calls = [r for r in function_results if not r.get("success", True)]

    # Performance metrics
    execution_times = [
        r.get("execution_time_ms", 0)
        for r in function_results
        if r.get("execution_time_ms")
    ]
    retry_counts = [r.get("retry_count", 0) for r in function_results]

    # Function usage patterns
    function_usage: Dict[str, Dict[str, int]] = {}
    for result in function_results:
        func_name = result.get("name", "unknown")
        if func_name not in function_usage:
            function_usage[func_name] = {
                "calls": 0,
                "successes": 0,
                "failures": 0,
            }

        function_usage[func_name]["calls"] += 1
        if result.get("success", False):
            function_usage[func_name]["successes"] += 1
        else:
            function_usage[func_name]["failures"] += 1

    # Error analysis
    error_patterns: Dict[str, Dict[str, Any]] = {}
    for result in failed_calls:
        error_code = result.get("error_code", "UNKNOWN")
        function_name = result.get("name", "unknown")

        if error_code not in error_patterns:
            error_patterns[error_code] = {"count": 0, "functions": set()}

        error_patterns[error_code]["count"] += 1
        error_patterns[error_code]["functions"].add(function_name)

    # Convert sets to lists for JSON serialization
    for pattern in error_patterns.values():
        pattern["functions"] = list(pattern["functions"])

    return {
        "total_calls": total_calls,
        "success_rate": (
            len(successful_calls) / total_calls if total_calls > 0 else 0
        ),
        "performance_metrics": {
            "avg_execution_time_ms": (
                sum(execution_times) / len(execution_times)
                if execution_times
                else 0
            ),
            "max_execution_time_ms": (
                max(execution_times) if execution_times else 0
            ),
            "min_execution_time_ms": (
                min(execution_times) if execution_times else 0
            ),
            "total_retries": sum(retry_counts),
            "avg_retries_per_call": (
                sum(retry_counts) / total_calls if total_calls > 0 else 0
            ),
        },
        "function_usage": function_usage,
        "error_patterns": error_patterns,
        "analysis_available": True,
    }
