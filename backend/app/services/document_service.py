import os
import logging
import asyncio
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from database import get_vector_store
from app.core.document_manager import DocumentManager

logger = logging.getLogger("pdfnectar.document_service")

class DocumentService:
    @staticmethod
    async def process_and_ingest_pdf(
        file_path: str,
        document_id: str,
        original_filename: str,
    ):
        """Processes a PDF with full lifecycle status tracking and error handling."""
        extra = {"doc_id": document_id}
        try:
            logger.info(f"Starting background processing for {document_id}", extra=extra)
            # 1. Load the PDF
            try:
                logger.info("Loading PDF", extra=extra)
                pdf_parse_timeout_s = float(
                    os.getenv("PDF_PARSE_TIMEOUT_SECONDS", "20")
                )
                max_text_chars = int(
                    os.getenv("MAX_PDF_TEXT_CHARS", "2000000")
                )
                def load_docs():
                    loader = PyMuPDFLoader(file_path)
                    return loader.load()
                documents = await asyncio.wait_for(
                    asyncio.to_thread(load_docs),
                    timeout=pdf_parse_timeout_s,
                )
                if not documents:
                    raise ValueError("Invalid or unreadable PDF")
                
                # Check page limits immediately
                max_pages = int(os.getenv("MAX_PDF_PAGES", "100"))
                doc_pages = len(documents)
                if doc_pages > max_pages:
                    logger.warning(
                        "PDF exceeds page limit: %s > %s",
                        doc_pages,
                        max_pages,
                        extra=extra,
                    )
                    await asyncio.to_thread(
                        DocumentManager.update_status, 
                        document_id, 
                        "failed", 
                        error=f"PDF exceeds maximum limit of {max_pages} pages"
                    )
                    return

                # Cap extracted text to avoid pathological PDFs causing memory/compute blowups
                total_chars = sum(len(d.page_content or "") for d in documents)
                if total_chars > max_text_chars:
                    logger.warning(
                        "PDF text too large: %s > %s",
                        total_chars,
                        max_text_chars,
                        extra=extra,
                    )
                    await asyncio.to_thread(
                        DocumentManager.update_status,
                        document_id,
                        "failed",
                        error="PDF content too large to process safely",
                    )
                    return
                    
            except asyncio.TimeoutError:
                logger.error("PDF parsing timed out", extra=extra, exc_info=True)
                await asyncio.to_thread(
                    DocumentManager.update_status,
                    document_id,
                    "failed",
                    error="PDF parsing timed out",
                )
                return
            except Exception as e:
                logger.error(f"PDF Loading failed: {str(e)}", extra=extra, exc_info=True)
                await asyncio.to_thread(
                    DocumentManager.update_status,
                    document_id,
                    "failed",
                    error="Invalid or unreadable PDF",
                )
                return

            # 2. Split the PDF into chunks
            logger.info("Splitting text", extra=extra)
            def split_docs():
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1500,
                    chunk_overlap=300,
                    separators=["\n\n", "\n", "|", " ", ""],
                    add_start_index=True
                )
                return text_splitter.split_documents(documents)
            chunks = await asyncio.to_thread(split_docs)
            
            # 3. Add rich metadata
            for chunk in chunks:
                page_num = chunk.metadata.get('page', 0)
                display_page = int(page_num) + 1 if isinstance(page_num, int) else page_num
                chunk.metadata.update({
                    'document_id': document_id,
                    'source_file': original_filename,
                    'page': display_page
                })

            # 4. Ingest into Vector Store
            try:
                logger.info("Embedding started", extra=extra)
                vectorstore = get_vector_store()
                await asyncio.to_thread(vectorstore.add_documents, chunks)
            except Exception as e:
                logger.error(f"Embedding failed: {str(e)}", extra=extra, exc_info=True)
                await asyncio.to_thread(DocumentManager.update_status, document_id, "failed", error="Vector indexing failed")
                return

            # 5. Extract numeric data and save metadata
            logger.info("Detecting numeric data", extra=extra)
            sample_chunks = chunks[:5]  # Simple sampling for MVP
            sample_text = "\n\n".join([c.page_content for c in sample_chunks])
            
            from app.services.numeric_detector import has_numeric_data, detect_chart_type
            has_data, _ = await asyncio.to_thread(has_numeric_data, sample_text)
            suggested_type = await asyncio.to_thread(detect_chart_type, sample_text)
            
            def save_meta():
                DocumentManager.save_metadata(document_id, {
                    "original_filename": original_filename,
                    "total_pages": len(documents),
                    "total_chunks": len(chunks),
                    "has_numeric_data": has_data,
                    "suggested_chart_type": suggested_type,
                    "suggested_questions": [] # Placeholder
                })
            await asyncio.to_thread(save_meta)
            
            logger.info(f"Processing completed for {document_id}", extra=extra)

        except Exception as e:
            logger.error(f"Unexpected background error: {str(e)}", extra=extra, exc_info=True)
            await asyncio.to_thread(DocumentManager.update_status, document_id, "failed", error="Internal processing error")
        finally:
            logger.info("Cleanup done", extra=extra)
            # Cleanup local temp file
            if os.path.exists(file_path):
                try: 
                    def remove_file():
                        os.remove(file_path)
                    await asyncio.to_thread(remove_file)
                except Exception as cleanup_err:
                    logger.warning(f"Temp file cleanup failed: {str(cleanup_err)}", extra=extra)
