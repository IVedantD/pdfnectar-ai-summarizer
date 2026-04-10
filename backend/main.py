import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import shutil
import tempfile
import uuid
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import from our database module
from database import get_vector_store
from app.services.chart_validator import ChartValidator

# Load environment variables from .env file
load_dotenv(override=True)

app = FastAPI(title="PDFNectar AI Summarizer API", version="1.0.0")

# Configure CORS for frontend integration
origins = [
    "http://localhost:5173", # Default Vite port
    "http://localhost:8080", # Alternative Vite port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to PDFNectar AI Summarizer API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

def cleanup_old_uploads(upload_dir: str, max_files: int = 50):
    """Deletes old files if the directory exceeds the max_files limit."""
    if not os.path.exists(upload_dir):
        return
    files = [os.path.join(upload_dir, f) for f in os.listdir(upload_dir) if f.endswith('.pdf')]
    if len(files) > max_files:
        files.sort(key=lambda x: os.path.getctime(x))
        for f in files[:len(files) - max_files]:
            try:
                os.remove(f)
            except Exception:
                pass

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only standard PDFs are allowed.")
        
    if file.size and file.size > MAX_FILE_SIZE:
         raise HTTPException(status_code=413, detail="File is too large. Max size is 50MB.")

    vectorstore = get_vector_store()
    
    # Generate a unique document ID
    document_id = str(uuid.uuid4())
    
    # Save the uploaded file to a temporary location for processing and permanent location for downloading
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Prefix filename with document_id to avoid accidental overwrites of identical filenames
    safe_filename = f"{document_id}_{file.filename}"
    permanent_path = os.path.join(upload_dir, safe_filename)
    
    # Trigger cleanup dynamically before saving the new file
    cleanup_old_uploads(upload_dir)
    
    try:
        import aiofiles
        async with aiofiles.open(permanent_path, "wb") as buffer:
            await buffer.write(await file.read())
            
        # Delegate heavy lifting to explicitly tailored service layer
        from app.services.document_service import DocumentService
        result = DocumentService.process_and_ingest_pdf(permanent_path, document_id, file.filename)

        print(f"\n[UPLOAD] Successfully processed document: {file.filename}")
        print(f"[UPLOAD] Generated document_id: {document_id}")
        
        return {
            "document_id": document_id,
            "filename": safe_filename, # Return safe filename for download endpoint
            "original_filename": file.filename,
            "total_chunks": result["total_chunks"],
            "total_pages": result["total_pages"],
            "suggested_questions": result["suggested_questions"]
        }
        
    except ValueError as ve:
        print(f"Known Processing Error: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        import uvicorn
        # Trigger uvicorn reload to fetch new .env values
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
        import traceback
        print("\n--- ERROR IN /api/upload ---")
        traceback.print_exc()
        print(f"Exception details: {str(e)}")
        print("----------------------------\n")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
        
    finally:
        # We don't remove the temporary file since we are saving it permanently now for download
        pass


@app.get("/api/download/{filename}")
async def download_pdf(filename: str):
    """Returns a previously uploaded PDF file"""
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    file_path = os.path.join(upload_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename.split("_", 1)[-1], # Strip the UUID for a clean user download name
        content_disposition_type="inline"
    )


# --- Chat & RAG Setup ---
from pydantic import BaseModel
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_core.documents import Document
from typing import List

# Import db connection configuration constants
from database import MONGO_URI, DB_NAME

class ChatRequest(BaseModel):
    query: str = "" # Still accepted but safely ignored by backend
    session_id: str
    document_id: str
    user_query: str = ""  
    mode: str = "chat"
    language: str = "English"
    length: str = "medium"

def get_session_history(session_id: str):
    """Retrieves or creates the chat history for a specific session ID stored in MongoDB."""
    return MongoDBChatMessageHistory(
        MONGO_URI, 
        session_id, 
        database_name=DB_NAME, 
        collection_name="chat_histories"
    )

@app.post("/api/chat")
async def chat_with_docs(request: ChatRequest):
    actual_query = request.user_query if request.user_query else request.query
    if not actual_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
             
    try:
        from app.services.router_service import RouterService
        from app.core.prompts import build_prompt
        router = RouterService()

        # Securely build prompt on backend based on the mode requested
        full_safe_query = build_prompt(
            user_query=actual_query, 
            mode=request.mode, 
            language=request.language, 
            length=request.length
        )

        # The router handles the decision between RAG and PageIndex, including fallback logic
        result = await router.route_query(
            user_query=actual_query,
            full_query=full_safe_query, # Send the safe backend prompt to LangChain
            session_id=request.session_id,
            document_id=request.document_id,
            mode=request.mode
        )

        # Construct the public PDF URL (using any retrieved doc metadata if needed, 
        # but for now we can reconstruct from document_id if we have it or use a default)
        from app.core.document_manager import DocumentManager
        metadata = DocumentManager.get_metadata(request.document_id)
        filename = metadata.get("original_filename", "document.pdf") if metadata else "document.pdf"
        safe_filename = f"{request.document_id}_{filename}"
        pdf_url = f"/api/download/{safe_filename}"
        
        # VALIDATION LAYER
        # Validate any charts in the response to ensure they are fully grounded in the document context
        context_str = result.get("context_str", "")
        validated_response = ChartValidator.validate(result["response"], context_str)
        
        # UI Polish: if the AI was scared to make a chart and apologized at the end, clean it up
        scared_apology = "The document does not provide enough information to generate a chart."
        if validated_response.strip().endswith(scared_apology):
            validated_response = validated_response.replace(scared_apology, "").strip()

        return {
            "response": validated_response,
            "pages": result["pages"],
            "source": result.get("source", "hybrid"),
            "pdf_url": pdf_url,
            "session_id": request.session_id,
            "document_id": request.document_id
        }
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        import traceback
        error_msg = str(e).lower()
        print(f"\n--- ERROR IN /api/chat: {str(e)} ---")
        
        if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
            return {"response": "AI Provider Rate Limit reached (Free Tier). This usually means the current model is under high traffic. Please wait 60 seconds or try a different model in your .env file.", "pages": [], "source": "error_rate_limit"}
            
        traceback.print_exc()
        return {"response": "Sorry, I encountered an error while answering that question. Please try again in 30 seconds.", "pages": [], "source": "error"}


@app.get("/api/history/{session_id}")
async def get_chat_history(session_id: str):
    """Fetch chat history to hydrate the frontend UI on load"""
    try:
        history = get_session_history(session_id)
        # Convert Langchain messages to simple dicts for the frontend
        formatted_messages = []
        for msg in history.messages:
            formatted_messages.append({
                "role": "user" if msg.type == "human" else "ai",
                "content": msg.content
            })
        return {"session_id": session_id, "messages": formatted_messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
