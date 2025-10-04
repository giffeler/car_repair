# Car Repair MCP Demonstrator

A production-ready FastAPI application demonstrating enterprise-grade integration between business applications and Large Language Models using the Model Context Protocol (MCP). This project showcases comprehensive error handling, structured logging, JWT authentication, rate limiting, Prometheus metrics, and intelligent service request analysis with advanced function calling capabilities using OpenAI's modern tool_calls format.

## Function Calling Support

The MCP server supports OpenAI's tool_calls format for advanced function calling, enabling multi-turn conversations with enterprise-grade error recovery. This allows the LLM to dynamically retrieve and update business data, ensuring comprehensive responses that incorporate real-time information. The implementation is fully compliant with OpenAI's latest API standards, providing robust and type-safe function execution.

### Multi-turn Conversation Flow with Error Recovery

The system implements a sophisticated conversation workflow with comprehensive error handling:

1. **Initial Request**: User sends query to the LLM.
2. **Tool Planning**: LLM determines which tools to call.
3. **Tool Execution**: Server executes functions with proper authentication, validation, and retry logic.
4. **Error Recovery**: Automatic retry for transient failures with exponential backoff.
5. **Context Integration**: Tool results are added to conversation context with execution metrics.
6. **Final Response**: LLM provides comprehensive answer incorporating all gathered data.

### Registered Functions

| Function Name | Description | Error Handling |
|---------------|-------------|---------------|
| get_customer_by_id | Retrieve a customer by primary key | Entity validation, DB retry |
| search_customers | Search customers by name or email | Parameter validation, timeout protection |
| get_appointment_by_id | Fetch appointment details by ID | Entity validation, DB retry |
| get_customer_appointments | List all appointments for a given customer | Parameter validation, result pagination |
| update_appointment_status | Modify the status of an existing appointment | Business logic validation, transaction safety |
| analyze_service_description | Extract key topics from a repair description | Input validation, complexity analysis |
| estimate_service_duration | Estimate duration from natural language text | Parameter validation, intelligent estimation |

### Enhanced Tool Call Response Format

A successful call to `/v1/chat/completions` with tool usage includes comprehensive metadata and error context:

- `choices`: Final LLM response incorporating tool results.
- `function_call_results`: List of executed tool call results with execution metrics.
- `function_call_summary`: Detailed execution statistics and performance metrics.
- `function_call_statistics`: Advanced analytics including retry patterns and error analysis.
- `initial_response`: Original response with tool calls.
- `conversation_messages`: Full conversation history.
- `request_id`: Request correlation ID for distributed tracing.

#### Example Enhanced Tool Call Result

