import logging
import time
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.v0 import api_router
from app.core.config import settings
from app.core.middleware import apply_middlewares
from fastapi.openapi.utils import get_openapi


logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="WiMi Backend API built with FastAPI and Supabase",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

apply_middlewares(app)              # wires up CORS & GZip

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all HTTP requests with timing information.
    
    Args:
        request (Request): The incoming request
        call_next (Callable): The next middleware or route handler
        
    Returns:
        Response: The response from the next handler
        
    Note:
        Adds X-Process-Time-ms header to responses with processing time in milliseconds
    """
    start_ts = time.time()
    # capture optional Idempotency-Key header
    idem_key = request.headers.get("Idempotency-Key", "-")
    try:
        response = await call_next(request)
    except Exception as exc:
        # log unexpected errors
        elapsed = (time.time() - start_ts) * 1000
        logger.exception(
            f"{request.method} {request.url.path} idem={idem_key} "
            f"failed_in={elapsed:.2f}ms error={exc}"
        )
        raise
    elapsed = (time.time() - start_ts) * 1000
    logger.info(
        f"{request.method} {request.url.path} idem={idem_key} "
        f"completed_in={elapsed:.2f}ms status_code={response.status_code}"
    )
    response.headers["X-Process-Time-ms"] = f"{elapsed:.2f}"
    return response

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Health"])
def root():
    """
    Root endpoint providing basic API information.
    
    Returns:
        dict: Basic information about the API
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.ENVIRONMENT != "production" else None,
    }

@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint for monitoring systems.
    
    Returns:
        dict: Health status of the API
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Global exception handler for HTTPExceptions.
    
    Args:
        request (Request): The request that caused the exception
        exc (HTTPException): The exception raised
        
    Returns:
        JSONResponse: A formatted error response
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Exception handler for request validation errors.
    
    Args:
        request (Request): The request that caused the exception
        exc (RequestValidationError): The validation error details
        
    Returns:
        JSONResponse: A detailed error response with validation issues
    """
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.on_event("startup")
async def on_startup():
    """
    Handler for application startup events.
    Initializes connections and resources.
    """
    logger.info("🚀 Application starting up")

@app.on_event("shutdown")
async def on_shutdown():
    """
    Handler for application shutdown events.
    Cleans up resources and connections.
    """
    logger.info("🛑 Application shutting down")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENVIRONMENT == "development",
    )
    
def get_openapi_schema():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="WiMi Backend API built with FastAPI and Supabase",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    # Apply bearerAuth globally (all routes)
    openapi_schema["security"] = [{"bearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = get_openapi_schema
