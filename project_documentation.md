# PDF Nectar AI Summarizer - Project Documentation

## Architecture Overview
The project is a full-stack application built to allow users to upload PDF documents, summarize them, and chat with them using Large Language Models and Retrieval Augmented Generation (RAG).

### 1. Frontend
- **Framework**: React 18, set up with Vite (`vite_react_shadcn_ts`).
- **Language**: TypeScript for static typing and safe builds.
- **Styling**: Tailwind CSS for utility-first styling.
- **UI Components**: Radix UI and Shadcn UI components for accessible, reusable components (like Dialogs, Forms, Menus, Toasts). Icons by Lucide React.
- **Animations**: Framer Motion for smooth transitions.
- **State Management & Routing**: React Query (@tanstack/react-query) for data fetching/caching and React Router DOM for routing.
- **Form Handling**: React Hook Form combined with Zod for robust client-side validation.

### 2. Backend
- **Framework**: FastAPI (Python), providing auto-generated API docs (Swagger/OpenAPI) and fast async endpoints.
- **Database**: MongoDB Atlas with Vector Search capabilities configured.
- **AI / LLM Integration**: LangChain heavily utilized to orchestrate RAG.
  - LLM Model: `gemini-1.5-flash` through `ChatGoogleGenerativeAI` for chat capabilities.
  - Embeddings: `models/embedding-001` through `GoogleGenerativeAIEmbeddings`.
- **PDF Processing**: `PyMuPDFLoader` (from `langchain_community.document_loaders`) and `RecursiveCharacterTextSplitter` to ingest, read, and chunk PDFs for vector storage.

## Features Implemented So Far

### Backend Setup and Endpoints
1. **Infrastructure**: Established virtual environment (`venv`) and managed dependencies (`requirements.txt`).
2. **Environment Configuration**: Set up `.env` for `GEMINI_API_KEY`, `MONGO_URI`, and DB vars.
3. **Database Module (`database.py`)**:
   - Connection to MongoDB (`DB_NAME`, `COLLECTION_NAME`).
   - Setup for `MongoDBAtlasVectorSearch` using Google's generative AI embeddings (`models/embedding-001` with 768 dimensions).
   - Utility for creating vector search indexes programmatically (`create_search_index()`).
4. **Main API Definitions (`main.py`)**:
   - `GET /`: Welcome route.
   - `GET /health`: Healthcheck endpoint.
   - `POST /api/upload`: Handles `.pdf` uploads, writes temporarily to disk, loads with `PyMuPDFLoader`, splits the text (`chunk_size=1000`, `chunk_overlap=200`), assigns metadata (`source_file`), and ingests into the MongoDB Vector store.
   - `POST /api/chat`: Accepts conversational queries (`query`, `session_id`). Retrieves similar vector chunks from DB (`k=5`). Uses a LCEL (LangChain Expression Language) prompt chain with Gemini (`gemini-1.5-flash`) via `RunnableWithMessageHistory` to hold context. History is durably stored in a distinct MongoDB collection (`chat_histories`).
   - `GET /api/history/{session_id}`: Retrieves chat history on frontend mount/load from MongoDB.

### Frontend Setup
1. **Core Configuration**: Standardized `npm` workspace with `package.json` listing Vite, React Hook Form, Shadcn dependencies.
2. **Index Structure (`index.html`)**: Updated meta tags, title set to "PDF Nectar", removed generic template artifacts. Favicon standardized.
3. **Tooling Integration**: Full ESLint, Vitest, and Playwright configuration mapped out for high quality logic and E2E testing. 

## Next Steps / Future Work
- Connecting the React UI components seamlessly with the established `/api/upload` and `/api/chat` endpoints using Axios or React Query explicitly.
- Rendering markdown or rich text responses from the Gemini API safely on the frontend.
- Polishing Shadcn UI components for PDF upload dropzones and chat interfaces.
