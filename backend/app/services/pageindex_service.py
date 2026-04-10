import logging
import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from ..core.config import (GEMINI_MODEL, OPENROUTER_API_KEY, OPENROUTER_MODEL, 
                           SITE_URL, SITE_NAME, GROQ_API_KEY, GROQ_MODEL)
from ..core.document_manager import DocumentManager
from database import get_vector_store

logger = logging.getLogger(__name__)

class SearchPlan(BaseModel):
    reasoning: str = Field(description="Explanation of why these sections were chosen")
    selected_pages: List[int] = Field(description="List of page numbers to retrieve for deep analysis")

class PageIndexService:
    def __init__(self):
        # Use Groq if available, else OpenRouter, else Gemini for PageIndex
        if GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY":
            logger.info(f"Initializing PageIndexService with Groq: {GROQ_MODEL}")
            self.llm = ChatGroq(
                model=GROQ_MODEL,
                groq_api_key=GROQ_API_KEY,
                temperature=0.1,
            )
        elif OPENROUTER_API_KEY and OPENROUTER_API_KEY != "YOUR_OPENROUTER_API_KEY":
            logger.info(f"Initializing PageIndexService with OpenRouter: {OPENROUTER_MODEL}")
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
            logger.info(f"Initializing PageIndexService with Gemini: {GEMINI_MODEL}")
            self.llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL, 
                temperature=0.1,
                max_retries=6, 
            )
        self.vectorstore = get_vector_store()

    async def get_document_structure(self, document_id: str) -> str:
        """
        Retrieves structural metadata or a summary of TOC.
        """
        retriever = self.vectorstore.as_retriever(
            search_kwargs={
                "k": 50,
                "pre_filter": {"document_id": {"$eq": document_id}}
            }
        )
        
        docs = []
        import asyncio
        for attempt in range(3):
            docs = retriever.invoke("summarize the table of contents")
            if docs:
                break
            if attempt < 2:
                logger.info(f"Retrying structure retrieval for {document_id} (Attempt {attempt+1}/3)...")
                await asyncio.sleep(2)
        
        structural_map = {}
        for d in docs:
            page = d.metadata.get("page", 1)
            if page not in structural_map:
                structural_map[page] = d.page_content[:200]
        
        summary = "\n".join([f"Page {p}: {text}..." for p, text in sorted(structural_map.items())])
        return summary

    async def query(self, user_query: str, full_query: str, session_id: str, document_id: str) -> Dict[str, Any]:
        """
        Reasoning-based retrieval:
        1. Understand document structure.
        2. Plan which pages to read.
        3. Retrieve and synthesize.
        """
        logger.info(f"Starting PageIndex reasoning for query: {user_query}")
        
        # 1. Get Document Map
        doc_structure = await self.get_document_structure(document_id)
        
        # 2. Reasoning Step: Plan which pages to fetch
        parser = JsonOutputParser(pydantic_object=SearchPlan)
        planner_prompt = (
            "You are a Document Navigation Expert. You have a query and a map of a large document.\n"
            "Your task is to identify which EXACT pages are most likely to contain the information needed "
            "to answer the question thoroughly.\n\n"
            "CRITICAL: Always include pages that look like they contain: Quantitative Data, Tables, "
            "Financial Metrics, Emissions Data, or Executive Summaries if the query asks for overall facts.\n\n"
            f"Query: {full_query}\n\n"
            f"Document Map (Summaries):\n{doc_structure}\n\n"
            "{format_instructions}\n"
            "Return ONLY the JSON object."
        )
        
        plan = self.llm.invoke([
            HumanMessage(content=planner_prompt.format(format_instructions=parser.get_format_instructions()))
        ])
        
        # Validate plan
        try:
            search_plan = parser.parse(plan.content)
            pages_to_fetch = search_plan.get("selected_pages", [])
            logger.info(f"PageIndex Reasoning: {search_plan['reasoning']}")
        except Exception as e:
            logger.warning(f"Failed to parse PageIndex plan: {e}. Falling back to top pages.")
            pages_to_fetch = [1, 2, 3]

        if not pages_to_fetch:
            pages_to_fetch = [1]

        # 3. Targeted Retrieval
        retrieved_docs = []
        for page in pages_to_fetch[:5]: # Max 5 pages
            page_docs = self.vectorstore.as_retriever(
                search_kwargs={
                    "k": 5,
                    "pre_filter": {
                        "$and": [
                            {"document_id": {"$eq": document_id}},
                            {"page": {"$eq": page}}
                        ]
                    }
                }
            ).invoke(user_query)
            retrieved_docs.extend(page_docs)

        # 4. Final Synthesis
        from .rag_service import RAGService
        rag_service = RAGService()
        doc_data = rag_service.group_and_format_docs(retrieved_docs)
        
        final_answer = self.llm.invoke([
            SystemMessage(content=rag_service.get_system_prompt().format(context=doc_data["context_str"])),
            HumanMessage(content=full_query)
        ]).content

        return {
            "response": final_answer,
            "pages": doc_data["source_pages"],
            "source": "pageindex_reasoning",
            "context_str": doc_data["context_str"]
        }