```json
{
  "choices": [
    {
      "message": {
        "content": "Based on the customer data I retrieved, John Doe has a brake pad replacement scheduled. Given his service history and the brake inspection requirements, I estimate this will take approximately 90 minutes total."
      }
    }
  ],
  "function_call_results": [
    {
      "name": "search_customers",
      "success": true,
      "result": [{"id": 123, "name": "John Doe", "email": "john@example.com"}],
      "execution_time_ms": 45.2,
      "retry_count": 0,
      "tool_call_id": "call_abc123"
    },
    {
      "name": "estimate_service_duration", 
      "success": true,
      "result": {"estimated_minutes": 90, "complexity": "medium"},
      "execution_time_ms": 12.8,
      "retry_count": 0,
      "tool_call_id": "call_def456"
    }
  ],
  "function_call_summary": {
    "total_calls": 2,
    "successful": 2,
    "failed": 0,
    "success_rate": "100.0%",
    "execution_metrics": {
      "total_execution_time_ms": 58.0,
      "average_execution_time_ms": 29.0,
      "max_execution_time_ms": 45.2,
      "total_retries": 0
    },
    "error_summary": null
  },
  "function_call_statistics": {
    "success_rate": 1.0,
    "performance_metrics": {
      "avg_execution_time_ms": 29.0,
      "max_execution_time_ms": 45.2,
      "avg_retries_per_call": 0.0
    },
    "function_usage": {
      "search_customers": {"calls": 1, "successes": 1, "failures": 0},
      "estimate_service_duration": {"calls": 1, "successes": 1, "failures": 0}
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Example Tool Call Request

```bash
POST /v1/chat/completions
{
  "model": "gpt-4.1-mini",
  "messages": [
    {"role": "system", "content": "You are a car repair assistant with access to customer data."},
    {"role": "user", "content": "Check the status of customer john@example.com and estimate how long their brake service will take"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "search_customers",
        "description": "Search customers by email or name",
        "parameters": {
          "type": "object",
          "properties": {
            "email": {"type": "string"},
            "name": {"type": "string"}
          }
        }
      }
    }
  ]
}
```

## Key Features

- **Enterprise Error Handling**: Comprehensive exception hierarchy with structured error codes and contextual information.
- **Advanced Function Calling**: Production-ready OpenAI tool_calls integration with multi-turn conversations and retry logic.
- **Structured Logging**: Request correlation and contextual logging using Python's standard library.
- **Intelligent Data Access**: LLM can dynamically query and update business data with enhanced error recovery.
- **MCP Protocol Compliance**: Standards-compliant integration with enhanced conversation management.
- **Modern Async Architecture**: FastAPI, SQLModel, and async SQLite with comprehensive dependency injection.
- **Type-Safe Function Registry**: Enhanced dependency injection with automatic parameter validation.
- **Production Monitoring**: Request correlation, performance metrics, and detailed health reporting with Prometheus.
- **Comprehensive Testing**: Live integration tests with real OpenAI API calls and tool execution.
- **JWT Authentication**: Secure endpoint access with token-based authentication.
- **Rate Limiting**: Configurable request limits for API protection.
- **Pydantic V2 Modernization**: Future-proof schema validation with ConfigDict patterns.

## Enhanced Architecture Overview

graph TB
    A[Client] --> B[FastAPI Application]
    B --> C[Customer API]
    B --> D[Appointment API]
    B --> E[MCP Endpoint]
    C --> F[SQLModel ORM]
    D --> F
    F --> G[Async SQLite]
    E --> H[OpenAI API]
    D --> I[MCP Client]
    I --> E
    
    subgraph "Error Handling Framework"
    J[Structured Exceptions]
    K[Request Correlation]
    L[Retry Logic]
    end
    
    subgraph "Function Registry"
    M[Dependency Injection]
    N[Type-Safe Execution]
    O[Performance Monitoring]
    end
    
    subgraph "Observability"
    P[Structured Logging]
    Q[Health Monitoring]
    R[Prometheus Metrics]
    end
    
    C --> J
    D --> J
    E --> M
    E --> P
    
    subgraph "Data Layer"
    F
    G
    end
    
    subgraph "AI Integration"
    E
    H
    I
    end

https://www.mermaidchart.com/play#pako:eNp9Uk2PmzAQ_SsjDr0hbdWeclgpIZCwDRs2u7fSg2MmxF3HpoPpFlX97x1DlMjKtiMh2fM-PH74dyRtjdEsiuO4MtKag2pmlQHQYrC9m0EtGsLKjPBB2zd5FOTgZcGcrt83JNqjX6z84u5rFaVElmAtTK2VaSAjccI3S69V9M3bTvXAxGdHvXQ9YQ3pL4mtU9Z0AesLs3b4o8fOQWKJUAtPCjibkeNogI1tlDxjaOr35vvI5Kw30rvADhvVsTCwK5ixxJb1aOQAufmO8ubMRya9DC3Gz-KAPDzK_oazZU6JdLB0EkYiFNYoZ4kjeX_E7b5D-in2Sis3sDbYB85lmB1fu7m6TvXElDUK7Y635061Y0bBsSnZcbRaB7f8R3qffDbCCdiIASmwy_xMT5uCn5KG7a4IwBWD824wEpiiHP7_lM-enXPyDhm4yTX1gyclpKZurTIuANc-OP55rJ-XeQDlZ12iFV5U0whcc0YvCMTxPSz8UxGdYx-Yt61WMpxlMbISr-s7Z09I5yPhAyz9FdpxvBNbXoF00iajNuPGw9RYXhr5tZmNzdW0ScfNmtGCv3Jq5mOTTaM_fwEttimj

## Enhanced Component Breakdown

| Component | Purpose | Technology | Enhancement |
|-----------|---------|------------|-------------|
| Error Handling | Structured exception management | Custom hierarchy with error codes | Request correlation and context |
| Function Registry | Type-safe tool execution | Enhanced dependency injection | Retry logic and performance monitoring |
| Logging System | Request correlation and monitoring | Standard library structured logging | JSON output and context propagation |
| Health Monitoring | System status and component health | Comprehensive endpoint reporting | Real-time capability assessment |
| SQLModel ORM | Type-safe database operations | SQLModel + SQLAlchemy 2.0 | Transaction safety and error recovery |
| MCP Client | HTTP client for LLM communication | httpx + enhanced error handling | Timeout protection and retry logic |
| MCP Server | Local proxy to OpenAI API | OpenAI Python SDK with tool calling | Multi-turn conversation management |
| Auth System | Bearer token authentication | FastAPI dependencies with JWT | Secure token issuance and validation |
| Rate Limiting | API request control | slowapi | Configurable limits per IP |
| Metrics | Performance monitoring | prometheus_client | Request, error, and tool call metrics |

## Project Structure

car-repair-mcp-demonstrator/
├── Core Application
│   ├── car_repair_mcp_server.py    # FastAPI application entrypoint with function registration
│   ├── main_mcp.py                 # REST API endpoints (customers & appointments)
│   ├── mcp_client.py               # Enhanced HTTP client for MCP communication
│   └── mcp_server_routes.py        # Multi-turn conversation MCP endpoint with error handling
│
├── Enhanced Function Calling Engine
│   ├── function_registry.py        # Type-safe function registration with dependency injection
│   ├── function_handlers.py        # Business logic implementations with error handling
│   ├── function_schemas.py         # Pydantic V2 parameter validation schemas
│   └── process_function_calls.py   # OpenAI tool call processing with retry logic
│
├── Error Handling & Observability
│   ├── exceptions.py               # Structured exception hierarchy with error codes
│   ├── logging_config.py           # Standard library structured logging with request correlation
│   └── metrics.py                  # Prometheus metrics for monitoring
│
├── Data Layer
│   ├── database.py                 # Async database engine & session management
│   ├── models.py                   # SQLModel ORM definitions
│   ├── schemas.py                  # Pydantic V2 request/response schemas
│   └── seed.py                     # Database seeding for demo data
│
├── Authentication
│   └── session_manager.py          # JWT authentication & session management
│
├── Production Testing Suite
│   ├── test_mcp.py                 # Comprehensive tool calling integration tests
│   ├── test_runner.py              # CLI test execution
│   ├── conftest.py                 # Enhanced pytest fixtures & setup
│   └── pytest.ini                 # Pytest configuration
│
├── Configuration
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example               # Environment variables template
│   └── README.md                   # Project documentation
│
└── Documentation
    └── docs/                       # Additional documentation (if any)

## Production Enhancements

### Comprehensive Error Handling Framework

The system implements enterprise-grade error management with structured exception hierarchies and standardized error codes:
```python
try:
    result = await function_registry.execute_function(name, params, session, user)
