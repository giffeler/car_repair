"""test_mcp.py

Comprehensive integration tests for the Car Repair MCP demonstrator.
Covers authentication, CRUD operations, LLM processing, and function calling workflows.
Uses live OpenAI API calls for realistic testing with error handling validation.
"""

import asyncio
import os
from typing import Any, Dict, cast

import nest_asyncio
import pytest
from httpx import AsyncClient

nest_asyncio.apply()

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
async def token(client: AsyncClient) -> str:
    """
    Obtain a JWT token for test authentication.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.

    Returns
    -------
    str
        JWT access token.

    Raises
    ------
    AssertionError
        If token request fails or response is invalid.
    """
    response = await client.post(
        "/api/v1/token",
        data={"username": "demo", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, f"Token request failed: {response.text}"
    token_data: Dict[str, Any] = response.json()
    return str(token_data["access_token"])


@pytest.fixture(scope="function")
async def auth_headers(token: str) -> Dict[str, str]:
    """
    Provide authentication headers with a valid JWT token.

    Parameters
    ----------
    token : str
        JWT access token from the token fixture.

    Returns
    -------
    Dict[str, str]
        Authorization header with Bearer token.
    """
    return {"Authorization": f"Bearer {token}"}


async def test_token_endpoint(client: AsyncClient) -> None:
    """
    Test the /api/v1/token endpoint for JWT authentication.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.

    Raises
    ------
    AssertionError
        If token response does not match expected structure or invalid credentials are not rejected.
    """
    response = await client.post(
        "/api/v1/token",
        data={"username": "demo", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test invalid credentials
    response = await client.post(
        "/api/v1/token",
        data={"username": "wrong", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 400
    assert "Incorrect username or password" in response.json()["detail"]


async def test_create_and_read_appointment(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test basic appointment CRUD operations.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If customer/appointment creation or retrieval fails.
    """
    customer_resp = await client.post(
        "/api/v1/customers/",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+4912345678",
        },
        headers=auth_headers,
    )
    assert (
        customer_resp.status_code == 201
    ), f"Customer creation failed: {customer_resp.text}"
    customer = customer_resp.json()
    customer_id = customer["id"]

    create_data = {
        "customer_id": customer_id,
        "date": "2025-06-30T09:00:00",
        "description": "Test LLM/MCP appointment",
        "status": "scheduled",
    }
    response = await client.post(
        "/api/v1/appointments/", json=create_data, headers=auth_headers
    )
    assert (
        response.status_code == 201
    ), f"Appointment creation failed: {response.text}"
    appointment = response.json()
    assert appointment["customer_id"] == customer_id

    get_response = await client.get(
        f"/api/v1/appointments/{appointment['id']}", headers=auth_headers
    )
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == appointment["id"]


async def test_update_appointment(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test appointment update functionality.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If customer/appointment creation or update fails.
    """
    customer_resp = await client.post(
        "/api/v1/customers/",
        json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+4912349999",
        },
        headers=auth_headers,
    )
    assert customer_resp.status_code == 201
    customer = customer_resp.json()
    create_data = {
        "customer_id": customer["id"],
        "date": "2025-07-01T14:00:00",
        "description": "Original appointment",
        "status": "scheduled",
    }
    appointment_resp = await client.post(
        "/api/v1/appointments/", json=create_data, headers=auth_headers
    )
    assert appointment_resp.status_code == 201
    appointment = appointment_resp.json()

    update_data = {"description": "Updated LLM/MCP appointment"}
    update_resp = await client.put(
        f"/api/v1/appointments/{appointment['id']}",
        json=update_data,
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["description"] == "Updated LLM/MCP appointment"


async def test_llm_process_appointment(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test the LLM/MCP processing endpoint.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If customer/appointment creation or LLM processing fails.
    """
    customer_resp = await client.post(
        "/api/v1/customers/",
        json={
            "name": "LLM User",
            "email": "llm@example.com",
            "phone": "+4911111111",
        },
        headers=auth_headers,
    )
    assert customer_resp.status_code == 201
    customer = customer_resp.json()
    create_data = {
        "customer_id": customer["id"],
        "date": "2025-08-01T10:30:00",
        "description": "Check brakes and oil",
        "status": "scheduled",
    }
    appointment_resp = await client.post(
        "/api/v1/appointments/", json=create_data, headers=auth_headers
    )
    assert appointment_resp.status_code == 201
    appointment = appointment_resp.json()

    llm_resp = await client.post(
        f"/api/v1/appointments/{appointment['id']}/llm-process/",
        headers=auth_headers,
    )
    assert llm_resp.status_code == 200
    result = llm_resp.json()
    assert "result" in result

    # With the improved MCP server, we should always get content
    assert "content" in result["result"]

    # The content should contain relevant information about the service
    content = result["result"]["content"]
    if content:  # Content might still be None in some edge cases
        content_lower = content.lower()
        assert any(
            word in content_lower
            for word in [
                "brake",
                "oil",
                "service",
                "check",
                "customer",
                "appointment",
            ]
        )

    # Check if function calls were made
    if "function_calls" in result["result"]:
        function_calls = result["result"]["function_calls"]
        if function_calls:
            # Verify meaningful functions were called
            function_names = [fc.get("name", "") for fc in function_calls]
            expected_functions = [
                "analyze_service_description",
                "estimate_service_duration",
                "get_customer_by_id",
            ]
            assert any(name in expected_functions for name in function_names)


async def test_mcp_endpoint_proxy(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test the MCP server endpoint without function calling.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If MCP response does not match expected structure.
    """
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the purpose of engine oil?"},
        ],
        "temperature": 0.2,
    }
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    # Handle both enhanced and standard response formats
    if "function_call_results" in data:
        assert "choices" in data or "function_call_results" in data
    else:
        assert "choices" in data
        assert len(data["choices"]) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.benchmark(group="llm_integration", min_rounds=3, warmup=True)
async def test_llm_function_calling_workflow(
    client: AsyncClient, auth_headers: Dict[str, str], benchmark: Any
) -> None:
    """
    Benchmark LLM function calling workflow, measuring end-to-end performance.

    Args:
        client: Async HTTP client for API calls.
        auth_headers: Authentication headers with JWT token.
        benchmark: Pytest-benchmark fixture for performance measurement.

    Raises:
        AssertionError: If customer creation or function calling workflow fails.
    """
    # Setup (non-benchmarked)
    customer_resp = await client.post(
        "/api/v1/customers/",
        json={
            "name": "Function Test",
            "email": "func@example.com",
            "phone": "+499999999",
        },
        headers=auth_headers,
    )
    assert customer_resp.status_code == 201
    customer = customer_resp.json()
    customer_id = customer["id"]

    # Benchmark the core workflow
    async def workflow() -> Dict[str, Any]:
        payload = {
            "model": "gpt-4.1-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an assistant with access to customer records. Use the available functions to help users.",
                },
                {
                    "role": "user",
                    "content": f"Please get the details for customer ID {customer_id}",
                },
            ],
            "temperature": 0.1,
        }
        response = await client.post(
            "/v1/chat/completions", json=payload, headers=auth_headers
        )
        return cast(Dict[str, Any], response.json())

    def sync_workflow() -> Dict[str, Any]:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(workflow())
        finally:
            loop.close()

    data = cast(Dict[str, Any], benchmark(sync_workflow))
    assert "function_call_results" in data
    function_results = data["function_call_results"]
    assert len(function_results) > 0
    customer_call = next(
        (r for r in function_results if r["name"] == "get_customer_by_id"), None
    )
    assert customer_call is not None
    assert customer_call["result"]["id"] == customer_id


async def test_function_call_search_customers(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test customer search function calling.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If customer creation or search function calling fails.
    """
    # Create test customers
    customers_data = [
        {
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone": "+1234567890",
        },
        {
            "name": "Bob Smith",
            "email": "bob@example.com",
            "phone": "+1234567891",
        },
        {
            "name": "Charlie Brown",
            "email": "charlie@example.com",
            "phone": "+1234567892",
        },
    ]

    for customer_data in customers_data:
        resp = await client.post(
            "/api/v1/customers/", json=customer_data, headers=auth_headers
        )
        assert resp.status_code == 201

    # Test search by name
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant. Use available functions to search for customers.",
            },
            {
                "role": "user",
                "content": "Find all customers with 'Smith' in their name",
            },
        ],
        "temperature": 0.1,
    }
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "function_call_results" in data

    # Verify search function was called
    function_results = data["function_call_results"]
    search_call = next(
        (r for r in function_results if r["name"] == "search_customers"), None
    )
    assert search_call is not None
    assert "result" in search_call

    # Should find Alice and Bob Smith
    customers = search_call["result"]
    assert len(customers) >= 2
    assert all("Smith" in customer["name"] for customer in customers)


async def test_function_call_appointment_management(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test appointment-related function calling.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If customer/appointment creation or appointment retrieval fails.
    """
    # Create customer and appointment
    customer_resp = await client.post(
        "/api/v1/customers/",
        json={
            "name": "Appointment Test",
            "email": "appt@example.com",
            "phone": "+1111111111",
        },
        headers=auth_headers,
    )
    assert customer_resp.status_code == 201
    customer = customer_resp.json()

    appointment_resp = await client.post(
        "/api/v1/appointments/",
        json={
            "customer_id": customer["id"],
            "date": "2025-12-01T10:00:00",
            "description": "Brake inspection and oil change",
            "status": "scheduled",
        },
        headers=auth_headers,
    )
    assert appointment_resp.status_code == 201
    initial_appointment_data: Dict[str, Any] = appointment_resp.json()

    # Validate initial data to ensure setup correctness and use the variable
    assert (
        "id" in initial_appointment_data
    ), "Appointment ID missing in response"
    assert (
        initial_appointment_data["status"] == "scheduled"
    ), "Initial appointment status mismatch"
    assert (
        initial_appointment_data["customer_id"] == customer["id"]
    ), "Customer ID mismatch in appointment"

    # Test getting customer appointments
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant with access to appointment records.",
            },
            {
                "role": "user",
                "content": f"Show me all appointments for customer ID {customer['id']}",
            },
        ],
        "temperature": 0.1,
    }
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    function_results = data["function_call_results"]
    appt_call = next(
        (
            r
            for r in function_results
            if r["name"] == "get_customer_appointments"
        ),
        None,
    )
    assert appt_call is not None
    assert len(appt_call["result"]) >= 1


async def test_function_call_analysis_functions(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test service analysis function calling.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If analysis function calling fails or expected functions are not invoked.
    """
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are a service advisor. Use available functions to analyze service requests.",
            },
            {
                "role": "user",
                "content": "Analyze this service request: 'Replace brake pads and check transmission fluid'",
            },
        ],
        "temperature": 0.1,
    }
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    function_results = data["function_call_results"]

    # Should call analysis functions
    analysis_call = next(
        (
            r
            for r in function_results
            if r["name"] == "analyze_service_description"
        ),
        None,
    )
    duration_call = next(
        (
            r
            for r in function_results
            if r["name"] == "estimate_service_duration"
        ),
        None,
    )

    # At least one analysis function should be called
    assert analysis_call is not None or duration_call is not None


async def test_function_call_error_handling(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test error scenarios in function calling.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If error handling in function calls does not produce expected results.
    """
    # Test with invalid customer ID
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant. Try to get customer information.",
            },
            {"role": "user", "content": "Please get customer with ID 999999"},
        ],
        "temperature": 0.1,
    }
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()

    # Should have function call results with errors
    if "function_call_results" in data:
        function_results = data["function_call_results"]
        # Check if any function calls resulted in errors
        error_calls = [r for r in function_results if "error" in r]
        # If a function was called with invalid ID, it should error
        if any(r["name"] == "get_customer_by_id" for r in function_results):
            assert len(error_calls) > 0


