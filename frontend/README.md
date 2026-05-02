# PDF Nectar AI Summarizer

A full-stack application built to allow users to upload PDF documents, summarize them, and chat with them using Large Language Models and Retrieval Augmented Generation (RAG).

## Architecture
- **Frontend**: Vite, React (TypeScript), Tailwind CSS, Shadcn UI
- **Backend**: FastAPI (Python), MongoDB Atlas Vector Search, LangChain, Google Gemini API

## Prerequisites
- Node.js (v18+) and npm/bun
- Python 3.9+
- MongoDB Atlas cluster with Vector Search configured
- Google Gemini API Key

---

## 🚀 How to Run the Project Locally

To run the full stack, you will need two separate terminal windows: one for the frontend and one for the backend.

### 1. Running the Backend

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   - **Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **macOS/Linux:**
     ```bash
     python3 -m venv venv
     source 
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Ensure you have a `.env` file in the `backend/` directory with the following variables:
   ```env
   GEMINI_API_KEY="your_gemini_api_key"
   MONGO_URI="your_mongodb_cluster_uri"
   DB_NAME="pdfnectar"
   COLLECTION_NAME="document_embeddings"
   ATLAS_VECTOR_SEARCH_INDEX_NAME="vector_index"
   ```

5. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   The backend API will run at `http://localhost:8000`. You can access the automatic documentation at `http://localhost:8000/docs`.

---

### 2. Running the Frontend

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Copy environment variables** (from `frontend/.env.example` to `frontend/.env`) and fill in your Supabase values.

3. **Install dependencies:**
   ```bash
   npm install
   ```

4. **Start the Vite development server:**
   ```bash
   npm run dev
   ```
   The frontend will run at `http://localhost:8080` (or another port provided by Vite in your terminal).

---

## Features
- **PDF Upload**: Ingest and process large PDF documents securely.
- **RAG Architecture**: Automatically chunks and embeds document text into a vector database for rapid semantic retrieval.
- **Contextual Chat**: Ask detailed questions about your uploaded documents, powered by gemini-1.5-flash.
