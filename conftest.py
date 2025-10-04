"""
conftest.py

Pytest fixtures for Car Repair MCP demonstrator.
Sets up live test database, FastAPI test client, seeds data, and initializes function registry.
Includes server health check to ensure Uvicorn is running.
"""

from collections.abc import AsyncGenerator, Generator
from typing import Any, Dict, cast

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient, ConnectError
from sqlmodel.ext.asyncio.session import AsyncSession

from car_repair_mcp_server import app as fastapi_app
from database import drop_db, engine, init_db
from seed import seed_db


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Use a session-scoped event loop for all async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def check_server() -> None:
    """
    Verify that the Uvicorn server is running before tests.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        try:
            response = await client.get("/health")
            assert (
                response.status_code == 200
            ), f"Server not running or unhealthy: {response.text}"
        except ConnectError:
            pytest.fail(
                "Uvicorn server is not running. Start the server with 'uvicorn car_repair_mcp_server:app --reload' before running tests."
            )


@pytest.fixture(scope="session", autouse=True)
async def prepare_database() -> AsyncGenerator[None, None]:
    """
    Create the test database schema before tests and drop it after.
    """
    await init_db()
    yield
    await drop_db()


@pytest.fixture(scope="session", autouse=True)
async def setup_function_registry() -> AsyncGenerator[None, None]:
    """
    Ensure function registry is initialized for tests.
    """
    try:
        from function_handlers import register_functions

        register_functions()
    except Exception:
        pass  # Functions might already be registered
    yield


@pytest.fixture(scope="function", autouse=True)
async def seed_test_data(prepare_database: Any) -> None:
    """
    Seed the test database before each test function.
    """
    await seed_db()


@pytest.fixture(scope="function")
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a fresh async SQLModel session for a test.
    """
    async with AsyncSession(engine) as session:
        yield session


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI test client for live, in-process API calls using ASGITransport.
    """
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture(scope="function")
async def test_customer(
    client: AsyncClient, auth_headers: Dict[str, str]
) -> Dict[str, Any]:
    """
    Creates a test customer for use in tests.
    """
    customer_data = {
        "name": "Test Customer",
        "email": "test.customer@example.com",
        "phone": "+1234567890",
    }
    response = await client.post(
        "/api/v1/customers/", json=customer_data, headers=auth_headers
    )
    assert response.status_code == 201
    return cast(Dict[str, Any], response.json())


@pytest.fixture(scope="function")
async def test_appointment(
    client: AsyncClient,
    auth_headers: Dict[str, str],
    test_customer: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Creates a test appointment for use in tests.
    """
    appointment_data = {
        "customer_id": test_customer["id"],
        "date": "2025-12-01T10:00:00",
        "description": "Test service appointment",
        "status": "scheduled",
    }
    response = await client.post(
        "/api/v1/appointments/", json=appointment_data, headers=auth_headers
    )
    assert response.status_code == 201
    return cast(Dict[str, Any], response.json())
