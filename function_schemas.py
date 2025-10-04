"""
function_schemas.py

Defines parameter and result schemas for all OpenAI-callable functions
in the Car Repair MCP demonstrator.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field

# --------------------- Customer Functions ---------------------


class GetCustomerByIdParams(BaseModel):
    """Parameters for retrieving a customer by ID."""

    customer_id: int = Field(
        ...,
        ge=1,
        description="The unique ID of the customer to retrieve.",
        examples=[1, 2, 42],
    )


class SearchCustomersParams(BaseModel):
    """Parameters for searching customers by email or name."""

    email: Optional[EmailStr] = Field(
        None,
        description="Filter customers by exact email address.",
        examples=["john.doe@example.com", "customer@shop.com"],
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=128,
        description="Filter customers by name (partial matches allowed).",
        examples=["John", "Smith", "Jane Doe"],
    )


# --------------------- Appointment Functions ---------------------


class GetAppointmentByIdParams(BaseModel):
    """Parameters for retrieving an appointment by ID."""

    appointment_id: int = Field(
        ...,
        ge=1,
        description="The unique ID of the appointment to retrieve.",
        examples=[1, 5, 123],
    )


class GetCustomerAppointmentsParams(BaseModel):
    """Parameters for retrieving all appointments for a customer."""

    customer_id: int = Field(
        ...,
        ge=1,
        description="The unique ID of the customer whose appointments to retrieve.",
        examples=[1, 2, 42],
    )


class UpdateAppointmentStatusParams(BaseModel):
    """Parameters for updating an appointment's status."""

    appointment_id: int = Field(
        ...,
        ge=1,
        description="The unique ID of the appointment to update.",
        examples=[1, 5, 123],
    )
    status: Literal[
        "scheduled",
        "confirmed",
        "in_progress",
        "completed",
        "cancelled",
        "rescheduled",
    ] = Field(
        ...,
        description="The new status for the appointment.",
        examples=["confirmed", "completed", "cancelled"],
    )


# --------------------- Analysis Functions ---------------------


class AnalyzeServiceDescriptionParams(BaseModel):
    """Parameters for analyzing a service description."""

    description: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The textual service request description to analyze.",
        examples=[
            "Check brakes and replace brake pads",
            "Oil change and tire rotation",
            "Engine diagnostic for strange noise",
        ],
    )


class EstimateServiceDurationParams(BaseModel):
    """Parameters for estimating service duration."""

    description: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="The service description to estimate duration for.",
        examples=[
            "Brake inspection and pad replacement",
            "Complete engine tune-up",
            "Tire mounting and balancing",
        ],
    )


# --------------------- Response Schemas ---------------------


class ServiceAnalysisResult(BaseModel):
    """Result schema for service description analysis."""

    summary: str = Field(
        ..., description="Human-readable summary of the service"
    )
    keywords: List[str] = Field(
        ..., description="Key terms extracted from description"
    )
    complexity: Literal["simple", "medium", "complex"] = Field(
        ..., description="Estimated complexity level"
    )


class DurationEstimateResult(BaseModel):
    """Result schema for service duration estimation."""

    estimated_minutes: int = Field(
        ..., ge=0, description="Estimated duration in minutes"
    )


class FunctionCallError(BaseModel):
    """Schema for function call errors."""

    error: str = Field(
        ..., description="Error message describing what went wrong"
    )
    function_name: str = Field(
        ..., description="Name of the function that failed"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
