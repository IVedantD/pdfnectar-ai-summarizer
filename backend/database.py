import os
import logging
from pymongo import MongoClient
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import load_dotenv

load_dotenv(override=True)

# Map the .env GEMINI_API_KEY to the GOOGLE_API_KEY expected automatically by LangChain
if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

# Environment variables
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "pdfnectar")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "document_embeddings")
ATLAS_VECTOR_SEARCH_INDEX_NAME = os.getenv(
    "ATLAS_VECTOR_SEARCH_INDEX_NAME", "vector_index"
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not MONGO_URI or not GEMINI_API_KEY:
    raise ValueError(
        "MONGO_URI and GEMINI_API_KEY must be set in the environment variables."
    )

# 1. Configure MongoDB Connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
MONGODB_COLLECTION = db[COLLECTION_NAME]
METADATA_COLLECTION = db["document_metadata"]
SESSIONS_COLLECTION = db["chat_sessions"]

logger = logging.getLogger("pdfnectar.database")

# Chat session TTL (seconds). Default 24h.
CHAT_SESSION_TTL_SECONDS = int(os.getenv("CHAT_SESSION_TTL_SECONDS", "86400"))

# 2. Set up HuggingFace Local Embeddings
DIMENSIONS = 384
_embedding_model = None

def get_embedding_model():
    """Returns the HuggingFace Inference API embedding model, loading it on first call."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing HuggingFace Inference API embeddings (sentence-transformers/all-MiniLM-L6-v2)...")
        # Ensure token is set (LangChain will look for HUGGINGFACEHUB_API_TOKEN automatically)
        hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not hf_token:
            logger.warning("HUGGINGFACEHUB_API_TOKEN not found in environment variables.")
        
        _embedding_model = HuggingFaceEndpointEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2",
            huggingfacehub_api_token=hf_token,
        )
        logger.info("Inference API Embedding model initialized.")
    return _embedding_model

# 3. Implement MongoDBAtlasVectorSearch initialization
def get_vector_store():
    """Returns the configured MongoDB Atlas Vector Search instance."""
    return MongoDBAtlasVectorSearch(
        collection=MONGODB_COLLECTION,
        embedding=get_embedding_model(),
        index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
        text_key="text",
        embedding_key="embedding"
    )

def create_search_index():
    """Creates the vector search index on the MongoDB collection."""
    logger.info("Verifying/Creating Atlas Vector Search index...")
    
    try:
        MONGODB_COLLECTION.create_search_index(
            {
                "name": ATLAS_VECTOR_SEARCH_INDEX_NAME,
                "type": "vectorSearch",
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": DIMENSIONS,
                            "similarity": "cosine"
                        },
                        {
                            "type": "filter",
                            "path": "document_id"
                        },
                        {
                            "type": "filter",
                            "path": "page"
                        }
                    ]
                }
            }
        )
        logger.info(f"Index '{ATLAS_VECTOR_SEARCH_INDEX_NAME}' creation task initiated.")
        
        # Add unique index for metadata status tracking
        METADATA_COLLECTION.create_index("document_id", unique=True)
        logger.info("Unique index on 'document_id' confirmed.")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("Search index already exists.")
        else:
            logger.error(f"Error during index verification: {e}")

# Pre-load model at module import level for production readiness
get_embedding_model()

# Ensure basic indexes exist
try:
    METADATA_COLLECTION.create_index("document_id", unique=True)
    SESSIONS_COLLECTION.create_index("session_id", unique=True)
    SESSIONS_COLLECTION.create_index(
        [("user_id", 1), ("document_id", 1), ("created_at", -1)]
    )
    # TTL index: MongoDB will auto-delete sessions after TTL. Cleanup is approximate.
    # We still enforce expiration in API handlers.
    SESSIONS_COLLECTION.create_index(
        "created_at", expireAfterSeconds=CHAT_SESSION_TTL_SECONDS
    )
except Exception as _idx_err:
    logger.warning("Index creation skipped: %s", _idx_err)

if __name__ == "__main__":
    create_search_index()
