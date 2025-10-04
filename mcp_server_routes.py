"""
mcp_server_routes.py

FastAPI routes for the Car Repair MCP demonstrator, providing OpenAI-compatible chat completions,
model listing, function registry, and health checks with enterprise-grade error handling and monitoring.
"""

import json
import os
import uuid
from datetime import datetime
from typing import (
    cast,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    Union,
    Callable,
    Awaitable,
)
import asyncio

import backoff
import openai
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from openai import RateLimitError
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
    ChatCompletionNamedToolChoiceParam,
)
from openai._types import NOT_GIVEN, NotGiven
from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_async_session
from exceptions import (
    AuthenticationError,
    CarRepairError,
    ErrorCode,
    # ExternalServiceError,
    handle_external_service_error,
)
from function_registry import function_registry
from logging_config import (
    clear_request_context,
    get_logger,
    set_request_context,
)
from metrics import ERROR_COUNT, REQUEST_COUNT, SYSTEM_HEALTH
from process_function_calls import (
    enhance_openai_response,
    get_function_call_statistics,
    process_function_calls,
)
from session_manager import get_current_user

mcp_router = APIRouter()
logger = get_logger("mcp_server")
limiter = Limiter(key_func=get_remote_address)
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"


class ErrorResponse(BaseModel):
    """Standardized error response structure for API endpoints."""

    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None


class ToolCall(BaseModel):
    """OpenAI tool call structure with validation."""

    id: str = Field(..., description="Unique identifier for the tool call")
    type: Literal["function"] = Field(
        default="function", description="Type of tool call"
    )
    function: Dict[str, Any] = Field(..., description="Function call details")


class Message(BaseModel):
    """OpenAI message structure with comprehensive validation."""

    role: Literal["system", "user", "assistant", "tool"] = Field(
        ..., description="Message role"
    )
    content: Optional[str] = Field(None, description="Message content")
    tool_calls: Optional[List[ToolCall]] = Field(
        None, description="Tool calls in the message"
    )
    tool_call_id: Optional[str] = Field(
        None, description="ID of the tool call this message responds to"
    )
    name: Optional[str] = Field(
        None, description="Name of the function that was called"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "role": "user",
                    "content": "How long will brake service take for customer john@example.com?",
                }
            ]
        }
    )


class ChatCompletionRequest(BaseModel):
    """OpenAI chat completion request with comprehensive validation and defaults."""

    model: str = Field(..., description="Model to use for completion")
    messages: List[Message] = Field(
        ..., min_length=1, description="List of messages in the conversation"
    )
    temperature: float = Field(
        default=0.2, ge=0.0, le=2.0, description="Sampling temperature"
    )
    tools: Optional[List[ChatCompletionToolParam]] = Field(
        None, description="Tools available for function calling"
    )
    tool_choice: Optional[
        Union[
            Literal["none", "auto", "required"],
            ChatCompletionNamedToolChoiceParam,
        ]
    ] = Field(None, description="Tool choice strategy")
    max_tokens: Optional[int] = Field(
        default=None, ge=1, le=4096, description="Maximum tokens to generate"
    )
    stream: bool = Field(
        default=False, description="Whether to stream the response"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "model": "gpt-4.1-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a car repair assistant.",
                        },
                        {
                            "role": "user",
                            "content": "Check customer john@example.com status",
                        },
                    ],
                    "temperature": 0.2,
                }
            ]
        }
    )


class OpenAIParams(TypedDict):
    """Typed dictionary for OpenAI chat completion parameters."""

    model: str
    messages: List[ChatCompletionMessageParam]
    temperature: float
    tools: Union[List[ChatCompletionToolParam], NotGiven]
    tool_choice: Union[
        Literal["none", "auto", "required"],
        ChatCompletionNamedToolChoiceParam,
        NotGiven,
    ]
    max_tokens: Union[int, NotGiven]
    stream: Literal[False]


