"""
seed.py

Seeds the development or test database with example customers and appointments.
Intended for test/dev/demo environments only.
"""

import asyncio
import logging
from typing import List

from faker import Faker
from sqlmodel.ext.asyncio.session import AsyncSession

from database import drop_db, engine, init_db
from models import Appointment, Customer

fake = Faker("de_DE")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("seed")

NUM_CUSTOMERS = 5
APPOINTMENTS_PER_CUSTOMER = 2


async def seed_db() -> None:
    """
    Recreate all tables and populate the database with demo data.
    Idempotent: Can be run repeatedly. Uses explicit commits for transaction safety per logical group (customers, then appointments) to ensure atomicity without nesting conflicts.
    """
    logger.info("Seeding database: dropping and recreating all tables.")
    await drop_db()
    await init_db()

    async with AsyncSession(engine) as session:
        # Add customers and commit atomically
        customers: List[Customer] = []
        for _ in range(NUM_CUSTOMERS):
            customer = Customer(
                name=fake.name(),
                email=fake.unique.email(),
                phone=fake.phone_number(),
            )
            session.add(customer)
            customers.append(customer)
        await session.commit()  # Commit customers group

        # Refresh to get IDs post-commit
        for customer in customers:
            await session.refresh(customer)

        # Add appointments and commit atomically
        for customer in customers:
            for _ in range(APPOINTMENTS_PER_CUSTOMER):
                appointment = Appointment(
                    customer_id=customer.id,
                    date=fake.date_time_this_year(),
                    description=fake.sentence(nb_words=5),
                    status="scheduled",
                )
                session.add(appointment)
        await session.commit()  # Commit appointments group

    logger.info(
        "Seeding complete. %d customers, %d appointments.",
        NUM_CUSTOMERS,
        NUM_CUSTOMERS * APPOINTMENTS_PER_CUSTOMER,
    )


if __name__ == "__main__":
    asyncio.run(seed_db())
