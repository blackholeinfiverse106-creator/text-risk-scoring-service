from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class ErrorBoundaryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled Exception: {str(e)}")
            # Zero unhandled 500 exceptions on malformed inputs -> return 400 Bad Request
            return JSONResponse(
                status_code=400,
                content={
                    "error": "true",
                    "message": "Error boundary caught an unhandled exception",
                    "details": str(e)
                }
            )
