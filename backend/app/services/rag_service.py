import os
from typing import List, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_core.documents import Document
from collections import defaultdict

from ..core.config import MONGO_URI, DB_NAME, GEMINI_MODEL
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
        self.llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.2)
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

    async def query(self, user_query: str, full_query: str, session_id: str, document_id: str) -> dict:
        retriever = self.get_retriever(document_id)
        search_query = user_query.strip() if user_query.strip() else full_query
        
        retrieved_docs = retriever.invoke(search_query)
        
        if not retrieved_docs:
            return {
                "response": "I couldn't find that information in the uploaded document.",
                "pages": [],
                "source": "vector_rag"
            }

        doc_data = self.group_and_format_docs(retrieved_docs)
        
        system_prompt = (
            "You are PDF Nectar, an expert AI assistant tasked with answering questions strictly based on the provided document excerpts. "
            "Follow these rules strictly:\n"
            "1. ONLY use the information provided in the Context below. Do not use outside knowledge or hallucinate information.\n"
            "2. If the answer cannot be found in the Context, politely state: 'I cannot find the answer to this question in the provided document.'\n"
            "3. Do NOT insert any page citations, source references, or page numbers inside your answer text.\n"
            "4. Do NOT write (Source: Page X), [Source: Page X], or any similar inline citation.\n"
            "5. Do NOT add a Sources or References section at the end.\n\n"
            "Context Information:\n{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
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
