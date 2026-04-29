import os
import tempfile
import uuid
import logging
import asyncio
import time
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks, Security, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.logger import setup_logging, CorrelationIdMiddleware, RequestSizeMiddleware
from app.core.auth import get_current_user
from app.core.supabase import supabase
from app.core.document_manager import DocumentManager
from app.services.document_service import DocumentService
from app.services.router_service import RouterService
from app.services.chart_validator import ChartValidator
from app.services.numeric_detector import user_requests_visualization
from database import MONGO_URI, DB_NAME, METADATA_COLLECTION

# 1. Initialize Logging
setup_logging()
logger = logging.getLogger("pdfnectar.main")
server_start_time = time.time()

# 2. Rate Limiting Setup
def get_user_or_ip(request: Request):
    user = getattr(request.state, "user", None)
    if user:
        return user.id
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_or_ip)
app = FastAPI(title="PDFNectar AI Summarizer API", version="2.4.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 3. Custom Auth Middleware (for Rate Limiting & Pre-auth)
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Exclude public paths from pre-auth
        if request.url.path in ["/api/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # We do a fast check without the full FastAPI dependency overhead
                user_response = supabase.auth.get_user(token)
                if user_response and user_response.user:
                    request.state.user = user_response.user
            except:
                pass # Will be caught by Depends(get_current_user) in routes
        return await call_next(request)

app.add_middleware(AuthMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestSizeMiddleware)

# 4. Middleware & Security
_trusted_hosts_env = os.getenv("TRUSTED_HOSTS", "")
if _trusted_hosts_env and "*" not in _trusted_hosts_env:
    ALLOWED_HOSTS = _trusted_hosts_env.split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

# Restrictive CORS for production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)

# Constants
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "100"))

# 5. Standardized Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "N/A")
    logger.error(f"Unhandled exception [req_id={req_id}]: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "code": "INTERNAL_SERVER_ERROR", "request_id": req_id}
    )

@app.get("/")
def read_root():
    return {"message": "PDFNectar AI Summarizer API v2.4.0 (Production Core)"}

@app.get("/api/health")
async def health_check():
    """Hardened health check for all dependencies."""
    async def check_mongo():
        try:
            await asyncio.to_thread(METADATA_COLLECTION.find_one, {})
            return "up"
        except: return "down"

    async def check_supabase():
        try:
            await asyncio.to_thread(supabase.storage.list_buckets)
            return "up"
        except: return "down"

    results = await asyncio.gather(check_mongo(), check_supabase(), return_exceptions=True)
    
    status = {
        "status": "online",
        "uptime": f"{int(time.time() - server_start_time)}s",
        "dependencies": {
            "mongodb": results[0] if not isinstance(results[0], Exception) else "down",
            "supabase": results[1] if not isinstance(results[1], Exception) else "down"
        }
    }
    
    if "down" in status["dependencies"].values():
        status["status"] = "degraded"
        status["failed_services"] = [k for k, v in status["dependencies"].items() if v == "down"]
        return JSONResponse(status_code=503, content=status)
        
    return status

@app.post("/api/upload")
@limiter.limit("10/minute")
async def upload_pdf(
    request: Request, 
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    req_id = request.state.request_id
    extra = {"req_id": req_id, "user_id": user.id}
    
    # 1. Defensive Validation
    if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Only standard PDFs are allowed.",
            headers={"code": "INVALID_FILE_TYPE"}
        )
    
    # 2. Memory-Safe Buffered Read
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413, 
            detail="File too large. Max 5MB allowed.",
            headers={"code": "FILE_TOO_LARGE"}
        )
    
    document_id = str(uuid.uuid4())
    logger.info(f"Upload initiated: {file.filename}", extra={**extra, "doc_id": document_id})

    # 3. Path Sanitization & Persistence
    safe_filename = "".join([c for c in file.filename if c.isalnum() or c in "._-"])
    storage_path = f"{document_id}_{safe_filename}"
    
    # 4. Atomic Initialization (Primary Record)
    await asyncio.to_thread(DocumentManager.initialize_status, document_id, file.filename, user.id)

    try:
        # 5. Supabase Persistence
        await asyncio.to_thread(
            supabase.storage.from_("pdfs").upload,
            path=storage_path,
            file=content,
            file_options={"content-type": "application/pdf"}
        )
        
        # 6. Trigger Asynchronous Processing
        temp_dir = os.path.join(tempfile.gettempdir(), "pdfnectar")
        
        def save_temp_file():
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = os.path.join(temp_dir, storage_path)
            with open(temp_file_path, "wb") as f:
                f.write(content)
            return temp_file_path

        temp_file_path = await asyncio.to_thread(save_temp_file)

        background_tasks.add_task(
            DocumentService.process_and_ingest_pdf, 
            temp_file_path, 
            document_id, 
            file.filename
        )

        return {
            "document_id": document_id,
            "status": "processing",
            "message": "File uploaded and processing started."
        }
        
    except Exception as e:
        logger.error(f"Upload flow failed: {str(e)}", extra=extra, exc_info=True)
        await asyncio.to_thread(DocumentManager.update_status, document_id, "failed", error="Storage upload failed")
        raise HTTPException(
            status_code=500, 
            detail="Failed to persist document.",
            headers={"code": "STORAGE_FAILURE"}
        )

