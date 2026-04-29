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
from app.core.prompts import build_prompt
from app.core.document_manager import DocumentManager

logger = logging.getLogger(__name__)

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
            # Use ChatOpenAI for OpenRouter
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

    async def query(self, user_query: str, session_id: str, document_id: str, mode: str = "chat", **kwargs) -> dict:
        is_summary = mode == "summary"
        extra = {"doc_id": document_id, "mode": mode}
        
        # 1. Fetch document metadata for reasoning calibration
        metadata = await asyncio.to_thread(DocumentManager.get_metadata, document_id)
        has_data = metadata.get("has_numeric_data", False)
        chart_type = metadata.get("suggested_chart_type", "bar")
        language = kwargs.get("language", "English")
        length = kwargs.get("length", "medium")

        # 2. Retrieval with eventual consistency protection
        primary_k = 10 if is_summary else 5
        retriever = self.get_retriever(document_id, k=primary_k)
        
        # Detect if user is specifically asking for a chart
        is_chart_requested = any(keyword in user_query.lower() for keyword in ["chart", "graph", "plot", "visualize", "data"])
        
        # Use summary-specific search if needed
        search_query = "overall summary document overview key main points" if is_summary else user_query
        
        retrieved_docs = []
        for attempt in range(5): 
            retrieved_docs = await asyncio.to_thread(retriever.invoke, search_query)
            if retrieved_docs:
                break
            if attempt < 4:
                logger.info(f"Atlas Search retry {attempt+1}/5 for {document_id}", extra=extra)
                await asyncio.sleep(4) 
        
        if not retrieved_docs:
            return {
                "response": "Processing complete, but document content isn't indexed yet. Please wait a moment and try again.",
                "pages": [],
                "source": "vector_rag"
            }

        # 3. Secondary retrieval for numeric context if data exists or chart requested
        if has_data or is_chart_requested:
            numeric_query = "numeric data tables figures statistics values financial metrics"
            numeric_retriever = self.get_retriever(document_id, k=8)
            try:
                numeric_docs = await asyncio.to_thread(numeric_retriever.invoke, numeric_query)
                existing_contents = set(d.page_content.strip() for d in retrieved_docs)
                for doc in numeric_docs:
                    if doc.page_content.strip() not in existing_contents:
                        retrieved_docs.append(doc)
            except Exception as e:
                logger.warning(f"Numeric retrieval failed: {e}", extra=extra)

        doc_data = self.group_and_format_docs(retrieved_docs)
        
        # 4. Prompt Engineering via core templates
        system_prompt = build_prompt(
            user_query=user_query,
            mode_str=mode,
            language=language,
            length=length,
            has_data=has_data,
            suggested_chart_type=chart_type,
            is_chart_requested=is_chart_requested
        )
        
        # Wrap context into system prompt
        full_system_prompt = f"{system_prompt}\n\nDOCUMENT CONTEXT:\n{doc_data['context_str']}"

        prompt_tmpl = ChatPromptTemplate.from_messages([
            ("system", full_system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ])

        chain = prompt_tmpl | self.llm | StrOutputParser()
        chain_with_history = RunnableWithMessageHistory(
            chain,
            get_session_history,
            input_messages_key="question",
            history_messages_key="history",
        )
        
        # 5. LLM Call with history
        response = await asyncio.to_thread(
            chain_with_history.invoke,
            {"question": user_query},
            config={"configurable": {"session_id": session_id}}
        )
        
        return {
            "response": response,
            "pages": doc_data["source_pages"],
            "source": "vector_rag",
            "context_str": doc_data["context_str"]
        }

