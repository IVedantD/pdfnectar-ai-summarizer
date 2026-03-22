import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# API Configurations
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Hybrid RAG Thresholds
PAGEINDEX_THRESHOLD = 30  # Page count threshold to enable PageIndex

# Keywords for complex query detection
COMPLEX_KEYWORDS = [
    "compare", "analyze", "trend", "why", "background", 
    "relationship", "explain", "difference", "correlation",
    "summary", "synthesize", "comprehensive"
]

# Database Configurations
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "pdfnectar")

# Storage
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
