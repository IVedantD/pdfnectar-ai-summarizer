import logging
import os
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from ..core.config import GEMINI_MODEL
from ..core.document_manager import DocumentManager
from database import get_vector_store

logger = logging.getLogger(__name__)

class SearchPlan(BaseModel):
    reasoning: str = Field(description="Explanation of why these sections were chosen")
    selected_pages: List[int] = Field(description="List of page numbers to retrieve for deep analysis")

class PageIndexService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.1)
        self.vectorstore = get_vector_store()

    async def get_document_structure(self, document_id: str) -> str:
        """
        Retrieves structural metadata or a summary of TOC.
        In a real PageIndex system, this would be a pre-built hierarchical tree.
        Here we use a simplified version: fetching the first chunk of each page.
        """
        # Fetching top chunks with distinct page numbers to build a 'map'
        # In a production system, this mapping would be stored in the database.
        retriever = self.vectorstore.as_retriever(
            search_kwargs={
                "k": 50,
                "pre_filter": {"document_id": {"$eq": document_id}}
            }
        )
        docs = retriever.invoke("summarize the table of contents")
        
        # Simple structural map: Page X -> First 100 chars
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
        planner_prompt = (
            "You are a Document Navigation Expert. You have a query and a map of a large document. "
            "Your task is to identify which EXACT pages are most likely to contain the information needed "
            "to answer the question thoroughly, especially focusing on complex relationships or comparisons.\n\n"
            f"Query: {full_query}\n\n"
            f"Document Map (Summaries):\n{doc_structure}\n\n"
            "Return a JSON object with 'reasoning' and 'selected_pages' (List of Integers)."
        )
        
        parser = JsonOutputParser(pydantic_object=SearchPlan)
        plan = self.llm.invoke([HumanMessage(content=planner_prompt)])
        
        # Validate plan (simplified)
        try:
            search_plan = parser.parse(plan.content)
            pages_to_fetch = search_plan.get("selected_pages", [])
            logger.info(f"PageIndex Plan: {search_plan['reasoning']}")
        except:
            logger.warning("Failed to parse PageIndex plan, falling back to top pages")
            pages_to_fetch = [1, 2, 3] # Fallback

        if not pages_to_fetch:
            pages_to_fetch = [1]

        # 3. Targeted Retrieval
        # We query the vector store specifically for these pages
        retrieved_docs = []
        for page in pages_to_fetch[:5]: # Max 5 pages for cost/latency
            page_docs = self.vectorstore.as_retriever(
                search_kwargs={
                    "k": 3,
                    "pre_filter": {
                        "$and": [
                            {"document_id": {"$eq": document_id}},
                            {"page": {"$eq": page}}
                        ]
                    }
                }
            ).invoke(user_query)
            retrieved_docs.extend(page_docs)

        # 4. Final Synthesis (Reuse RAG logic or custom)
        from .rag_service import RAGService
        rag_service = RAGService()
        doc_data = rag_service.group_and_format_docs(retrieved_docs)
        
        system_prompt = (
            "You are PDF Nectar (Deep Analysis Mode). You have performed a hierarchical search "
            "across a large document. Answer the user's question with high detail and reasoning.\n"
            "Context Information:\n{context}"
        )
        
        # Synthesis call (Simplified from RAGService for brevity here)
        final_answer = self.llm.invoke([
            SystemMessage(content=system_prompt.format(context=doc_data["context_str"])),
            HumanMessage(content=full_query)
        ]).content

        return {
            "response": final_answer,
            "pages": doc_data["source_pages"],
            "source": "pageindex_reasoning"
        }