except EntityNotFoundError as e:
    # Business logic error with detailed context
    logger.error("Entity not found", error_code=e.error_code.value, context=e.context)
    return structured_error_response(e, request_id)
except DatabaseOperationError as e:
    # Automatic retry for transient database errors
    if attempt < max_retries:
        await asyncio.sleep(retry_delay)
        continue
```

### Advanced Tool Call Processing

Enhanced retry logic with intelligent backoff strategies and comprehensive monitoring:

- Automatic Retry Logic: Transient failures automatically retry with exponential backoff.
- Timeout Protection: Configurable timeouts prevent resource exhaustion.
- Performance Monitoring: Detailed execution metrics and success rate tracking.
- Error Classification: Business logic errors vs. transient failures handled differently.
- Modern API Compliance: Uses OpenAI's tool_calls format for robust integration.

### Request Correlation and Observability

Production-ready logging and monitoring using Python's standard library and Prometheus:
```python
# Request correlation across all operations
request_id = set_request_context(req_id=str(uuid.uuid4()))
logger.info("Processing request", request_id=request_id, user_id=user.get('username'))

# Structured JSON logging for production
{
  "timestamp": "2025-07-25T10:30:00Z",
  "level": "INFO",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "function_name": "search_customers",
  "execution_time_ms": 45.2,
  "success": true
}
```

### JWT Authentication

Secure endpoint access using JSON Web Tokens (JWT):
```python
# Obtain JWT token
access_token = create_access_token(data={"sub": username})
# Use in API calls
headers = {"Authorization": f"Bearer {access_token}"}
```

### Rate Limiting

Configurable rate limits to protect API endpoints, implemented with slowapi:

- Default: 10 requests per minute per IP for /v1/chat/completions.
- Bypassed in DEBUG=true mode for testing.

### Prometheus Metrics

Exposes metrics for monitoring via /metrics endpoint:

- Request counts and error rates.
- Tool call execution statistics.
- System health status.

### Type-Safe Dependency Injection

Enhanced function registry with modern Python patterns:
```python
# Protocol-based function handler interface
class FunctionHandler(Protocol):
    async def __call__(
        self, params: BaseModel, session: AsyncSession, user: Dict[str, Any]
    ) -> Any: ...

