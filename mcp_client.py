"""
mcp_client.py

Updated implementation using explicit HTTP calls to a standalone MCP server,
with JWT authentication for function calling responses.
"""

import logging
import os
from typing import Any, Dict

import httpx

from models import Appointment

logger = logging.getLogger("mcp_client")

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
MCP_MODEL = os.getenv("MCP_MODEL", "gpt-4.1-mini")


async def get_jwt_token() -> str:
    """
    Obtain a JWT token from the /api/v1/token endpoint.

    Returns:
        str: JWT access token.

    Raises:
        RuntimeError: If token request fails or response is invalid.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/api/v1/token",
                data={"username": "demo", "password": "password"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            response.raise_for_status()
            token_data = response.json()
            if (
                not isinstance(token_data, dict)
                or "access_token" not in token_data
            ):
                raise RuntimeError(
                    "Invalid token response: missing 'access_token'"
                )
            if not isinstance(token_data["access_token"], str):
                raise RuntimeError(
                    "Invalid token response: 'access_token' is not a string"
                )
            return token_data["access_token"]
    except httpx.HTTPError as exc:
        logger.error("Token request failed: %s", exc, exc_info=True)
        raise RuntimeError("Failed to obtain JWT token") from exc


async def process_with_llm(appointment: Appointment) -> Dict[str, Any]:
    """
    Sends appointment data to the MCP server endpoint and returns the result.
    Uses JWT authentication for requests.

    Args:
        appointment (Appointment): The appointment ORM object.

    Returns:
        Dict[str, Any]: Parsed response from the MCP server.

    Raises:
        RuntimeError: If MCP server API call fails.
    """
    prompt = (
        f"A customer (ID: {appointment.customer_id}) has an appointment for: "
        f"{appointment.description or 'No details provided.'} on {appointment.date.isoformat()}.\n"
        "Analyze this service request and provide recommendations. "
        "Use available functions to get customer details and estimate service duration if helpful."
    )
    logger.info("Sending prompt to MCP server: %s", prompt)

    try:
        token = await get_jwt_token()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/v1/chat/completions",
                json={
                    "model": MCP_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a car repair service assistant with access to customer and appointment data.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            # Handle both function calling and regular responses
            if "function_call_results" in result:
                choices = result.get("choices", [])
                content = (
                    choices[0]["message"]["content"]
                    if choices
                    else "Function calls executed successfully"
                )
                return {
                    "content": content,
                    "raw_response": result,
                    "function_calls": result["function_call_results"],
                }
            elif "choices" in result:
                content = result["choices"][0]["message"]["content"]
                return {
                    "content": content,
                    "raw_response": result,
                    "function_calls": [],
                }
            else:
                return {
                    "content": str(result),
                    "raw_response": result,
                    "function_calls": [],
                }

    except httpx.HTTPError as exc:
        logger.error("MCP server request failed: %s", exc, exc_info=True)
        raise RuntimeError("MCP processing failed") from exc
