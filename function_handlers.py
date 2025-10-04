"""
function_handlers.py

Implements OpenAI-callable business logic functions with comprehensive error handling
and structured logging for the Car Repair MCP demonstrator.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from exceptions import (
    EntityNotFoundError,
    ValidationError,
    handle_database_error,
)
from logging_config import get_logger, log_database_operation
from models import Appointment, Customer
from schemas import AppointmentRead, CustomerRead

# Type checking imports to avoid circular dependencies
if TYPE_CHECKING:
    from function_schemas import (
        AnalyzeServiceDescriptionParams,
        EstimateServiceDurationParams,
        GetAppointmentByIdParams,
        GetCustomerAppointmentsParams,
        GetCustomerByIdParams,
        SearchCustomersParams,
        UpdateAppointmentStatusParams,
    )

# ---------------- Customer Function Handlers ----------------


async def get_customer_by_id_handler(
    params: GetCustomerByIdParams, session: AsyncSession, user: Dict[str, Any]
) -> CustomerRead:
    """
    Retrieve a customer by their unique ID with comprehensive error handling.

    Args:
        params: Validated parameters containing customer_id
        session: Async database session
        user: Authenticated user context

    Returns:
        CustomerRead: Customer data

    Raises:
        EntityNotFoundError: If customer does not exist
        DatabaseOperationError: If database operation fails
    """
    logger = get_logger("customer_handlers")
    start_time = time.time()

    try:
        customer = await session.get(Customer, params.customer_id)
        execution_time_ms = (time.time() - start_time) * 1000

        if not customer:
            log_database_operation(
                logger,
                "select",
                "Customer",
                params.customer_id,
                False,
                execution_time_ms,
            )
            raise EntityNotFoundError("Customer", params.customer_id)

        log_database_operation(
            logger,
            "select",
            "Customer",
            params.customer_id,
            True,
            execution_time_ms,
        )

        return CustomerRead.model_validate(customer.model_dump())

    except SQLAlchemyError as e:
        execution_time_ms = (time.time() - start_time) * 1000
        log_database_operation(
            logger,
            "select",
            "Customer",
            params.customer_id,
            False,
            execution_time_ms,
        )
        raise handle_database_error("get_customer_by_id", e)


async def search_customers_handler(
    params: SearchCustomersParams, session: AsyncSession, user: Dict[str, Any]
) -> List[CustomerRead]:
    """
    Search customers by email or name with comprehensive error handling.

    Args:
        params: Validated search parameters
        session: Async database session
        user: Authenticated user context

    Returns:
        List[CustomerRead]: Matching customers

    Raises:
        ValidationError: If search parameters are invalid
        DatabaseOperationError: If database operation fails
    """
    logger = get_logger("customer_handlers")
    start_time = time.time()

    # Validate search criteria
    if not params.email and not params.name:
        raise ValidationError(
            field="search_criteria",
            value="empty",
            message="At least one search criterion (email or name) must be provided",
        )

    try:
        query = select(Customer)
        search_criteria = []

        if params.email:
            query = query.where(Customer.email == params.email)
            search_criteria.append(f"email={params.email}")

        if params.name:
            # Use func.lower() for case-insensitive matching with proper typing
            query = query.where(
                func.lower(Customer.name).contains(func.lower(params.name))
            )
            search_criteria.append(f"name_contains={params.name}")

        results = await session.exec(query)
        customers = results.all()

        execution_time_ms = (time.time() - start_time) * 1000
        log_database_operation(
            logger, "search", "Customer", None, True, execution_time_ms
        )

        logger.info(
            "Customer search completed",
            search_criteria=search_criteria,
            result_count=len(customers),
            execution_time_ms=execution_time_ms,
        )

        return [CustomerRead.model_validate(c.model_dump()) for c in customers]

    except SQLAlchemyError as e:
        execution_time_ms = (time.time() - start_time) * 1000
        log_database_operation(
            logger, "search", "Customer", None, False, execution_time_ms
        )
        raise handle_database_error("search_customers", e)


# ---------------- Appointment Function Handlers ----------------


async def get_appointment_by_id_handler(
    params: GetAppointmentByIdParams,
    session: AsyncSession,
    user: Dict[str, Any],
) -> AppointmentRead:
    """
    Retrieve an appointment by its unique ID with comprehensive error handling.

    Args:
        params: Validated parameters containing appointment_id
        session: Async database session
        user: Authenticated user context

    Returns:
        AppointmentRead: Appointment data

    Raises:
        EntityNotFoundError: If appointment does not exist
        DatabaseOperationError: If database operation fails
    """
    logger = get_logger("appointment_handlers")
    start_time = time.time()

    try:
        appointment = await session.get(Appointment, params.appointment_id)
        execution_time_ms = (time.time() - start_time) * 1000

        if not appointment:
            log_database_operation(
                logger,
                "select",
                "Appointment",
                params.appointment_id,
                False,
                execution_time_ms,
            )
            raise EntityNotFoundError("Appointment", params.appointment_id)

        log_database_operation(
            logger,
            "select",
            "Appointment",
            params.appointment_id,
            True,
            execution_time_ms,
        )

        return AppointmentRead.model_validate(appointment.model_dump())

    except SQLAlchemyError as e:
        execution_time_ms = (time.time() - start_time) * 1000
        log_database_operation(
            logger,
            "select",
            "Appointment",
            params.appointment_id,
            False,
            execution_time_ms,
        )
        raise handle_database_error("get_appointment_by_id", e)


async def get_customer_appointments_handler(
    params: GetCustomerAppointmentsParams,
    session: AsyncSession,
    user: Dict[str, Any],
) -> List[AppointmentRead]:
    """
    Get all appointments for a specific customer with comprehensive error handling.

    Args:
        params: Validated parameters containing customer_id
        session: Async database session
        user: Authenticated user context

    Returns:
        List[AppointmentRead]: Customer's appointments

    Raises:
        DatabaseOperationError: If database operation fails
    """
    logger = get_logger("appointment_handlers")
    start_time = time.time()

    try:
        query = select(Appointment).where(
            Appointment.customer_id == params.customer_id
        )
        results = await session.exec(query)
        appointments = results.all()

        execution_time_ms = (time.time() - start_time) * 1000
        log_database_operation(
            logger,
            "select",
            "Appointment",
            params.customer_id,
            True,
            execution_time_ms,
        )

        logger.info(
            "Customer appointments retrieved",
            customer_id=params.customer_id,
            appointment_count=len(appointments),
            execution_time_ms=execution_time_ms,
        )

        return [
            AppointmentRead.model_validate(a.model_dump()) for a in appointments
        ]

    except SQLAlchemyError as e:
        execution_time_ms = (time.time() - start_time) * 1000
        log_database_operation(
            logger,
            "select",
            "Appointment",
            params.customer_id,
            False,
            execution_time_ms,
        )
        raise handle_database_error("get_customer_appointments", e)


async def update_appointment_status_handler(
    params: UpdateAppointmentStatusParams,
    session: AsyncSession,
    user: Dict[str, Any],
) -> AppointmentRead:
    """
    Update the status of an existing appointment with transaction management.

    Args:
        params: Validated parameters containing appointment_id and status
        session: Async database session
        user: Authenticated user context

    Returns:
        AppointmentRead: Updated appointment data

    Raises:
        EntityNotFoundError: If appointment does not exist
        ValidationError: If status transition is invalid
        DatabaseOperationError: If database operation fails
    """
    logger = get_logger("appointment_handlers")
    start_time = time.time()

    # Valid status transitions (simplified business logic)
    VALID_TRANSITIONS = {
        "scheduled": ["confirmed", "cancelled", "rescheduled"],
        "confirmed": ["in_progress", "cancelled", "rescheduled"],
        "in_progress": ["completed", "cancelled"],
        "completed": [],  # Final state
        "cancelled": ["rescheduled"],  # Can reschedule cancelled appointments
        "rescheduled": ["scheduled", "confirmed"],
    }

    try:
        # Begin transaction scope
        appointment = await session.get(Appointment, params.appointment_id)

        if not appointment:
            raise EntityNotFoundError("Appointment", params.appointment_id)

        # Validate status transition
        current_status = appointment.status
        new_status = params.status

        if new_status not in VALID_TRANSITIONS.get(current_status, []):
            raise ValidationError(
                field="status",
                value=new_status,
                message=f"Invalid status transition from '{current_status}' to '{new_status}'",
                context={
                    "current_status": current_status,
                    "requested_status": new_status,
                    "valid_transitions": VALID_TRANSITIONS.get(
                        current_status, []
                    ),
                },
            )

        # Update appointment
        old_status = appointment.status
        appointment.status = new_status
        session.add(appointment)

        await session.commit()
        await session.refresh(appointment)

        execution_time_ms = (time.time() - start_time) * 1000
        log_database_operation(
            logger,
            "update",
            "Appointment",
            params.appointment_id,
            True,
            execution_time_ms,
        )

        logger.info(
            "Appointment status updated",
            appointment_id=params.appointment_id,
            old_status=old_status,
            new_status=new_status,
            user_token=(
                user.get("token", "unknown")[:10] + "..."
                if user.get("token")
                else None
            ),
            execution_time_ms=execution_time_ms,
        )

        return AppointmentRead.model_validate(appointment.model_dump())

    except (EntityNotFoundError, ValidationError):
        # Re-raise business logic errors without wrapping
        await session.rollback()
        raise
    except SQLAlchemyError as e:
        await session.rollback()
        execution_time_ms = (time.time() - start_time) * 1000
        log_database_operation(
            logger,
            "update",
            "Appointment",
            params.appointment_id,
            False,
            execution_time_ms,
        )
        raise handle_database_error("update_appointment_status", e)


# ---------------- Analysis Function Handlers ----------------


async def analyze_service_description_handler(
    params: AnalyzeServiceDescriptionParams,
    session: AsyncSession,
    user: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Analyze a service description and extract key information with validation.

    Args:
        params: Validated parameters containing service description
        session: Async database session (unused for this function)
        user: Authenticated user context

    Returns:
        Dict[str, Any]: Analysis results with summary, keywords, and complexity

    Raises:
        ValidationError: If description is too short or invalid
    """
    logger = get_logger("analysis_handlers")
    start_time = time.time()

    description = params.description.strip()

    # Validate description content
    if len(description) < 5:
        raise ValidationError(
            field="description",
            value=description,
            message="Service description must be at least 5 characters long",
        )

    # Remove common stop words and extract meaningful keywords
    stop_words = {
        "and",
        "or",
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "for",
        "of",
        "to",
        "in",
        "on",
        "at",
    }
    words = [w.strip(".,!?;:") for w in description.lower().split()]
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]

    # Determine complexity based on keywords and description length
    complexity_score = len(keywords) + (len(description) // 50)
    if complexity_score <= 3:
        complexity = "simple"
    elif complexity_score <= 7:
        complexity = "medium"
    else:
        complexity = "complex"

    # Generate intelligent summary
    if len(keywords) > 0:
        primary_keywords = keywords[:5]
        summary = (
            f"This service likely involves: {', '.join(primary_keywords)}."
        )
    else:
        summary = "General service request requiring further clarification."

    execution_time_ms = (time.time() - start_time) * 1000

    result = {
        "summary": summary,
        "keywords": keywords[:10],  # Limit to top 10 keywords
        "complexity": complexity,
        "word_count": len(words),
        "keyword_count": len(keywords),
    }

    logger.info(
        "Service description analyzed",
        description_length=len(description),
        keyword_count=len(keywords),
        complexity=complexity,
        execution_time_ms=execution_time_ms,
    )

    return result


async def estimate_service_duration_handler(
    params: EstimateServiceDurationParams,
    session: AsyncSession,
    user: Dict[str, Any],
) -> Dict[str, int]:
    """
    Estimate service duration based on description keywords with improved logic.

    Args:
        params: Validated parameters containing service description
        session: Async database session (unused for this function)
        user: Authenticated user context

    Returns:
        Dict[str, int]: Duration estimate in minutes with breakdown

    Raises:
        ValidationError: If description is invalid
    """
    logger = get_logger("analysis_handlers")
    start_time = time.time()

    description = params.description.strip().lower()

    if len(description) < 3:
        raise ValidationError(
            field="description",
            value=description,
            message="Description must be at least 3 characters for duration estimation",
        )

    # Enhanced duration estimation with service-specific logic
    base_time = 30  # Base service time in minutes
    service_times = {
        # Brake services
        "brake": 60,
        "brakes": 60,
        "brake pad": 45,
        "brake fluid": 30,
        # Oil and fluid services
        "oil": 20,
        "oil change": 25,
        "fluid": 15,
        "coolant": 20,
        # Tire services
        "tire": 40,
        "tyre": 40,
        "wheel": 35,
        "rotation": 30,
        "balance": 25,
        # Engine services
        "engine": 120,
        "tune": 90,
        "tune-up": 90,
        "spark": 45,
        "filter": 15,
        # Transmission services
        "transmission": 180,
        "clutch": 150,
        "gearbox": 160,
        # Electrical services
        "battery": 20,
        "alternator": 90,
        "starter": 75,
        "electrical": 60,
        # Diagnostic services
        "diagnostic": 60,
        "check": 45,
        "inspection": 30,
        "scan": 20,
    }

    additional_time = 0
    matched_services = []

    for service, duration in service_times.items():
        if service in description:
            additional_time += duration
            matched_services.append(f"{service}({duration}min)")

    # Apply complexity multiplier for multiple services
    if len(matched_services) > 1:
        complexity_multiplier = 1.2  # 20% additional time for multiple services
        additional_time = int(additional_time * complexity_multiplier)

    total_minutes = base_time + additional_time

    # Reasonable bounds (15 minutes to 8 hours)
    total_minutes = max(15, min(total_minutes, 480))

    execution_time_ms = (time.time() - start_time) * 1000

    result = {
        "estimated_minutes": total_minutes,
        "base_time": base_time,
        "additional_time": additional_time,
        "matched_services": len(matched_services),
    }

    logger.info(
        "Service duration estimated",
        description_length=len(description),
        estimated_minutes=total_minutes,
        matched_services=matched_services,
        execution_time_ms=execution_time_ms,
    )

    return result


# ---------------- Function Registration ----------------


def register_functions() -> None:
    """Register all available functions with the function registry."""
    from function_registry import FunctionDefinition, function_registry
    from function_schemas import (
        AnalyzeServiceDescriptionParams,
        EstimateServiceDurationParams,
        GetAppointmentByIdParams,
        GetCustomerAppointmentsParams,
        GetCustomerByIdParams,
        SearchCustomersParams,
        UpdateAppointmentStatusParams,
    )

    # Customer functions
    function_registry.register(
        FunctionDefinition(
            name="get_customer_by_id",
            description="Retrieve a customer by their unique ID",
            parameters_model=GetCustomerByIdParams,
            handler=get_customer_by_id_handler,
        )
    )

    function_registry.register(
        FunctionDefinition(
            name="search_customers",
            description="Search customers by email or name with partial matching",
            parameters_model=SearchCustomersParams,
            handler=search_customers_handler,
        )
    )

    # Appointment functions
    function_registry.register(
        FunctionDefinition(
            name="get_appointment_by_id",
            description="Retrieve an appointment by its unique ID",
            parameters_model=GetAppointmentByIdParams,
            handler=get_appointment_by_id_handler,
        )
    )

    function_registry.register(
        FunctionDefinition(
            name="get_customer_appointments",
            description="Get all appointments for a specific customer",
            parameters_model=GetCustomerAppointmentsParams,
            handler=get_customer_appointments_handler,
        )
    )

    function_registry.register(
        FunctionDefinition(
            name="update_appointment_status",
            description="Update the status of an existing appointment",
            parameters_model=UpdateAppointmentStatusParams,
            handler=update_appointment_status_handler,
        )
    )

    # Analysis functions
    function_registry.register(
        FunctionDefinition(
            name="analyze_service_description",
            description="Analyze a service description and extract key information",
            parameters_model=AnalyzeServiceDescriptionParams,
            handler=analyze_service_description_handler,
        )
    )

    function_registry.register(
        FunctionDefinition(
            name="estimate_service_duration",
            description="Estimate service duration based on description keywords",
            parameters_model=EstimateServiceDurationParams,
            handler=estimate_service_duration_handler,
        )
    )
