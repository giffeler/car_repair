"""
main_mcp.py

Defines FastAPI API endpoints for car repair operations,
including both customer and appointment CRUD operations,
with MCP/LLM (OpenAI) integration. Includes token endpoint for JWT authentication.
"""

from typing import Dict, List, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_async_session
from mcp_client import process_with_llm
from models import Appointment, Customer
from schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
)
from session_manager import create_access_token, get_current_user

api_router = APIRouter()

# ------------------ Authentication Endpoint ------------------


@api_router.post(
    "/token",
    status_code=status.HTTP_200_OK,
    summary="Generate access token",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Dict[str, str]:
    """
    Generate JWT access token for authentication.

    Args:
        form_data: OAuth2 password request form with username and password.

    Returns:
        dict: Access token and token type.

    Raises:
        HTTPException: If credentials are invalid.
    """
    if form_data.username != "demo" or form_data.password != "password":
        raise HTTPException(
            status_code=400, detail="Incorrect username or password"
        )
    access_token: str = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


# ------------------ Customer Endpoints ------------------


@api_router.post(
    "/customers/",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
)
async def create_customer(
    customer_in: CustomerCreate,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Customer:
    """
    Create a new customer.

    Args:
        customer_in: Customer creation data.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        Customer: Created customer data.
    """
    customer = Customer.model_validate(customer_in)
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


@api_router.get(
    "/customers/{customer_id}",
    response_model=CustomerRead,
    status_code=status.HTTP_200_OK,
    summary="Get customer by ID",
)
async def get_customer(
    customer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Customer:
    """
    Retrieve a customer by ID.

    Args:
        customer_id: Customer ID.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        Customer: Customer data.

    Raises:
        HTTPException: If customer not found.
    """
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )
    return customer


@api_router.get(
    "/customers/",
    response_model=List[CustomerRead],
    status_code=status.HTTP_200_OK,
    summary="List customers",
)
async def list_customers(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> List[Customer]:
    """
    List all customers (paginated).

    Args:
        skip: Offset for pagination.
        limit: Maximum number of results.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        List[Customer]: List of customers.
    """
    statement = select(Customer).offset(skip).limit(limit)
    results = await session.exec(statement)
    return list(results.all())


@api_router.put(
    "/customers/{customer_id}",
    response_model=CustomerRead,
    status_code=status.HTTP_200_OK,
    summary="Update customer by ID",
)
async def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Customer:
    """
    Update a customer by ID.

    Args:
        customer_id: Customer ID.
        customer_in: Customer update data.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        Customer: Updated customer data.

    Raises:
        HTTPException: If customer not found.
    """
    db_customer = await session.get(Customer, customer_id)
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found"
        )
    for key, value in customer_in.model_dump(exclude_unset=True).items():
        setattr(db_customer, key, value)
    session.add(db_customer)
    await session.commit()
    await session.refresh(db_customer)
    return db_customer


# ------------------ Appointment Endpoints ------------------


@api_router.get(
    "/appointments/",
    response_model=List[AppointmentRead],
    status_code=status.HTTP_200_OK,
    summary="List all appointments",
)
async def list_appointments(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> List[Appointment]:
    """
    Retrieve a paginated list of all appointments.

    Args:
        skip: Offset for pagination.
        limit: Maximum number of results.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        List[Appointment]: List of appointments.
    """
    statement = select(Appointment).offset(skip).limit(limit)
    results = await session.exec(statement)
    return list(results.all())


@api_router.post(
    "/appointments/",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new appointment",
)
async def create_appointment(
    appointment_in: AppointmentCreate,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Appointment:
    """
    Create a new appointment.

    Args:
        appointment_in: Appointment creation data.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        Appointment: Created appointment data.
    """
    appointment = Appointment.model_validate(appointment_in)
    session.add(appointment)
    await session.commit()
    await session.refresh(appointment)
    return appointment


@api_router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentRead,
    status_code=status.HTTP_200_OK,
    summary="Get appointment by ID",
)
async def get_appointment(
    appointment_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Appointment:
    """
    Retrieve an appointment by its ID.

    Args:
        appointment_id: Appointment ID.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        Appointment: Appointment data.

    Raises:
        HTTPException: If appointment not found.
    """
    appointment = await session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    return appointment


@api_router.put(
    "/appointments/{appointment_id}",
    response_model=AppointmentRead,
    status_code=status.HTTP_200_OK,
    summary="Update appointment by ID",
)
async def update_appointment(
    appointment_id: int,
    appointment_in: AppointmentUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Appointment:
    """
    Update an appointment by ID.

    Args:
        appointment_id: Appointment ID.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        Appointment: Updated appointment data.

    Raises:
        HTTPException: If appointment not found.
    """
    db_appointment = await session.get(Appointment, appointment_id)
    if not db_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    for key, value in appointment_in.model_dump(exclude_unset=True).items():
        setattr(db_appointment, key, value)
    session.add(db_appointment)
    await session.commit()
    await session.refresh(db_appointment)
    return db_appointment


# ------------------ LLM/MCP Integration Endpoint (async, safe) ------------------


@api_router.post(
    "/appointments/{appointment_id}/llm-process/",
    status_code=status.HTTP_200_OK,
    summary="Process appointment with LLM via MCP",
)
async def process_appointment_with_llm(
    appointment_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Call the LLM (via MCP) on the appointment record for demonstration.

    Args:
        appointment_id: Appointment ID.
        session: Async database session.
        user: Authenticated user context.

    Returns:
        dict: LLM processing result.

    Raises:
        HTTPException: If appointment not found.
    """
    appointment = await session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    llm_result = await process_with_llm(appointment)
    return {"result": llm_result}
