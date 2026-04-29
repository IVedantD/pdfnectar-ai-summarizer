import os
import logging
from pymongo import MongoClient
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv

load_dotenv(override=True)

# Map the .env GEMINI_API_KEY to the GOOGLE_API_KEY expected automatically by LangChain
if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

# Environment variables
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "pdfnectar")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "document_embeddings")
ATLAS_VECTOR_SEARCH_INDEX_NAME = os.getenv("ATLAS_VECTOR_SEARCH_INDEX_NAME", "vector_index")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not MONGO_URI or not GEMINI_API_KEY:
    raise ValueError("MONGO_URI and GEMINI_API_KEY must be set in the environment variables.")

# 1. Configure MongoDB Connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
MONGODB_COLLECTION = db[COLLECTION_NAME]
METADATA_COLLECTION = db["document_metadata"]

logger = logging.getLogger("pdfnectar.database")

# 2. Set up HuggingFace Local Embeddings
DIMENSIONS = 384 
_embedding_model = None

def get_embedding_model():
    """Returns the HuggingFace embedding model, loading it on first call."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing HuggingFace embedding model (all-MiniLM-L6-v2)...")
        _embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        logger.info("Embedding model loaded and ready.")
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

if __name__ == "__main__":
    create_search_index()
