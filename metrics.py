"""
metrics.py

Prometheus metrics collection for the Car Repair MCP server.
"""

from fastapi import Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
ERROR_COUNT = Counter("errors_total", "Total errors by code", ["error_code"])

# Function call metrics
FUNCTION_CALL_COUNT = Counter(
    "function_calls_total", "Total function calls", ["function_name", "success"]
)
FUNCTION_RETRY_COUNT = Histogram(
    "function_retries",
    "Function call retries",
    ["function_name"],
    buckets=[0, 1, 2, 3, 5],
)
SYSTEM_HEALTH = Gauge(
    "system_health", "Overall system health (1=healthy, 0=degraded)"
)


def metrics_endpoint() -> Response:
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")
