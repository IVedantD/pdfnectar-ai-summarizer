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

        # 5. Generate Suggested Questions based on the initial chunks
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
        vectorstore = get_vector_store()
        
        # 1. Configure the retriever with a filter using the document_id
        # We increase k to 10 to fetch more candidates before re-ranking/grouping
        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": 5,
                "pre_filter": {
                    "document_id": {"$eq": request.document_id}
                }
            }
        )

        # 2. Initialize the Gemini LLM
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

        
        # 3. Define a strict System Prompt — no inline citations, clean readable answers
        system_prompt = (
            "You are PDF Nectar, an expert AI assistant tasked with answering questions strictly based on the provided document excerpts. "
            "Follow these rules strictly:\n"
            "1. ONLY use the information provided in the Context below. Do not use outside knowledge or hallucinate information.\n"
            "2. If the answer cannot be found in the Context, politely state: 'I cannot find the answer to this question in the provided document.'\n"
            "3. Do NOT insert any page citations, source references, or page numbers inside your answer text.\n"
            "4. Do NOT write (Source: Page X), [Source: Page X], or any similar inline citation.\n"
            "5. Do NOT add a Sources or References section at the end — the system will add sources automatically.\n"
            "6. Write clean, natural, readable answers like modern AI assistants (ChatGPT, Perplexity).\n"
            "7. Keep your answers clear, professional, and well-structured, using markdown if helpful.\n\n"
            "Context Information:\n{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ])
        
        def group_and_format_docs(docs: List[Document], max_pages: int = 5) -> dict:
            """
            Groups text chunks by page, selects the top N relevant pages, 
            and returns the formatted context string alongside unique page numbers.
            """
            from collections import defaultdict
            
            # Group chunks by their page number.
            # Because MongoDB Atlas returns documents in order of vector similarity,
            # the first time we encounter a page, we consider that page's relevance score.
            page_groups = defaultdict(list)
            ordered_pages = [] # Keep track of relevance order
            
            for d in docs:
                page = d.metadata.get('page', 'Unknown')
                text = d.page_content.strip()
                
                if page not in page_groups:
                    ordered_pages.append(page)
                
                page_groups[page].append(text)

            # Take the top N most relevant distinct pages
            top_pages = ordered_pages[:max_pages]
            
            formatted_chunks = []
            final_pages = set()
            
            for page in top_pages:
                if page != 'Unknown':
                    final_pages.add(page)
                    
                # Join all chunks from the same page into one cohesive block
                combined_text = "\n...\n".join(page_groups[page])
                formatted_chunks.append(f"--- Excerpt from Page {page} ---\n{combined_text}\n")
            
            return {
                "context_str": "\n".join(formatted_chunks),
                "source_pages": sorted(list(final_pages))
            }

        # 5. Build the LangChain pipeline
        # We use a custom function to handle the extraction of docs and passing them to the prompt
        def setup_and_invoke_chain(retrieved_docs, query, session_id):
            doc_data = group_and_format_docs(retrieved_docs, max_pages=5)
            context_str = doc_data["context_str"]
            source_pages = doc_data["source_pages"]
            
            # Create a simple chain just for the LLM resolution 
            # (bypassing the standard retriever | format pipe so we can keep the pages variable)
            core_chain = prompt | llm | StrOutputParser()
            
            # Wrap for history
            chain_with_history = RunnableWithMessageHistory(
                core_chain,
                get_session_history,
                input_messages_key="question",
                history_messages_key="history",
            )
            
            # Generate the LLM answer
            ai_answer = chain_with_history.invoke(
                {"context": context_str, "question": query},
                config={"configurable": {"session_id": session_id}}
            )
            
            return ai_answer, source_pages

        # 6. Use ONLY the raw user question for embedding-based retrieval
        # The full prompt (request.query) contains ~500 lines of instructions which
        # produce a poor embedding for similarity search. user_query is the short question.
        search_query = request.user_query.strip() if request.user_query and request.user_query.strip() else request.query
        
        print(f"\n[DEBUG] Search query for retrieval: {search_query[:150]}...")
        print(f"[DEBUG] Document ID filter: {request.document_id}")
        
        retrieved_docs = retriever.invoke(search_query)
        
        print(f"[DEBUG] Retrieved {len(retrieved_docs)} chunks")
        for i, doc in enumerate(retrieved_docs):
            page = doc.metadata.get('page', '?')
            print(f"[DEBUG]   Chunk {i}: page={page}, len={len(doc.page_content)}")
        
        # 6.5 Add explicit fallback if context is empty
        if not retrieved_docs:
            print("[DEBUG] *** No documents retrieved — returning fallback ***")
            return {
                "response": "I couldn't find that information in the uploaded document.",
                "pages": [],
                "pdf_url": None,
                "session_id": request.session_id,
                "document_id": request.document_id
            }

        final_response, pages = setup_and_invoke_chain(retrieved_docs, request.query, request.session_id)
        
        # 7. Construct the public PDF URL from metadata
        import os
        file_path = retrieved_docs[0].metadata.get("file_path", "")
        filename = os.path.basename(file_path)
        pdf_url = f"/api/download/{filename}"

        return {
            "response": final_response,
            "pages": pages,
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