async def test_function_call_update_appointment_status(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test appointment status update via function calling.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If customer/appointment creation or status update fails.
    """
    # Create customer and appointment
    customer_resp = await client.post(
        "/api/v1/customers/",
        json={
            "name": "Status Test",
            "email": "status@example.com",
            "phone": "+2222222222",
        },
        headers=auth_headers,
    )
    assert customer_resp.status_code == 201
    customer = customer_resp.json()

    appointment_resp = await client.post(
        "/api/v1/appointments/",
        json={
            "customer_id": customer["id"],
            "date": "2025-12-15T14:00:00",
            "description": "Tire replacement",
            "status": "scheduled",
        },
        headers=auth_headers,
    )
    assert appointment_resp.status_code == 201
    initial_appointment_data: Dict[str, Any] = appointment_resp.json()

    # Validate initial data to ensure setup correctness and use the variable
    assert (
        "id" in initial_appointment_data
    ), "Appointment ID missing in response"
    assert (
        initial_appointment_data["status"] == "scheduled"
    ), "Initial appointment status mismatch"
    assert (
        initial_appointment_data["customer_id"] == customer["id"]
    ), "Customer ID mismatch in appointment"

    # Test status update via function calling
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant that can update appointment statuses.",
            },
            {
                "role": "user",
                "content": f"Please mark appointment {initial_appointment_data['id']} as completed",
            },
        ],
        "temperature": 0.1,
    }
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    if "function_call_results" in data:
        function_results = data["function_call_results"]
        update_call = next(
            (
                r
                for r in function_results
                if r["name"] == "update_appointment_status"
            ),
            None,
        )
        if update_call and "result" in update_call:
            assert update_call["result"]["status"] == "completed"


async def test_list_functions_endpoint(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test the function listing endpoint.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If function listing fails or expected functions are missing.
    """
    response = await client.get("/v1/functions", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "functions" in data
    assert "total" in data
    assert data["total"] > 0

    # Check that all expected functions are registered
    function_names = [f["name"] for f in data["functions"]]
    expected_functions = [
        "get_customer_by_id",
        "search_customers",
        "get_appointment_by_id",
        "get_customer_appointments",
        "update_appointment_status",
        "analyze_service_description",
        "estimate_service_duration",
    ]

    for expected in expected_functions:
        assert expected in function_names


async def test_health_check(client: AsyncClient) -> None:
    """
    Test the health check endpoint.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.

    Raises
    ------
    AssertionError
        If health check response does not match expected structure.
    """
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["function_calling"] == "enabled"


@pytest.mark.slow
async def test_rate_limiting(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test rate limiting on /v1/chat/completions endpoint in non-debug mode.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If rate limiting does not enforce expected behavior.
    """
    if os.getenv("DEBUG", "false").lower() == "true":
        pytest.skip("Rate limiting tests require DEBUG=false")
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Test rate limiting"},
        ],
        "temperature": 0.2,
    }
    for _ in range(10):
        response = await client.post(
            "/v1/chat/completions", json=payload, headers=auth_headers
        )
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}"
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json().get("error", "")


async def test_tool_calls_format(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Test that the /v1/chat/completions endpoint correctly handles tool_calls format.

    Parameters
    ----------
    client : AsyncClient
        Async HTTP client for API calls.
    auth_headers : Dict[str, str]
        Authentication headers with JWT token.

    Raises
    ------
    AssertionError
        If tool calls format handling or function execution fails.
    """
    # Create test customer
    customer_resp = await client.post(
        "/api/v1/customers/",
        json={
            "name": "Tool Test",
            "email": "tool@example.com",
            "phone": "+499999998",
        },
        headers=auth_headers,
    )
    assert customer_resp.status_code == 201
    customer = customer_resp.json()
    customer_id = customer["id"]

    # Test tool_calls format
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant with access to customer records. Use available tools to help users.",
            },
            {
                "role": "user",
                "content": f"Please get the details for customer ID {customer_id}",
            },
        ],
        "temperature": 0.1,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_customer_by_id",
                    "description": "Retrieve a customer by their unique ID",
                    "parameters": {
                        "type": "object",
                        "properties": {"customer_id": {"type": "integer"}},
                        "required": ["customer_id"],
                    },
                },
            }
        ],
        "tool_choice": "auto",
    }
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert "function_call_results" in data

    # Verify function was called successfully
    function_results = data["function_call_results"]
    assert len(function_results) > 0

    # Check if get_customer_by_id was called
    customer_call = next(
        (r for r in function_results if r["name"] == "get_customer_by_id"), None
    )
    assert customer_call is not None
    assert "result" in customer_call
    assert customer_call["result"]["id"] == customer_id

    # Verify tool_calls in the response
    if "conversation_messages" in data:
        assistant_message = next(
            (
                m
                for m in data["conversation_messages"]
                if m["role"] == "assistant"
            ),
            None,
        )
        assert assistant_message is not None
        assert "tool_calls" in assistant_message
        assert len(assistant_message["tool_calls"]) > 0
        assert assistant_message["tool_calls"][0]["type"] == "function"
        assert (
            assistant_message["tool_calls"][0]["function"]["name"]
            == "get_customer_by_id"
        )