# Automatic dependency injection and validation
async def execute_function(self, name: str, params: Dict[str, Any], 
                          session: AsyncSession, user: Dict[str, Any]) -> Any:
    validated_params = self.parameters_model(**params)
    return await self.handler(validated_params, session, user)
```

## Quick Start

### Prerequisites

- Python 3.10+ (recommended: 3.11 or 3.12).
- Virtual environment (venv, conda, or poetry).
- OpenAI API key with GPT-4 access.
- Git for cloning the repository.

### Installation

1. Clone the repository
   ```
   git clone <repository-url>
   cd car-repair-mcp-demonstrator
   ```

2. Set up virtual environment
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Configure environment
   ```
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Set up OpenAI API key and JWT secret
   ```
   export OPENAI_API_KEY="your-openai-api-key-here"
   export SECRET_KEY="your-secure-secret-key-here"
   # Or add to your .env file
   ```

### Initialize Database

```
python seed.py
```

This command will:

- Create all database tables.
- Populate with sample customers and appointments.
- Verify database connectivity.

### Start the Application

```
uvicorn car_repair_mcp_server:app --reload --host 0.0.0.0 --port 8000
```

You're ready to go! The application will be available at:

- API Base: http://localhost:8000/api/v1
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- MCP Endpoint: http://localhost:8000/v1/chat/completions
- Health Check: http://localhost:8000/v1/health
- Metrics: http://localhost:8000/metrics

## API Reference

### Authentication

Obtain a JWT token via the /api/v1/token endpoint:
```
curl -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=password"
```

Use the returned access_token in the Authorization header for all API calls:
Authorization: Bearer your-token-here

### Customer Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/customers/ | Create new customer |
| GET | /api/v1/customers/ | List customers (paginated) |
| GET | /api/v1/customers/{id} | Get customer by ID |
| PUT | /api/v1/customers/{id} | Update customer |

Example: Create Customer
```
curl -X POST "http://localhost:8000/api/v1/customers/" \
  -H "Authorization: Bearer your-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Max Mustermann",
    "email": "max@example.com", 
    "phone": "+49-123-456789"
  }'
```

### Appointment Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/appointments/ | Create new appointment |
| GET | /api/v1/appointments/ | List appointments (paginated) |
| GET | /api/v1/appointments/{id} | Get appointment by ID |
| PUT | /api/v1/appointments/{id} | Update appointment |
| POST | /api/v1/appointments/{id}/llm-process/ | AI Process appointment |

Example: AI Processing
```
curl -X POST "http://localhost:8000/api/v1/appointments/1/llm-process/" \
  -H "Authorization: Bearer your-token-here"
```

### MCP Integration

The /v1/chat/completions endpoint provides OpenAI-compatible API access with intelligent tool calling:
```
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token-here" \
  -d '{
    "model": "gpt-4.1-mini",
    "messages": [
      {"role": "system", "content": "You are a car repair assistant with access to customer data."},
      {"role": "user", "content": "Check the status of customer john@example.com and estimate how long their brake service will take"}
    ],
    "temperature": 0.2
  }'
```

### Function Registry Endpoints

List Available Functions:
```
curl http://localhost:8000/v1/functions \
  -H "Authorization: Bearer your-token-here"
```

Health Check Endpoints
The system provides comprehensive health monitoring:
```
curl http://localhost:8000/v1/health
```

Returns detailed component status including function registry health, OpenAI connectivity, database status, and system capabilities:
```
{
  "status": "healthy",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "components": {
    "function_registry": {
      "status": "healthy",
      "function_count": 7,
      "registered_functions": ["get_customer_by_id", "search_customers", "..."]
    },
    "openai_api": {
      "status": "healthy",
      "connectivity": true
    },
    "error_handling": {
      "status": "enabled",
      "structured_errors": true,
      "retry_logic": true,
      "monitoring": true
    }
  },
  "capabilities": {
    "function_calling": true,
    "multi_turn_conversations": true,
    "error_recovery": true,
    "request_correlation": true,
    "performance_monitoring": true
  }
}
```

