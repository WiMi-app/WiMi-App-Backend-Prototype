import logging
import time
import uvicorn

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.v0 import api_router
from app.core.config import settings
from app.core.middleware import apply_middlewares


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
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.ENVIRONMENT != "production" else None,
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Application starting up")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("🛑 Application shutting down")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENVIRONMENT == "development",
    )