def create_error_response(
    error: CarRepairError,
    request_id: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> JSONResponse:
    """
    Create standardized error response from CarRepairError.

    Args:
        error: Structured error object
        request_id: Request correlation ID
        status_code: HTTP status code to return

    Returns:
        JSONResponse: Formatted error response
    """
    response_data = ErrorResponse(
        error=error.message,
        error_code=error.error_code.value,
        details=error.context,
        request_id=request_id,
        timestamp=datetime.utcnow().isoformat(),
    )

    logger.error(
        "API error response generated",
        extra={
            "error_code": error.error_code.value,
            "status_code": status_code,
            "request_id": request_id,
            "error_context": error.context,
        },
    )

    return JSONResponse(
        status_code=status_code, content=response_data.model_dump()
    )


def map_error_to_http_status(error: CarRepairError) -> int:
    """
    Map structured error codes to appropriate HTTP status codes.

    Args:
        error: Structured error object

    Returns:
        int: Appropriate HTTP status code
    """
    status_map = {
        ErrorCode.AUTHENTICATION_FAILED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.AUTHORIZATION_FAILED: status.HTTP_403_FORBIDDEN,
        ErrorCode.INVALID_TOKEN: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.ENTITY_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.CUSTOMER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.APPOINTMENT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.FUNCTION_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.ENTITY_VALIDATION_FAILED: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.FUNCTION_PARAMETER_INVALID: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.INVALID_APPOINTMENT_STATUS: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ErrorCode.REQUEST_TIMEOUT: status.HTTP_408_REQUEST_TIMEOUT,
        ErrorCode.OPENAI_RATE_LIMITED: status.HTTP_429_TOO_MANY_REQUESTS,
        ErrorCode.OPENAI_INVALID_REQUEST: status.HTTP_400_BAD_REQUEST,
        ErrorCode.DATABASE_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
        ErrorCode.OPENAI_API_ERROR: status.HTTP_502_BAD_GATEWAY,
    }

    return status_map.get(
        error.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
    )


async def _make_openai_call(params: OpenAIParams) -> ChatCompletion:
    """
    Make an OpenAI chat completion call with rate limit retry handling.

    Args:
        params: OpenAI call parameters

    Returns:
        ChatCompletion: OpenAI response

    Raises:
        RateLimitError: If retries are exhausted
    """

    @backoff.on_exception(
        backoff.expo,
        RateLimitError,
        max_tries=3,
        max_time=60,
        jitter=backoff.full_jitter,
    )
    def openai_call() -> ChatCompletion:
        return openai.chat.completions.create(**params)

    return await asyncio.to_thread(openai_call)


async def _process_function_calls(
    response: ChatCompletion,
    tools: Union[List[ChatCompletionToolParam], NotGiven],
    request: ChatCompletionRequest,
    db: AsyncSession,
    user: Dict[str, Any],
    request_id: str,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Process function calls from initial OpenAI response and generate final response.

    Args:
        response: Initial OpenAI response
        tools: Available tools
        request: Original chat completion request
        db: Database session
        user: User context
        request_id: Request ID

    Returns:
        tuple: Final enhanced response and function results
    """
    function_results: List[Dict[str, Any]] = []
    messages: List[ChatCompletionMessageParam] = [
        cast(ChatCompletionMessageParam, msg.model_dump(exclude_none=True))
        for msg in request.messages
    ]

    if tools is not NOT_GIVEN and response.choices:
        function_results = await process_function_calls(
            response, function_registry, db, user
        )

        if function_results:
            logger.info(
                "Function calls executed, continuing conversation",
                extra={
                    "request_id": request_id,
                    "function_call_count": len(function_results),
                    "successful_calls": sum(
                        1 for r in function_results if r.get("success", False)
                    ),
                },
            )

            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": response.choices[0].message.content,
                "tool_calls": [],
            }

            if (
                hasattr(response.choices[0].message, "tool_calls")
                and response.choices[0].message.tool_calls
            ):
                assistant_message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response.choices[0].message.tool_calls
                ]

            messages.append(cast(ChatCompletionMessageParam, assistant_message))

            for func_result in function_results:
                result_content = func_result.get(
                    "result", func_result.get("error", "Unknown error")
                )

                if hasattr(result_content, "model_dump"):
                    content_str = json.dumps(
                        result_content.model_dump(mode="json")
                    )
                elif (
                    isinstance(result_content, list)
                    and result_content
                    and hasattr(result_content[0], "model_dump")
                ):
                    content_str = json.dumps(
                        [
                            item.model_dump(mode="json")
                            for item in result_content
                        ]
                    )
                elif (
                    isinstance(
                        result_content,
                        (dict, list, str, int, float, bool),
                    )
                    or result_content is None
                ):
                    content_str = json.dumps(result_content)
                else:
                    content_str = str(result_content)

                tool_message: Dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": func_result.get(
                        "tool_call_id", f"call_{func_result['name']}"
                    ),
                    "name": func_result["name"],
                    "content": content_str,
                }
                messages.append(cast(ChatCompletionMessageParam, tool_message))

            final_params: OpenAIParams = {
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature,
                "tools": NOT_GIVEN,
                "tool_choice": NOT_GIVEN,
                "max_tokens": (
                    request.max_tokens
                    if request.max_tokens is not None
                    else NOT_GIVEN
                ),
                "stream": False,
            }

            logger.debug(
                "Making follow-up OpenAI call for final response",
                extra={
                    "request_id": request_id,
                    "message_count": len(messages),
                },
            )

            final_response = await _make_openai_call(final_params)

            enhanced_response = enhance_openai_response(
                final_response, function_results
            )
            enhanced_response["initial_response"] = response.model_dump()
            enhanced_response["conversation_messages"] = messages
            enhanced_response["request_id"] = request_id
            enhanced_response["function_call_statistics"] = (
                get_function_call_statistics(function_results)
            )

            logger.info(
                "Chat completion with function calls completed successfully",
                extra={
                    "request_id": request_id,
                    "total_tokens": enhanced_response.get("usage", {}).get(
                        "total_tokens", 0
                    ),
                    "function_success_rate": enhanced_response[
                        "function_call_statistics"
                    ].get("success_rate", 0),
                },
            )

            return enhanced_response, function_results

    return response.model_dump(), function_results


def _handle_exception(
    exc: Exception,
    request_id: str,
    method: str = "POST",
    endpoint: str = "/v1/chat/completions",
) -> JSONResponse:
    """
    Handle exceptions uniformly and return structured error responses.

    Args:
        exc: Raised exception
        request_id: Request ID
        method: HTTP method
        endpoint: Endpoint path

    Returns:
        JSONResponse: Error response
    """
    if isinstance(exc, PydanticValidationError):
        validation_error = CarRepairError(
            message=f"Request validation failed: {str(exc)}",
            error_code=ErrorCode.ENTITY_VALIDATION_FAILED,
            context={"validation_errors": exc.errors()},
        )
        http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        ERROR_COUNT.labels(error_code=validation_error.error_code.value).inc()
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=http_status,
        ).inc()
        return create_error_response(validation_error, request_id, http_status)

    elif isinstance(exc, AuthenticationError):
        http_status = map_error_to_http_status(exc)
        ERROR_COUNT.labels(error_code=exc.error_code.value).inc()
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=http_status,
        ).inc()
        return create_error_response(exc, request_id, http_status)

    elif isinstance(exc, CarRepairError):
        http_status = map_error_to_http_status(exc)
        ERROR_COUNT.labels(error_code=exc.error_code.value).inc()
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=http_status,
        ).inc()
        return create_error_response(exc, request_id, http_status)

    elif isinstance(exc, openai.OpenAIError):
        openai_error = handle_external_service_error("OpenAI", exc)
        http_status = map_error_to_http_status(openai_error)
        ERROR_COUNT.labels(error_code=openai_error.error_code.value).inc()
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=http_status,
        ).inc()
        return create_error_response(openai_error, request_id, http_status)

    else:
        logger.exception(
            "Unexpected error in chat completions endpoint",
            extra={"request_id": request_id, "error": str(exc)},
        )
        unexpected_error = CarRepairError(
            message="Internal server error occurred",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            context={"original_error": str(exc)},
            cause=exc,
        )
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        ERROR_COUNT.labels(error_code=unexpected_error.error_code.value).inc()
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=http_status,
        ).inc()
        return create_error_response(unexpected_error, request_id, http_status)


@mcp_router.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Union[Dict[str, Any], JSONResponse]:
    """
    OpenAI-compatible chat completions endpoint with comprehensive error handling and function calling.

    Provides enterprise-grade reliability with request correlation, structured error responses,
    and detailed monitoring for production AI applications.
    Bypasses rate limiting in debug mode for testing.

    Args:
        request: Chat completion request parameters
        http_request: FastAPI request object for headers and metadata
        db: Database session for function execution
        user: Authenticated user context

    Returns:
        Enhanced OpenAI response with function call results or structured error response
    """
    request_id = str(uuid.uuid4())

    # Apply rate limiting only in non-debug mode
    if not DEBUG_MODE:
        # Define the handler with explicit typing to satisfy mypy
        handler: Callable[
            [Request], Awaitable[Union[Dict[str, Any], JSONResponse]]
        ] = lambda req: chat_completions(request, req, db, user)

        # Apply rate limiting decorator
        limited_handler = cast(
            Callable[[Request], Awaitable[Union[Dict[str, Any], JSONResponse]]],
            limiter.limit("10/minute")(handler),
        )

        # Execute the rate-limited handler
        return await limited_handler(http_request)

    try:
        set_request_context(
            req_id=request_id, user_id_val=user.get("username", "unknown")
        )

        logger.info(
            "Processing chat completion request",
            extra={
                "request_id": request_id,
                "model": request.model,
                "message_count": len(request.messages),
                "user_agent": http_request.headers.get("user-agent", "unknown"),
                "tools_provided": len(request.tools) if request.tools else 0,
            },
        )

        if request.stream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Streaming is not supported in this implementation",
            )

        tools: Union[List[ChatCompletionToolParam], NotGiven] = NOT_GIVEN
        if request.tools is not None:
            tools = request.tools
        elif function_registry.functions:
            tools = cast(
                List[ChatCompletionToolParam],
                function_registry.get_openai_tools(),
            )
            logger.info(
                "Using registered functions as tools",
                extra={
                    "function_names": [t["function"]["name"] for t in tools],
                    "request_id": request_id,
                },
            )

        openai_params: OpenAIParams = {
            "model": request.model,
            "messages": [
                cast(
                    ChatCompletionMessageParam,
                    msg.model_dump(exclude_none=True),
                )
                for msg in request.messages
            ],
            "temperature": request.temperature,
            "tools": tools,
            "tool_choice": (
                request.tool_choice
                if request.tool_choice is not None
                else "auto" if tools is not NOT_GIVEN else NOT_GIVEN
            ),
            "max_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else NOT_GIVEN
            ),
            "stream": False,
        }

        logger.debug(
            "Calling OpenAI API",
            extra={
                "request_id": request_id,
                "model": request.model,
                "tools_count": len(tools) if isinstance(tools, list) else 0,
            },
        )

        response = await _make_openai_call(openai_params)

        function_results: List[Dict[str, Any]] = []
        if tools is not NOT_GIVEN and response.choices:
            enhanced_response, function_results = await _process_function_calls(
                response, tools, request, db, user, request_id
            )
            return enhanced_response

        # Handle standard response without function calls
        standard_response: Dict[str, Any] = response.model_dump()
        standard_response["request_id"] = request_id

        logger.info(
            "Chat completion completed successfully",
            extra={
                "request_id": request_id,
                "total_tokens": standard_response.get("usage", {}).get(
                    "total_tokens", 0
                ),
                "function_calls_made": False,
            },
        )

        REQUEST_COUNT.labels(
            method="POST", endpoint="/v1/chat/completions", status_code=200
        ).inc()
        return standard_response

    except Exception as exc:
        return _handle_exception(exc, request_id)

    finally:
        clear_request_context()


@mcp_router.get("/v1/models", response_model=None)
async def list_models() -> Union[Dict[str, Any], JSONResponse]:
    """
    List available OpenAI models with error handling and request correlation.

    Returns:
        OpenAI models response or structured error response
    """
    request_id = str(uuid.uuid4())

    try:
        set_request_context(req_id=request_id)

        logger.info(
            "Listing available models", extra={"request_id": request_id}
        )

        models = openai.models.list()
        response = models.model_dump()
        response["request_id"] = request_id

        logger.info(
            "Models listed successfully",
            extra={
                "request_id": request_id,
                "model_count": len(response.get("data", [])),
            },
        )

        REQUEST_COUNT.labels(
            method="GET", endpoint="/v1/models", status_code=200
        ).inc()
        return response

    except openai.OpenAIError as e:
        openai_error = handle_external_service_error("OpenAI", e)
        http_status = map_error_to_http_status(openai_error)
        ERROR_COUNT.labels(error_code=openai_error.error_code.value).inc()
        REQUEST_COUNT.labels(
            method="GET", endpoint="/v1/models", status_code=http_status
        ).inc()
        return create_error_response(openai_error, request_id, http_status)

    except Exception as e:
        logger.exception(
            "Unexpected error listing models",
            extra={"request_id": request_id, "error": str(e)},
        )

        unexpected_error = CarRepairError(
            message="Failed to retrieve model list",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            context={"original_error": str(e)},
            cause=e,
        )
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        ERROR_COUNT.labels(error_code=unexpected_error.error_code.value).inc()
        REQUEST_COUNT.labels(
            method="GET", endpoint="/v1/models", status_code=http_status
        ).inc()
        return create_error_response(unexpected_error, request_id, http_status)

    finally:
        clear_request_context()


@mcp_router.get("/v1/functions", response_model=None)
async def list_functions() -> Union[Dict[str, Any], JSONResponse]:
    """
    List all registered functions with enhanced metadata and monitoring information.

    Returns:
        Function registry information with comprehensive metadata
    """
    request_id = str(uuid.uuid4())

    try:
        set_request_context(req_id=request_id)

        logger.info(
            "Listing registered functions", extra={"request_id": request_id}
        )

        functions_list = function_registry.list_functions()
        function_count = function_registry.get_function_count()

        response = {
            "functions": functions_list,
            "total": function_count,
            "registry_status": "healthy" if function_count > 0 else "empty",
            "function_names": [f["name"] for f in functions_list],
            "request_id": request_id,
            "metadata": {
                "registry_type": "enhanced_dependency_injection",
                "error_handling": "structured",
                "retry_support": True,
                "monitoring_enabled": True,
            },
        }

        logger.info(
            "Functions listed successfully",
            extra={
                "request_id": request_id,
                "function_count": function_count,
                "function_names": response["function_names"],
            },
        )

        REQUEST_COUNT.labels(
            method="GET", endpoint="/v1/functions", status_code=200
        ).inc()
        return response

    except Exception as e:
        logger.exception(
            "Unexpected error listing functions",
            extra={"request_id": request_id, "error": str(e)},
        )

        unexpected_error = CarRepairError(
            message="Failed to retrieve function list",
            error_code=ErrorCode.FUNCTION_REGISTRY_ERROR,
            context={"original_error": str(e)},
            cause=e,
        )
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        ERROR_COUNT.labels(error_code=unexpected_error.error_code.value).inc()
        REQUEST_COUNT.labels(
            method="GET", endpoint="/v1/functions", status_code=http_status
        ).inc()
        return create_error_response(unexpected_error, request_id, http_status)

    finally:
        clear_request_context()


@mcp_router.get("/v1/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint with system status and metrics.

    Returns:
        System health status with detailed component information
    """
    request_id = str(uuid.uuid4())

    try:
        set_request_context(req_id=request_id)

        function_count = function_registry.get_function_count()
        registry_healthy = function_count > 0

        openai_healthy = True
        try:
            test_response = openai.models.list()
            openai_healthy = len(test_response.data) > 0
        except Exception:
            openai_healthy = False

        overall_status = (
            "healthy" if (registry_healthy and openai_healthy) else "degraded"
        )
        SYSTEM_HEALTH.set(1 if overall_status == "healthy" else 0)

        health_status = {
            "status": overall_status,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "function_registry": {
                    "status": "healthy" if registry_healthy else "unhealthy",
                    "function_count": function_count,
                    "registered_functions": list(
                        function_registry.functions.keys()
                    ),
                },
                "openai_api": {
                    "status": "healthy" if openai_healthy else "unhealthy",
                    "connectivity": openai_healthy,
                },
                "database": {"status": "healthy", "type": "async_sqlite"},
                "error_handling": {
                    "status": "enabled",
                    "structured_errors": True,
                    "retry_logic": True,
                    "monitoring": True,
                },
            },
            "capabilities": {
                "function_calling": registry_healthy,
                "multi_turn_conversations": True,
                "error_recovery": True,
                "request_correlation": True,
                "performance_monitoring": True,
            },
            "version": "1.1.0",
            "service": "car-repair-mcp-server",
        }

        logger.info(
            "Health check completed",
            extra={
                "request_id": request_id,
                "overall_status": health_status["status"],
                "function_registry_healthy": registry_healthy,
                "openai_healthy": openai_healthy,
            },
        )

        REQUEST_COUNT.labels(
            method="GET", endpoint="/v1/health", status_code=200
        ).inc()
        return health_status

    except Exception as e:
        logger.exception(
            "Health check failed",
            extra={"request_id": request_id, "error": str(e)},
        )
        SYSTEM_HEALTH.set(0)

        REQUEST_COUNT.labels(
            method="GET", endpoint="/v1/health", status_code=500
        ).inc()
        return {
            "status": "unhealthy",
            "request_id": request_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "service": "car-repair-mcp-server",
        }

    finally:
        clear_request_context()