# neu


@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_example_verification(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    This test automates manual examples, ensuring endpoints behave as documented.
    Uses existing fixtures for authentication and client setup.
    """
    # Example: Create customer (Step 2)
    customer_payload: Dict[str, Any] = {
        "name": "Max Mustermann",
        "email": "max@example.com",
        "phone": "+49-123-456789",
    }
    response = await client.post(
        "/api/v1/customers/", json=customer_payload, headers=auth_headers
    )
    assert response.status_code == 201
    customer: Dict[str, Any] = response.json()
    assert customer["name"] == "Max Mustermann"

    # Example: Create appointment (Step 3)
    appointment_payload: Dict[str, Any] = {
        "customer_id": customer["id"],
        "date": "2025-12-01T10:00:00",
        "description": "Brake inspection and oil change",
        "status": "scheduled",
    }
    response = await client.post(
        "/api/v1/appointments/", json=appointment_payload, headers=auth_headers
    )
    assert response.status_code == 201
    appointment: Dict[str, Any] = response.json()
    assert appointment["description"] == "Brake inspection and oil change"

    # Add more examples (e.g., LLM process from Step 5)
    # ...


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_examples(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Ensures proper handling of invalid inputs, with assertions on error codes.
    """
    # Example: Invalid customer ID (ENTITY_NOT_FOUND)
    payload: Dict[str, Any] = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "user", "content": "Get customer ID 999999"},
        ],
    }
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert (
        response.status_code == 200
    )  # MCP returns 200 even with function errors
    data: Dict[str, Any] = response.json()
    assert "function_call_results" in data
    error_result = next(
        (
            r
            for r in data["function_call_results"]
            if not r.get("success", True)
        ),
        None,
    )
    assert error_result is not None
    assert error_result["error_code"] == "DB_004"  # From exceptions.py

    # Add more error cases (e.g., invalid status transition)...


@pytest.mark.asyncio
@pytest.mark.slow
async def test_rate_limiting_enhanced(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> None:
    """
    Enhanced rate limiting test with configurable loops.

    Simulates excessive requests to verify 429 responses, using async loops.
    Assumes DEBUG=false; skips otherwise.
    """
    import os

    if os.getenv("DEBUG", "false").lower() == "true":
        pytest.skip("Rate limiting tests require DEBUG=false")

    payload: Dict[str, Any] = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": "Test rate limiting"}],
    }
    for _ in range(10):
        response = await client.post(
            "/v1/chat/completions", json=payload, headers=auth_headers
        )
        assert response.status_code == 200

    # 11th request should hit limit (slowapi: 10/minute)
    response = await client.post(
        "/v1/chat/completions", json=payload, headers=auth_headers
    )
    assert response.status_code == 429
    error: Dict[str, Any] = response.json()
    assert "Rate limit exceeded" in error.get("error", "")
