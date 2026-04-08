import os
from database import get_vector_store
from dotenv import load_dotenv

def test_search():
    load_dotenv(override=True)
    vectorstore = get_vector_store()
    
    # Let's get a document ID from the database first
    from pymongo import MongoClient
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "pdfnectar")
    coll_name = os.getenv("COLLECTION_NAME", "document_embeddings")
    
    client = MongoClient(uri)
    coll = client[db_name][coll_name]
    doc = coll.find_one()
    
    if not doc:
        print("No documents found in MongoDB.")
        return
        
    doc_id = doc.get('document_id')
    print(f"Testing search for document_id: {doc_id}")
    
    # Test 1: pre_filter dictionary
    try:
        print("\nTest 1: pre_filter")
        results = vectorstore.similarity_search(
            "test query",
            k=2,
            pre_filter={"document_id": {"$eq": doc_id}}
        )
        print(f"Results: {len(results)}")
    except Exception as e:
        print(f"Error 1: {e}")

    # Test 2: raw MongoDB aggregation
    print("\nTest 2: Raw search")
    try:
        results = vectorstore._similarity_search_with_score(
            "test query",
            k=2,
            pre_filter={"document_id": {"$eq": doc_id}}
        )
        print(f"Results: {len(results)}")
    except Exception as e:
        print(f"Error 2: {e}")

if __name__ == "__main__":
    test_search()
