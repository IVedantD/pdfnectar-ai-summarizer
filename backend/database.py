import os
import logging
import time
from pymongo import MongoClient
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings
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

# 2. Set up Embeddings
DIMENSIONS = 768
_embedding_model = None

def get_embedding_model():
    """Returns the Gemini embedding model, loading it on first call.

    text-embedding-004 was shut down on 2026-01-14. gemini-embedding-001 is the
    supported text model. Leave task_type unset so documents use
    RETRIEVAL_DOCUMENT and queries use RETRIEVAL_QUERY.
    Output is fixed at DIMENSIONS; the model default is 3072 and would not
    match the Atlas index.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing Gemini embeddings (gemini-embedding-001, %s-d)...", DIMENSIONS)
        _embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            output_dimensionality=DIMENSIONS,
        )
        logger.info("Embedding model initialized.")
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

def _index_dimensions(index_doc: dict):
    """Return numDimensions for the embedding field, if the index defines one."""
    definition = index_doc.get("latestDefinition") or index_doc.get("definition") or {}
    for field in definition.get("fields", []):
        if field.get("type") == "vector" and field.get("path") == "embedding":
            return field.get("numDimensions")
    return None


def _search_index_definition():
    return {
        "name": ATLAS_VECTOR_SEARCH_INDEX_NAME,
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": DIMENSIONS,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "document_id"},
                {"type": "filter", "path": "page"},
            ]
        },
    }


def ensure_search_index():
    """Create the Atlas vector index, or replace it when its size does not match.

    Atlas cannot change numDimensions on an existing index. The previous
    MiniLM index is 384-d. Leaving it in place stores Gemini vectors that
    search cannot use.
    """
    logger.info("Verifying Atlas Vector Search index (%s dimensions)...", DIMENSIONS)
    try:
        indexes = list(MONGODB_COLLECTION.list_search_indexes())
    except Exception as e:
        logger.warning("Could not list Atlas search indexes: %s", e)
        return

    existing = next(
        (idx for idx in indexes if idx.get("name") == ATLAS_VECTOR_SEARCH_INDEX_NAME),
        None,
    )
    current_dims = _index_dimensions(existing) if existing else None
    if existing is not None and current_dims == DIMENSIONS:
        logger.info(
            "Atlas vector index '%s' already matches %s dimensions.",
            ATLAS_VECTOR_SEARCH_INDEX_NAME,
            DIMENSIONS,
        )
        return

    if existing is not None and current_dims is None:
        logger.warning(
            "Atlas vector index '%s' exists, but its dimensions could not be read. Leaving it in place.",
            ATLAS_VECTOR_SEARCH_INDEX_NAME,
        )
        return

    if existing is not None:
        logger.warning(
            "Recreating Atlas vector index '%s' (%s -> %s dimensions). Previously uploaded documents must be uploaded again.",
            ATLAS_VECTOR_SEARCH_INDEX_NAME,
            current_dims,
            DIMENSIONS,
        )
        try:
            MONGODB_COLLECTION.drop_search_index(ATLAS_VECTOR_SEARCH_INDEX_NAME)
        except Exception as e:
            logger.error("Failed to drop vector index: %s", e)
            return

        dropped = False
        for _ in range(15):
            time.sleep(1)
            try:
                names = [idx.get("name") for idx in MONGODB_COLLECTION.list_search_indexes()]
            except Exception as e:
                logger.warning("Waiting for vector index drop: %s", e)
                continue
            if ATLAS_VECTOR_SEARCH_INDEX_NAME not in names:
                dropped = True
                break
        if not dropped:
            logger.error("Timed out waiting for the old vector index to drop.")
            return

    try:
        MONGODB_COLLECTION.create_search_index(_search_index_definition())
        logger.info("Index '%s' creation task initiated.", ATLAS_VECTOR_SEARCH_INDEX_NAME)
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("Search index already exists.")
        else:
            logger.error("Error during index verification: %s", e)

# Pre-load model at module import level for production readiness
get_embedding_model()
ensure_search_index()

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
    ensure_search_index()
