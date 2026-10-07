import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Ensure consistent API key for Google/Gemini
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'")
if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# Models shut down as of October 2026. A Render env var may still name the old id.
_RETIRED_MODELS = {
    "gemini-2.0-flash": "gemini-3.6-flash",
    "gemini-2.0-flash-001": "gemini-3.6-flash",
    "gemini-2.0-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.0-flash-lite-001": "gemini-3.5-flash-lite",
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
    "google/gemini-2.0-flash-lite-preview-02-05:free": "google/gemma-4-31b-it:free",
}

def _current_model(env_name: str, default: str) -> str:
    raw = (os.getenv(env_name) or default).strip()
    return _RETIRED_MODELS.get(raw, raw)

# API Configurations
GEMINI_MODEL = _current_model("GEMINI_MODEL", "gemini-3.6-flash")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = _current_model("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = _current_model("GROQ_MODEL", "openai/gpt-oss-120b")
SITE_URL = os.getenv("SITE_URL", "http://localhost:3000")
SITE_NAME = os.getenv("SITE_NAME", "PDFNectar")

# Hybrid RAG Thresholds
PAGEINDEX_THRESHOLD = 20  # Page count threshold to enable PageIndex

# Keywords for complex query detection
COMPLEX_KEYWORDS = [
    "compare", "analyze", "trend", "why", "background", 
    "relationship", "explain", "difference", "correlation",
    "summary", "summarize", "synthesize", "comprehensive"
]

# Database Configurations
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "pdfnectar")

# Storage
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
