import os
from typing import List, Tuple
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_core.documents import Document
from collections import defaultdict

import logging
from ..core.config import (MONGO_URI, DB_NAME, GEMINI_MODEL, OPENROUTER_API_KEY, 
                           OPENROUTER_MODEL, SITE_URL, SITE_NAME, GROQ_API_KEY, GROQ_MODEL)

logger = logging.getLogger(__name__)
from database import get_vector_store

def get_session_history(session_id: str):
    return MongoDBChatMessageHistory(
        MONGO_URI, 
        session_id, 
        database_name=DB_NAME, 
        collection_name="chat_histories"
    )

class RAGService:
    def __init__(self):
        # Use Groq if API key is provided, else fallback to OpenRouter, else Gemini
        if GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY":
            logger.info(f"Initializing RAGService with Groq model: {GROQ_MODEL}")
            self.llm = ChatGroq(
                model=GROQ_MODEL,
                groq_api_key=GROQ_API_KEY,
                temperature=0.1,
            )
        elif OPENROUTER_API_KEY and OPENROUTER_API_KEY != "YOUR_OPENROUTER_API_KEY":
            logger.info(f"Initializing RAGService with OpenRouter model: {OPENROUTER_MODEL}")
            self.llm = ChatOpenAI(
                model=OPENROUTER_MODEL,
                openai_api_key=OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": SITE_URL,
                    "X-Title": SITE_NAME,
                },
                temperature=0.1,
            )
        else:
            logger.info(f"Initializing RAGService with Gemini model: {GEMINI_MODEL}")
            self.llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL, 
                temperature=0.1,
                max_retries=6, 
            )
        self.vectorstore = get_vector_store()

    def get_system_prompt(self):
        """Standard System Prompt for PDF Bot"""
        return (
            "You are PDF Nectar, an intelligent document analysis assistant. "
            "Your goal is to provide **structured, highly detailed, and data-driven answers**. \n\n"
            "STRICT GUIDELINES:\n"
            "1. **Extract Numeric Data**: Always prioritize specific values (emissions, percentages, currency, dates) over generic text.\n"
            "2. **Structured Formatting**: Use Markdown (Level 2/3 headers, bold text, and bullet points) to make information readable.\n"
            "3. **Tone**: Be professional but direct. Use clear icons (e.g., 🌍, 📊, 🧾) for major sections if appropriate.\n"
            "4. **No Hallucinations**: Only use the provided context. If a value is missing, say so.\n"
            "5. **Source Citation**: Mention page numbers if available in brackets (e.g., [Page 12]).\n\n"
            "Context Information:\n{context}"
        )

    def get_retriever(self, document_id: str, k: int = 5):
        return self.vectorstore.as_retriever(
            search_kwargs={
                "k": k,
                "pre_filter": {
                    "document_id": {"$eq": document_id}
                }
            }
        )

    def group_and_format_docs(self, docs: List[Document], max_pages: int = 5) -> dict:
        page_groups = defaultdict(list)
        ordered_pages = []
        
        for d in docs:
            page = d.metadata.get('page', 'Unknown')
            text = d.page_content.strip()
            if page not in page_groups:
                ordered_pages.append(page)
            page_groups[page].append(text)

        top_pages = ordered_pages[:max_pages]
        formatted_chunks = []
        final_pages = set()
        
        for page in top_pages:
            if page != 'Unknown':
                final_pages.add(page)
            combined_text = "\n...\n".join(page_groups[page])
            formatted_chunks.append(f"--- Excerpt from Page {page} ---\n{combined_text}\n")
        
        return {
            "context_str": "\n".join(formatted_chunks),
            "source_pages": sorted(list(final_pages))
        }

    async def query(self, user_query: str, full_query: str, session_id: str, document_id: str) -> dict:
        retriever = self.get_retriever(document_id)
        search_query = user_query.strip() if user_query.strip() else full_query
        
        # Atlas Vector Search is eventually consistent. 
        # If we just uploaded a document, we might need a moment for the index to catch up.
        retrieved_docs = []
        import asyncio
        for attempt in range(5): # Try up to 5 times (20 seconds)
            retrieved_docs = retriever.invoke(search_query)
            if retrieved_docs:
                break
            if attempt < 4:
                logger.info(f"Retrying retrieval for {document_id} (Attempt {attempt+1}/5) - Waiting for Atlas index...")
                await asyncio.sleep(5) # Wait 5 seconds for Atlas to index
        
        if not retrieved_docs:
            return {
                "response": "I couldn't find that information in the uploaded document.",
                "pages": [],
                "source": "vector_rag"
            }

        doc_data = self.group_and_format_docs(retrieved_docs)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ])

        chain = prompt | self.llm | StrOutputParser()
        
        chain_with_history = RunnableWithMessageHistory(
            chain,
            get_session_history,
            input_messages_key="question",
            history_messages_key="history",
        )
        
        response = chain_with_history.invoke(
            {"context": doc_data["context_str"], "question": full_query},
            config={"configurable": {"session_id": session_id}}
        )
        
        return {
            "response": response,
            "pages": doc_data["source_pages"],
            "source": "vector_rag"
        }