Metrics Endpoint
Exposes Prometheus metrics for monitoring:
```
curl http://localhost:8000/metrics
```

## Curl Examples for Manual Testing

### Obtain a JWT Token

```bash
curl -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=demo&password=password"
```

### Create a Customer

```bash
curl -X POST "http://localhost:8000/api/v1/customers/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Max Mustermann",
    "email": "max@example.com",
    "phone": "+49-123-456789"
  }'
```

### Create an Appointment

```bash
curl -X POST "http://localhost:8000/api/v1/appointments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "date": "2025-12-01T10:00:00",
    "description": "Brake inspection and oil change",
    "status": "scheduled"
  }'
```

### Query Customer Details via OpenAI Function Call

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4.1-mini",
    "messages": [
      {"role": "system", "content": "You are a car repair assistant with access to customer data."},
      {"role": "user", "content": "Please get the details for customer ID 1"}
    ],
    "temperature": 0.1
  }'
```

### Process Appointment with LLM

```bash
curl -X POST "http://localhost:8000/api/v1/appointments/1/llm-process/" \
  -H "Authorization: Bearer $TOKEN"
```

### Search Customers via OpenAI

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4.1-mini",
    "messages": [
      {"role": "system", "content": "You are a car repair assistant. Use available functions to search for customers."},
      {"role": "user", "content": "Find all customers with \"Max\" in their name"}
    ],
    "temperature": 0.1
  }'
```

### Update Appointment Status via OpenAI

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4.1-mini",
    "messages": [
      {"role": "system", "content": "You are an assistant that can update appointment statuses."},
      {"role": "user", "content": "Please mark appointment 1 as completed"}
    ],
    "temperature": 0.1
  }'
```

### Check Health and Functions

**Health Check**:
```bash
curl http://localhost:8000/v1/health
```

**List Functions**:
```bash
curl http://localhost:8000/v1/functions -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting Tips

- **Authentication Errors**:
  - If `401 Unauthorized`, verify `$TOKEN` is valid (re-run Step 1).
  - Check `SECRET_KEY` in `.env`.
- **OpenAI Errors**:
  - `OPENAI_API_ERROR`: Ensure `OPENAI_API_KEY` is valid.
  - `OPENAI_RATE_LIMITED`: Wait and retry, or check API key limits.
  - Use `DEBUG=true` for detailed logs (`grep "error_code" logs/app.log`).
- **Database Issues**:
  - If `ENTITY_NOT_FOUND`, ensure customer/appointment exists (re-run `python seed.py`).
  - Check `DATABASE_URL` in `.env`.
- **Rate Limiting**:
  - If `429 Too Many Requests`, wait or set `DEBUG=true` to bypass (`slowapi` limits to 10/minute).
- **Parsing Responses**:
  - Pipe to `jq` for clarity: `curl ... | jq .`.

## Expected OpenAI Behavior

- **Function Calls**: OpenAI (`gpt-4.1-mini`) intelligently selects functions (e.g., `get_customer_by_id` for ID-based queries) based on the prompt and registered tools (`function_registry.py`).
- **Error Handling**: Errors like `ENTITY_NOT_FOUND` or `FUNCTION_PARAMETER_INVALID` are returned in `function_call_results` with detailed `error_code` and `context` (from `exceptions.py`).
- **Multi-Turn Conversations**: For complex queries (e.g., Step 5), OpenAI may chain multiple calls (e.g., `analyze_service_description` followed by `estimate_service_duration`), with results integrated into the final `content`.
- **Metrics**: Responses include `execution_time_ms`, `retry_count`, and `success_rate` for observability (`process_function_calls.py`).

## Verification

- **Run Commands**: Execute each `curl` command and verify responses match expected formats.
- **Check Logs**: Use `grep "request_id" logs/app.log` to trace requests (from `logging_config.py`).
- **Test Errors**: Try invalid inputs (e.g., non-existent customer ID) to confirm structured error responses:
  ```json
  {
    "error": "Customer with ID 999999 not found",
    "error_code": "DB_004",
    "details": {"entity_type": "Customer", "entity_id": "999999"},
    "request_id": "...",
    "timestamp": "..."
  }
  ```
  