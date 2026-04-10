import logging
from typing import Tuple
from .rag_service import RAGService
from ..core.config import PAGEINDEX_THRESHOLD, COMPLEX_KEYWORDS
from ..core.document_manager import DocumentManager

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RouterService:
    def __init__(self):
        self.rag_service = RAGService()
        from .pageindex_service import PageIndexService
        self.pageindex_service = PageIndexService()

    def should_use_pageindex(self, query: str, document_id: str) -> bool:
        """
        Decision logic:
        1. Check if document exists and has page count > threshold.
        2. Check if query contains complex keywords.
        """
        page_count = DocumentManager.get_page_count(document_id)
        
        # Rule 1: Document size check
        if page_count < PAGEINDEX_THRESHOLD:
            logger.info(f"Routing to Vector RAG: Page count {page_count} < {PAGEINDEX_THRESHOLD}")
            return False
            
        # Rule 2: Keyword detection
        query_lower = query.lower()
        has_complex_keyword = any(keyword in query_lower for keyword in COMPLEX_KEYWORDS)
        
        if has_complex_keyword:
            logger.info(f"Routing to PageIndex: Complex keywords detected in large document ({page_count} pages)")
            return True
        
        logger.info(f"Routing to Vector RAG: No complex keywords found in {page_count}-page document")
        return False

    async def route_query(self, user_query: str, full_query: str, session_id: str, document_id: str, mode: str = "chat") -> dict:
        use_pageindex = self.should_use_pageindex(full_query, document_id)
        
        if use_pageindex:
            try:
                logger.info("PageIndex triggered")
                result = await self.pageindex_service.query(user_query, full_query, session_id, document_id)
                return result
            except Exception as e:
                logger.error(f"PageIndex failed: {str(e)}")
                logger.info("Fallback to RAG triggered")
                # Fallback continues to the RAG call below

        # Default fallback to Vector RAG
        try:
            logger.info("Standard Vector RAG triggered")
            return await self.rag_service.query(user_query, full_query, session_id, document_id, mode=mode)
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise e
