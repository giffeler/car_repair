"""
models.py

Defines SQLModel ORM entities for the car repair domain.
Classic SQLModel relationship syntax is used.
"""

from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Customer(SQLModel, table=True):
    """
    Customer entity representing a car repair client.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=128)
    email: str = Field(index=True, unique=True, min_length=5, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)

    appointments: List["Appointment"] = Relationship(back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}', email='{self.email}')>"


class Appointment(SQLModel, table=True):
    """
    Appointment entity representing a repair/service booking.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    date: datetime = Field(index=True)
    description: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="scheduled", max_length=32)

    customer: Optional[Customer] = Relationship(back_populates="appointments")

    def __repr__(self) -> str:
        return (
            f"<Appointment(id={self.id}, customer_id={self.customer_id}, "
            f"date={self.date.isoformat()}, status={self.status})>"
        )
