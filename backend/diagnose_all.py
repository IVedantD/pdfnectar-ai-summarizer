import os
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

def diagnose():
    load_dotenv(override=True)
    
    # 1. Check MongoDB
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "pdfnectar")
    coll_name = os.getenv("COLLECTION_NAME", "document_embeddings")
    
    print(f"--- MongoDB Diagnosis ---")
    try:
        client = MongoClient(uri)
        db = client[db_name]
        coll = db[coll_name]
        
        doc = coll.find_one()
        if doc:
            print(f"Sample document found!")
            print(f"Fields: {list(doc.keys())}")
            print(f"document_id: '{doc.get('document_id')}' (Type: {type(doc.get('document_id'))})")
            print(f"metadata: {doc.get('metadata')}")
        else:
            print("❌ No documents found in collection.")
            
        # Check index
        indexes = list(coll.list_search_indexes())
        print(f"Search Indexes: {[idx['name'] for idx in indexes]}")
        
    except Exception as e:
        print(f"❌ MongoDB Error: {e}")

    # 2. Check OpenRouter Models
    print(f"\n--- OpenRouter Model Diagnosis ---")
    api_key = os.getenv("OPENROUTER_API_KEY")
    try:
        response = requests.get("https://openrouter.ai/api/v1/models")
        if response.status_code == 200:
            models = response.json().get("data", [])
            free_models = [m["id"] for m in models if m.get("pricing", {}).get("prompt") == "0"]
            print(f"Found {len(free_models)} free models.")
            print(f"Top 10 free models: {free_models[:10]}")
            
            target = "google/gemini-2.0-flash-lite-preview-02-05:free"
            if target in free_models:
                print(f"✅ {target} is VALID.")
            else:
                print(f"❌ {target} is NOT in the free models list.")
                # Look for similar
                similar = [m for m in free_models if "gemini" in m.lower()]
                print(f"Similar Gemini models found: {similar}")
        else:
            print(f"❌ Failed to fetch models: {response.status_code}")
    except Exception as e:
        print(f"❌ OpenRouter Error: {e}")

if __name__ == "__main__":
    diagnose()
