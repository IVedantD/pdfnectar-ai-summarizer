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

# Load environment variables from .env file
load_dotenv(override=True)

app = FastAPI(title="PDFNectar AI Summarizer API", version="1.0.0")

# Configure CORS for frontend integration
origins = [
    "http://localhost:5173", # Default Vite port
    "http://localhost:8080", # Alternative Vite port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    vectorstore = get_vector_store()
    
    # Generate a unique document ID
    document_id = str(uuid.uuid4())
    
    # Save the uploaded file to a temporary location for processing and permanent location for downloading
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Prefix filename with document_id to avoid accidental overwrites of identical filenames
    safe_filename = f"{document_id}_{file.filename}"
    permanent_path = os.path.join(upload_dir, safe_filename)
    
    try:
        with open(permanent_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # We can use the permanent path for PyMuPDFLoader as well
        tmp_path = permanent_path

        # 1. Load the PDF
        loader = PyMuPDFLoader(tmp_path)
        documents = loader.load()

        # 2. Split the PDF into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True
        )
        chunks = text_splitter.split_documents(documents)
        
        # 3. Add rich metadata: document_id, source_file, and page
        for chunk in chunks:
            # PyMuPDFLoader already adds 'page' (0-indexed) to metadata by default
            # We add document_id and source_file to the existing metadata
            page_num = chunk.metadata.get('page', 0)
            # Ensure page is a clean integer representing standard 1-indexed pages for users
            display_page = int(page_num) + 1 if isinstance(page_num, int) else page_num
            
            chunk.metadata.update({
                'document_id': document_id,
                'source_file': file.filename,
                'page': display_page
            })

        # 4. Ingest into MongoDB Vector Store using Gemini Embeddings
        inserted_ids = vectorstore.add_documents(chunks)

        # 5. Save metadata using DocumentManager
        from app.core.document_manager import DocumentManager
        DocumentManager.save_metadata(document_id, {
            "original_filename": file.filename,
            "total_pages": len(documents),
            "total_chunks": len(chunks)
        })

        # 6. Generate Suggested Questions based on the initial chunks
        suggested_questions = []
        try:
            # We take the first 3 chunks (or fewer if the document is very small) as sample context
            sample_text = "\n\n".join([chunk.page_content for chunk in chunks[:3]])
            
            # Use Gemini to generate the questions
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import SystemMessage, HumanMessage
            
            # We use a simple prompt for speed and reliability during upload
            # T is set slightly higher to get variety in the questions
            question_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
            
            messages = [
                SystemMessage(content=(
                    "You are an assistant that helps users understand uploaded documents. "
                    "Based on the following excerpts from the beginning of a document, generate 3 to 5 insightful "
                    "questions that a user might want to ask about the text. "
                    "Output ONLY the questions, with one question per line, starting with a dash (-)."
                )),
                HumanMessage(content=f"Document Excerpts:\n{sample_text}")
            ]
            
            response = question_llm.invoke(messages)
            
            # Parse the response into a list of strings
            lines = response.content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    # Remove the markdown bullet and clean up whitespace
                    question = line[1:].strip()
                    if question:
                        suggested_questions.append(question)
                elif line: # Fallback if LLM ignores bullet instructions
                     suggested_questions.append(line)
                     
            # Safety fallback in case of parsing failure or empty generation
            if not suggested_questions:
                suggested_questions = [
                    "What is the main purpose of this document?",
                    "What are the key findings presented?",
                    "Could you summarize the main points?"
                ]
                
        except Exception as e:
            print(f"Warning: Failed to generate suggested questions: {e}")
            # Do not fail the whole upload just because suggestion generation failed
            suggested_questions = [
                "What is the main topic of this document?",
                "Can you provide a brief summary?",
                "What are the most important takeaways?"
            ]

        return {
            "document_id": document_id,
            "filename": safe_filename, # Return safe filename for download endpoint
            "original_filename": file.filename,
            "total_chunks": len(chunks),
            "total_pages": len(documents),
            "suggested_questions": suggested_questions[:5] # Enforce max 5
        }
        
    except Exception as e:
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
        filename=filename.split("_", 1)[-1] # Strip the UUID for a clean user download name
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
    query: str
    session_id: str
    document_id: str
    user_query: str = ""  # Raw user question for embedding/retrieval (separate from the full prompt)

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
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
             
    try:
        from app.services.router_service import RouterService
        router = RouterService()

        # The router handles the decision between RAG and PageIndex, including fallback logic
        result = await router.route_query(
            user_query=request.user_query,
            full_query=request.query,
            session_id=request.session_id,
            document_id=request.document_id
        )

        # Construct the public PDF URL (using any retrieved doc metadata if needed, 
        # but for now we can reconstruct from document_id if we have it or use a default)
        from app.core.document_manager import DocumentManager
        metadata = DocumentManager.get_metadata(request.document_id)
        filename = metadata.get("original_filename", "document.pdf") if metadata else "document.pdf"
        safe_filename = f"{request.document_id}_{filename}"
        pdf_url = f"/api/download/{safe_filename}"

        return {
            "response": result["response"],
            "pages": result["pages"],
            "source": result.get("source", "hybrid"),
            "pdf_url": pdf_url,
            "session_id": request.session_id,
            "document_id": request.document_id
        }
    except Exception as e:
        import traceback
        print("\n--- ERROR IN /api/chat ---")
        traceback.print_exc()
        print(f"Exception details: {str(e)}")
        print("----------------------------\n")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        print("\n--- ERROR IN /api/chat ---")
        traceback.print_exc()
        print(f"Exception details: {str(e)}")
        print("----------------------------\n")
        raise HTTPException(status_code=500, detail=str(e))

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
