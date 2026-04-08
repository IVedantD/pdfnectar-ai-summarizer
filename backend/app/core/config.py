import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Ensure consistent API key for Google/Gemini
if os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# API Configurations
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-preview-02-05:free")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
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
