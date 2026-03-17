import os
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
ATLAS_VECTOR_SEARCH_INDEX_NAME = os.getenv("ATLAS_VECTOR_SEARCH_INDEX_NAME", "vector_index")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not MONGO_URI or not GEMINI_API_KEY:
    raise ValueError("MONGO_URI and GEMINI_API_KEY must be set in the environment variables.")

# 1. Configure MongoDB Connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
MONGODB_COLLECTION = db[COLLECTION_NAME]

# 2. Set up GoogleGenerativeAIEmbeddings
# Updated to gemini-embedding-001 per the v1beta API registry
embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
DIMENSIONS = 3072 # gemini-embedding-001 outputs 3072-dimensional vectors

# 3. Implement MongoDBAtlasVectorSearch initialization
def get_vector_store():
    """Returns the configured MongoDB Atlas Vector Search instance."""
    vectorstore = MongoDBAtlasVectorSearch(
        collection=MONGODB_COLLECTION,
        embedding=embedding_model,
        index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
        text_key="text",
        embedding_key="embedding"
    )
    return vectorstore

def create_search_index():
    """Creates the vector search index on the MongoDB collection."""
    print("Creating vector search index...")
    vectorstore = get_vector_store()
    
    # Required parameters for creating the index
    vectorstore.create_vector_search_index(
        dimensions=DIMENSIONS
    )
    print(f"Index '{ATLAS_VECTOR_SEARCH_INDEX_NAME}' creation initiated. Check MongoDB Atlas UI for status.")

if __name__ == "__main__":
    create_search_index()
