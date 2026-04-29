import logging
import sys
import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Centralized Logging Configuration
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s [req_id=%(req_id)s doc_id=%(doc_id)s user_id=%(user_id)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout
    )

    # Filter to ensure req_id, doc_id, user_id are always present in record
    class ContextFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, "req_id"): record.req_id = "N/A"
            if not hasattr(record, "doc_id"): record.doc_id = "N/A"
            if not hasattr(record, "user_id"): record.user_id = "N/A"
            return True

    for handler in logging.root.handlers:
        handler.addFilter(ContextFilter())

logger = logging.getLogger("pdfnectar")

# Middleware for Request Correlation ID
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        # Store request_id in request state for later use
        request.state.request_id = request_id
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        return response

# Middleware for Request Size Limiting
class RequestSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("Content-Length")
            if content_length and int(content_length) > 6 * 1024 * 1024:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=413, 
                    content={"detail": "Request entity too large. Max allowed is 6MB."}
                )
        return await call_next(request)
