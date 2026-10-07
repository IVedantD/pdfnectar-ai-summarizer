# PDFNectar AI Summarizer 🍯

**PDFNectar** is an enterprise-grade AI document intelligence platform. It ingests complex, multi-page PDF documents, extracts text and semantic meaning, and enables real-time Retrieval-Augmented Generation (RAG) chat and summarization. 

Designed with resilience and scalability in mind, it features a sophisticated multi-model fallback router, dynamic retrieval strategies, and a highly optimized asynchronous backend.

## 🌟 Core Architecture & Engineering Highlights

This project demonstrates advanced AI engineering and full-stack system design, bridging complex LLM orchestration with robust backend infrastructure.

### 🧠 Intelligent Routing & Dynamic Retrieval
- **Context-Aware Query Routing:** The `RouterService` dynamically inspects incoming queries and document sizes, routing requests between standard **Vector RAG** (for targeted questions) and a specialized **PageIndex** strategy (for complex, document-wide keyword analysis).
- **Multi-Model Orchestration:** Summaries are written by Gemini (`gemini-3.6-flash`) with the same API key used for embeddings. Groq and OpenRouter remain fallbacks when that key is absent.
- **Gemini Embeddings:** Document chunks are embedded with Google `gemini-embedding-001` at 768 dimensions and stored in **MongoDB Atlas Vector Search** for cosine similarity lookup.

### ⚡ Resilient & Asynchronous Backend
- **FastAPI / Python 3.12:** Fully asynchronous non-blocking I/O operations for high concurrency.
- **Enterprise Security:** Implements rate limiting (SlowAPI), custom JWT authentication (Supabase), structured CORS, and Trusted Host middleware.
- **Eventual Consistency:** Defensively coded retrieval loops to handle the latency between database ingestion and Atlas Vector Search index updates.
- **Memory-Safe Ingestion:** Buffered asynchronous chunking for PDFs up to 100 pages, ensuring the server handles heavy payloads without OOM (Out Of Memory) crashes.

### 🎨 Modern Frontend & Infrastructure
- **React + Vite + TypeScript:** A highly responsive frontend utilizing `shadcn/ui` and Tailwind CSS.
- **Supabase Storage & Auth:** Secure, edge-optimized storage for raw PDFs with JWT-based row-level security.
- **MongoDB Atlas:** Acts as both the primary transactional database (metadata, chat histories, session TTL) and the Vector Database.

## 🛠️ Tech Stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Shadcn UI
- **Backend:** Python, FastAPI, LangChain, PyMongo, SlowAPI, Gunicorn
- **AI/ML:** Google Gemini (chat and embeddings), Groq, OpenRouter
- **Database & Auth:** MongoDB Atlas (Vector Search), Supabase (Auth & Storage)

## 🚀 Getting Started

### 1. Environment Setup

Create a `.env` in the `backend/` directory:
```env
MONGO_URI=mongodb+srv://<user>:<password>@cluster0.mongodb.net/?appName=Cluster0
DB_NAME=pdfnectar
COLLECTION_NAME=document_embeddings
ATLAS_VECTOR_SEARCH_INDEX_NAME=vector_index

# Model Fallbacks
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-v1-...
GEMINI_API_KEY=AIza...

# Supabase
SUPABASE_URL=https://<project-id>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
```

Create a `.env` in the `frontend/` directory:
```env
VITE_SUPABASE_PROJECT_ID="<project-id>"
VITE_SUPABASE_PUBLISHABLE_KEY="eyJhbGci..."
VITE_SUPABASE_URL="https://<project-id>.supabase.co"
```

### 2. Running Locally

**Start the backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Start the frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 📈 System Workflow
1. **Upload & Sanitize:** The user uploads a PDF. The file is validated and securely stored in Supabase.
2. **Background Ingestion:** A background task extracts text, chunks it, generates 768-dimension embeddings with Gemini, and pushes vectors to MongoDB Atlas.
3. **Query Analysis:** A user submits a query. The `RouterService` analyzes the prompt complexity and document metadata (e.g. `has_numeric_data`).
4. **Vector Search:** The system performs a K-NN vector search against MongoDB Atlas. 
5. **LLM Generation:** The context is packaged into a strict prompt template and sent to Gemini 3.6 Flash for the final response.
