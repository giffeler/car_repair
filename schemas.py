"""
schemas.py

Defines Pydantic schemas for input/output validation in the Car Repair MCP API.
Modernized for Pydantic V2 with ConfigDict and updated field validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    """Base fields for a customer with Pydantic V2 configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Max Mustermann",
                    "email": "max@example.com",
                    "phone": "+49-123-4567",
                }
            ]
        }
    )

    name: str = Field(..., min_length=1, max_length=128)
    email: EmailStr = Field(...)
    phone: Optional[str] = Field(None, max_length=32)


class CustomerCreate(CustomerBase):
    """Fields required to create a customer."""

    pass


class CustomerUpdate(BaseModel):
    """Fields allowed for customer update."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Erika Musterfrau",
                    "email": "erika@example.com",
                    "phone": "+49-987-6543",
                }
            ]
        }
    )

    name: Optional[str] = Field(None, min_length=1, max_length=128)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=32)


class CustomerRead(CustomerBase):
    """Customer fields returned in API responses."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "name": "Max Mustermann",
                    "email": "max@example.com",
                    "phone": "+49-123-4567",
                }
            ]
        }
    )

    id: int


class AppointmentBase(BaseModel):
    """Base fields for an appointment with Pydantic V2 configuration."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "date": "2025-01-01T09:00:00",
                    "description": "Oil change",
                    "status": "scheduled",
                }
            ]
        }
    )

    date: datetime = Field(...)
    description: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field("scheduled", max_length=32)


class AppointmentCreate(AppointmentBase):
    """Fields required to create an appointment."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "customer_id": 1,
                    "date": "2025-01-01T09:00:00",
                    "description": "Oil change",
                    "status": "scheduled",
                }
            ]
        }
    )

    customer_id: int = Field(...)


class AppointmentUpdate(BaseModel):
    """Fields allowed for appointment update."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "description": "Update: new tires and alignment",
                    "status": "rescheduled",
                }
            ]
        }
    )

    date: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=32)


class AppointmentRead(AppointmentBase):
    """Appointment fields returned in API responses."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "customer_id": 1,
                    "date": "2025-01-01T09:00:00",
                    "description": "Oil change",
                    "status": "scheduled",
                }
            ]
        }
    )

    id: int
    customer_id: int
