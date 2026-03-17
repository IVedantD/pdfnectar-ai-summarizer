import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(override=True)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "pdfnectar")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "document_embeddings")
ATLAS_VECTOR_SEARCH_INDEX_NAME = os.getenv("ATLAS_VECTOR_SEARCH_INDEX_NAME", "vector_index")

if not MONGO_URI:
    raise ValueError("MONGO_URI must be set in the environment variables.")

def create_search_index():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Define the vector search index model natively via PyMongo
    # Using the standard Gemini embedding dimensions (768)
    search_index_model = {
        "name": ATLAS_VECTOR_SEARCH_INDEX_NAME,
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "numDimensions": 768,
                    "path": "embedding",
                    "similarity": "cosine"
                }
            ]
        }
    }
    
    try:
        print(f"Creating vector search index '{ATLAS_VECTOR_SEARCH_INDEX_NAME}' natively...")
        collection.create_search_index(model=search_index_model)
        print("Index creation initiated successfully. Check MongoDB Atlas UI for status.")
    except Exception as e:
        print(f"An error occurred (the index may already exist): {e}")

if __name__ == "__main__":
    create_search_index()
