# Backend Setup Guide

This guide outlines the steps required to set up the Python backend for the PDFNectar AI Summarizer project, utilizing FastAPI along with MongoDB Vector Search and LangChain as explored in our reference material.

## Prerequisites
- Python 3.9+
- A running MongoDB Atlas cluster with Vector Search capabilities
- Gemini API Key

## 1. Project Initialization
Navigate to the root directory of the project (`d:\pdfnectar-ai-summarizer`) and create a dedicated backend folder:
```bash
mkdir backend
cd backend
```

## 2. Virtual Environment Setup
It is best practice to keep Python dependencies isolated. Create and activate a virtual environment:

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Dependencies
With the virtual environment active, install the necessary libraries for the server, MongoDB interactions, and LangChain:
```bash
pip install fastapi uvicorn langchain-mongodb langchain-google-genai langchain-core langchain python-dotenv pymongo PyMuPDF langchain-community python-multipart
```

You can optionally freeze these into a `requirements.txt`:
```bash
pip freeze > requirements.txt
```

## 4. Environment Variables Configuration
Create a `.env` file inside the `backend/` directory to securely store your credentials:
```env
GEMINI_API_KEY="your_gemini_api_key_here"
MONGO_URI="your_mongodb_connection_string_here"

# Database structure configuration
DB_NAME="pdfnectar"
COLLECTION_NAME="document_embeddings"
ATLAS_VECTOR_SEARCH_INDEX_NAME="vector_index"
```

## 5. Running the Development Server
Once the basic FastAPI template (`main.py`) is implemented in Phase 1, you will be able to start the development server using:
```bash
uvicorn main:app --reload --port 8000
```
This will host your backend locally, typically at `http://127.0.0.1:8000`, making endpoints available to the React frontend.