@app.get("/api/status/{document_id}")
async def get_document_status(document_id: str, user=Depends(get_current_user)):
    """Poll document status securely."""
    metadata = DocumentManager.get_metadata_for_user(document_id, user.id)
    if not metadata:
        raise HTTPException(
            status_code=404, 
            detail="Document not found or access denied.",
            headers={"code": "DOCUMENT_NOT_FOUND"}
        )
    return metadata

@app.post("/api/chat")
@limiter.limit("5/minute")
async def chat_with_docs(request: Request, chat_req: dict, user=Depends(get_current_user)):
    document_id = chat_req.get("document_id")
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")

    # Verify ownership and status
    metadata = DocumentManager.get_metadata_for_user(document_id, user.id)
    if not metadata:
        raise HTTPException(status_code=403, detail="Unauthorized access to document", headers={"code": "UNAUTHORIZED"})
    
    if metadata.get("status") != "completed":
        return JSONResponse(
            status_code=409, 
            content={"detail": "Document is still processing.", "code": "DOCUMENT_NOT_READY"}
        )

    try:
        router = RouterService()
        result = await asyncio.wait_for(
            router.route_query(
                user_query=chat_req.get("user_query", ""),
                full_query=chat_req.get("query", ""),
                session_id=chat_req.get("session_id", ""),
                document_id=document_id,
                mode=chat_req.get("mode", "chat"),
                language=chat_req.get("language", "English"),
                length=chat_req.get("length", "medium")
            ),
            timeout=45.0
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"AI Timeout for {document_id}", extra={"doc_id": document_id, "user_id": user.id})
        return JSONResponse(
            status_code=504, 
            content={"detail": "LLM response timed out.", "code": "AI_TIMEOUT"}
        )
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}", extra={"doc_id": document_id, "user_id": user.id}, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal chat error", headers={"code": "CHAT_ERROR"})

@app.get("/api/download/{document_id}")
async def download_pdf(document_id: str, user=Depends(get_current_user)):
    """Securely proxy PDF download from Supabase with ownership check."""
    try:
        metadata = DocumentManager.get_metadata_for_user(document_id, user.id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Document not found", headers={"code": "DOCUMENT_NOT_FOUND"})
        
        files = supabase.storage.from_("pdfs").list(path="")
        target_file = next((f["name"] for f in files if f["name"].startswith(document_id)), None)
        
        if not target_file:
            raise HTTPException(status_code=404, detail="File missing from storage", headers={"code": "FILE_MISSING"})
            
        res = supabase.storage.from_("pdfs").create_signed_url(target_file, 3600)
        return {"url": res["signedURL"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed for {document_id}: {str(e)}", extra={"doc_id": document_id, "user_id": user.id})
        raise HTTPException(status_code=500, detail="Failed to retrieve download link", headers={"code": "DOWNLOAD_ERROR"})

@app.get("/api/history/{session_id}")
async def get_chat_history(session_id: str, user=Depends(get_current_user)):
    """Fetch chat history with auth verification."""
    try:
        from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
        history = MongoDBChatMessageHistory(
            MONGO_URI, 
            session_id, 
            database_name=DB_NAME, 
            collection_name="chat_histories"
        )
        # Note: In a full-scale app, session_id would be tied to user_id in a metadata collection
        formatted_messages = []
        for msg in history.messages:
            formatted_messages.append({
                "role": "user" if msg.type == "human" else "ai",
                "content": msg.content
            })
        return {"session_id": session_id, "messages": formatted_messages}
    except Exception as e:
        logger.error(f"History fetch failed for {session_id}: {str(e)}", extra={"user_id": user.id})
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history", headers={"code": "HISTORY_ERROR"})
