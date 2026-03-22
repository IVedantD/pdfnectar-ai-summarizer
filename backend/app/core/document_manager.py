import os
import json
from typing import Optional
from .config import UPLOAD_DIR

class DocumentManager:
    """Manages document metadata and storage paths."""
    
    @staticmethod
    def get_document_path(document_id: str, filename: str) -> str:
        return os.path.join(UPLOAD_DIR, f"{document_id}_{filename}")

    @staticmethod
    def save_metadata(document_id: str, metadata: dict):
        metadata_path = os.path.join(UPLOAD_DIR, f"{document_id}_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

    @staticmethod
    def get_metadata(document_id: str) -> Optional[dict]:
        metadata_path = os.path.join(UPLOAD_DIR, f"{document_id}_metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                return json.load(f)
        return None

    @staticmethod
    def get_page_count(document_id: str) -> int:
        metadata = DocumentManager.get_metadata(document_id)
        if metadata:
            return metadata.get("total_pages", 0)
        return 0
