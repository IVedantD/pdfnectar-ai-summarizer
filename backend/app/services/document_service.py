import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from database import get_vector_store
from app.core.document_manager import DocumentManager
import logging
from app.core.config import (OPENROUTER_API_KEY, OPENROUTER_MODEL, SITE_URL, 
                             SITE_NAME, GROQ_API_KEY, GROQ_MODEL)

logger = logging.getLogger(__name__)

class DocumentService:
    @staticmethod
    def process_and_ingest_pdf(file_path: str, document_id: str, original_filename: str) -> dict:
        """Processes a PDF, chunks it, generates embeddings, saves metadata, and generates sample questions."""
        vectorstore = get_vector_store()
        
        # 1. Load the PDF
        try:
            logger.info("Loading PDF")
            loader = PyMuPDFLoader(file_path)
            documents = loader.load()
            if not documents:
                raise ValueError("Invalid or unreadable PDF")
        except Exception as e:
            logger.error(f"PDF Loading failed: {str(e)}")
            if isinstance(e, ValueError): raise
            raise ValueError("Invalid or unreadable PDF")

        # 2. Split the PDF into chunks
        logger.info("Splitting text")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=300,
            separators=["\n\n", "\n", "|", " ", ""],
            add_start_index=True
        )
        chunks = text_splitter.split_documents(documents)
        
        # 3. Add rich metadata: document_id, source_file, and page
        for chunk in chunks:
            page_num = chunk.metadata.get('page', 0)
            display_page = int(page_num) + 1 if isinstance(page_num, int) else page_num
            
            chunk.metadata.update({
                'document_id': document_id,
                'source_file': original_filename,
                'page': display_page
            })

        # 4. Ingest into MongoDB Vector Store using Gemini Embeddings
        try:
            logger.info("Embedding started")
            vectorstore.add_documents(chunks)
        except Exception as e:
            logger.error(f"MongoDB/Embedding failed: {str(e)}")
            if "pymongo" in str(type(e)).lower() or "timeout" in str(e).lower():
                raise ValueError("Database connection failed")
            raise ValueError("Embedding failed")

        # 5. Save metadata using DocumentManager
        logger.info("Saving document metadata")
        DocumentManager.save_metadata(document_id, {
            "original_filename": original_filename,
            "total_pages": len(documents),
            "total_chunks": len(chunks)
        })

        # 6. Generate Suggested Questions based on the initial chunks
        suggested_questions = []
        try:
            # We take the first 3 chunks (or fewer if the document is very small) as sample context
            sample_text = "\n\n".join([chunk.page_content for chunk in chunks[:3]])
            
            # Use Groq if available, then OpenRouter, then Gemini for questions
            if GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY":
                question_llm = ChatGroq(
                    model=GROQ_MODEL,
                    groq_api_key=GROQ_API_KEY,
                    temperature=0.2,
                )
            elif OPENROUTER_API_KEY and OPENROUTER_API_KEY != "YOUR_OPENROUTER_API_KEY":
                question_llm = ChatOpenAI(
                    model=OPENROUTER_MODEL,
                    openai_api_key=OPENROUTER_API_KEY,
                    openai_api_base="https://openrouter.ai/api/v1",
                    default_headers={
                        "HTTP-Referer": SITE_URL,
                        "X-Title": SITE_NAME,
                    },
                    temperature=0.2,
                )
            else:
                # Use a specific known model version if falling back
                question_llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
            
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
                    question = line[1:].strip()
                    if question:
                        suggested_questions.append(question)
                elif line:
                     suggested_questions.append(line)
                     
            if not suggested_questions:
                suggested_questions = [
                    "What is the main purpose of this document?",
                    "What are the key findings presented?",
                    "Could you summarize the main points?"
                ]
                
        except Exception as e:
            print(f"Warning: Failed to generate suggested questions: {e}")
            suggested_questions = [
                "What is the main topic of this document?",
                "Can you provide a brief summary?",
                "What are the most important takeaways?"
            ]

        return {
            "total_chunks": len(chunks),
            "total_pages": len(documents),
            "suggested_questions": suggested_questions[:5] # Enforce max 5
        }
