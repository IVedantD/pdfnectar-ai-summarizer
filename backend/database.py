import os
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

# 2. Set up HuggingFace Local Embeddings
# all-MiniLM-L6-v2 is fast, lightweight (80MB), and completely free to run locally!
# Lazy-loaded singleton — avoids blocking server startup for 10+ seconds
DIMENSIONS = 384 # all-MiniLM-L6-v2 outputs 384-dimensional vectors
_embedding_model = None

def get_embedding_model():
    """Returns the HuggingFace embedding model, loading it on first call."""
    global _embedding_model
    if _embedding_model is None:
        print("Loading HuggingFace embedding model (first request)...")
        _embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        print("Embedding model ready.")
    return _embedding_model

# 3. Implement MongoDBAtlasVectorSearch initialization
def get_vector_store():
    """Returns the configured MongoDB Atlas Vector Search instance."""
    vectorstore = MongoDBAtlasVectorSearch(
        collection=MONGODB_COLLECTION,
        embedding=get_embedding_model(),
        index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
        text_key="text",
        embedding_key="embedding"
    )
    return vectorstore

def create_search_index():
    """Creates the vector search index on the MongoDB collection."""
    print("Creating vector search index...")
    
    # We use the raw pymongo client to ensure the most robust index definition
    # for Atlas Vector Search with filtering support.
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
        print(f"Index '{ATLAS_VECTOR_SEARCH_INDEX_NAME}' creation initiated. Check MongoDB Atlas UI for status.")
    except Exception as e:
        print(f"Error initiating index creation: {e}")
        print("If the index already exists, this is normal. Status can be 'FAILED', 'PENDING', or 'READY'.")

if __name__ == "__main__":
    create_search_index()
