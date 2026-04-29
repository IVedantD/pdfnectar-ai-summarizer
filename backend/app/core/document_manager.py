import logging
from datetime import datetime
from typing import Optional
from database import METADATA_COLLECTION

logger = logging.getLogger("pdfnectar.document_manager")

class DocumentManager:
    """Manages document metadata and status tracking in MongoDB."""
    
    @staticmethod
    def initialize_status(document_id: str, original_filename: str, user_id: str):
        """Creates the initial document record with 'processing' status and owner."""
        now = datetime.utcnow()
        METADATA_COLLECTION.update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "document_id": document_id,
                    "user_id": user_id,
                    "original_filename": original_filename,
                    "status": "processing",
                    "created_at": now,
                    "updated_at": now
                }
            },
            upsert=True
        )
        logger.info(f"Initialized status for {document_id}", extra={"doc_id": document_id, "user_id": user_id})

    @staticmethod
    def update_status(document_id: str, status: str, error: Optional[str] = None):
        """Atomically updates the document processing status."""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        if error:
            update_data["error"] = error
            
        METADATA_COLLECTION.update_one(
            {"document_id": document_id},
            {"$set": update_data}
        )
        logger.info(f"Updated status for {document_id} to {status}", extra={"doc_id": document_id})

    @staticmethod
    def save_metadata(document_id: str, metadata: dict):
        """Saves full document metadata and marks as completed."""
        metadata["status"] = "completed"
        metadata["updated_at"] = datetime.utcnow()
        
        METADATA_COLLECTION.update_one(
            {"document_id": document_id},
            {"$set": metadata}
        )
        logger.info(f"Saved final metadata for {document_id}", extra={"doc_id": document_id})

    @staticmethod
    def get_metadata(document_id: str) -> Optional[dict]:
        """Retrieves document metadata (internal use)."""
        return METADATA_COLLECTION.find_one({"document_id": document_id}, {"_id": 0})

    @staticmethod
    def get_metadata_for_user(document_id: str, user_id: str) -> Optional[dict]:
        """Retrieves document metadata only if it belongs to the specified user."""
        return METADATA_COLLECTION.find_one(
            {"document_id": document_id, "user_id": user_id}, 
            {"_id": 0}
        )

    @staticmethod
    def get_page_count(document_id: str) -> int:
        metadata = DocumentManager.get_metadata(document_id)
        if metadata:
            return metadata.get("total_pages", 0)
        return 0
